"""Benchmark harness (D17): does routing actually save credits *per success*?

The claim under test is not "cheaper tokens". It is ``cost_per_success`` —
total provider-billed USD divided by the tasks that passed. An arm that saves
money by failing more is not cheaper, it is worse. So every arm runs the same
tasks, in a randomized order, and the comparison is paired task-by-task.

Arms:

  plain-strong    one strong model, static effort, no brief
  plain-cheap     one cheap model, static effort, no brief
  tamias-static   routing off (static policy), brief off
  tamias-full     routing auto + brief on
  external-codex  an external agent, when configured (else reported as skipped)

Decision gate: routing becomes the default only if ``tamias-full`` improves
``cost_per_success`` by at least 20% over ``tamias-static`` with a pass-rate
drop of at most 2 points. Otherwise it stays opt-in and the *negative* result is
published — a benchmark that can only ever say "yes" is not a benchmark.

This module is the harness and the maths. It does not contain any results: run
it (:func:`main`) to produce a results file. Never quote a number this did not
measure.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from dataclasses import asdict, dataclass

GATE_MIN_IMPROVEMENT = 0.20   # >= 20% cheaper per success to promote
GATE_MAX_PASS_DROP = 0.02     # <= 2 percentage points of pass-rate loss
DEFAULT_ITERATIONS = 2000


@dataclass(frozen=True)
class Arm:
    """One configuration under test."""
    name: str
    model: str
    effort: str = "static"     # AGENT_EFFORT_POLICY
    brief: bool = False        # AGENT_BRIEF
    tiers: tuple = ()          # (free, mid, premium) for routing; () = none
    note: str = ""


DEFAULT_ARMS = (
    Arm("plain-strong", "anthropic/claude-3-opus",
        note="naive: one strong model, no routing, no brief"),
    Arm("plain-cheap", "google/gemma-4-31b-it:free",
        note="naive: one cheap model, no routing, no brief"),
    Arm("tamias-static", "nvidia/nemotron-3.5-lightning:free", "static", False,
        note="control: tamias with routing off, same base model as tamias-full"),
    Arm("tamias-full", "nvidia/nemotron-3.5-lightning:free", "auto", True,
        tiers=("nvidia/nemotron-3.5-lightning:free",
               "google/gemma-4-31b-it:free",
               "anthropic/claude-3.5-sonnet"),
        note="tamias with routing on and the brief compiler on"),
    Arm("external-codex", "external:codex", note="skipped unless wired"),
)


@dataclass(frozen=True)
class Task:
    """One benchmark task and how to grade it."""
    id: str
    prompt: str
    check: str = ""            # shell command; exit 0 == passed. "" == ungraded


@dataclass
class TaskResult:
    task: str
    arm: str
    passed: bool
    cost_usd: float
    steps: int = 0
    note: str = ""


@dataclass
class ArmSummary:
    arm: str
    tasks: int
    passed: int
    pass_rate: float
    total_usd: float
    cost_per_success: float    # inf when nothing passed


@dataclass
class Decision:
    promote: bool
    improvement: float         # fraction cheaper per success (0.2 == 20%)
    pass_drop: float           # absolute pass-rate drop
    reason: str


def summarize(results, arms=None) -> list:
    """Per-arm totals. ``cost_per_success`` is inf when an arm passed nothing."""
    names = [a.name for a in (arms or [])]
    seen = []

    for result in results:
        if result.arm not in seen:
            seen.append(result.arm)

    ordered = [name for name in names if name in seen] + \
              [name for name in seen if name not in names]

    summaries = []

    for name in ordered:
        rows = [r for r in results if r.arm == name]
        passed = sum(1 for r in rows if r.passed)
        total = sum(r.cost_usd for r in rows)
        rate = (passed / len(rows)) if rows else 0.0
        cps = (total / passed) if passed else float("inf")

        summaries.append(ArmSummary(
            arm=name, tasks=len(rows), passed=passed, pass_rate=round(rate, 4),
            total_usd=round(total, 6), cost_per_success=cps,
        ))

    return summaries


def _cps(rows):
    passed = sum(1 for r in rows if r.passed)
    total = sum(r.cost_usd for r in rows)
    return (total / passed) if passed else float("inf")


def _pass_rate(rows):
    return (sum(1 for r in rows if r.passed) / len(rows)) if rows else 0.0


def paired_bootstrap(results, baseline, candidate, iterations=DEFAULT_ITERATIONS,
                     seed=0, confidence=0.95):
    """Paired CIs for two arms over the same tasks.

    Resamples *tasks* with replacement (paired: both arms are re-measured on the
    same resampled task set), so the interval reflects task difficulty rather
    than arm-to-arm noise. Returns a dict with the point deltas and the CI
    bounds; ``improvement`` is the fraction cheaper per success.
    """
    by_task = {}

    for result in results:
        if result.arm in (baseline, candidate):
            by_task.setdefault(result.task, {})[result.arm] = result

    tasks = [t for t, pair in by_task.items()
             if baseline in pair and candidate in pair]

    if not tasks:
        return {"tasks": 0, "improvement": 0.0, "pass_drop": 0.0,
                "improvement_ci": [0.0, 0.0], "pass_drop_ci": [0.0, 0.0]}

    def stats_for(sample):
        base_rows = [by_task[t][baseline] for t in sample]
        cand_rows = [by_task[t][candidate] for t in sample]
        base_cps, cand_cps = _cps(base_rows), _cps(cand_rows)

        if base_cps in (0.0, float("inf")) or base_cps != base_cps:
            improvement = 0.0
        else:
            improvement = (base_cps - cand_cps) / base_cps

        pass_drop = _pass_rate(base_rows) - _pass_rate(cand_rows)
        return improvement, pass_drop

    point_improvement, point_pass_drop = stats_for(tasks)

    rng = random.Random(seed)
    improvements = []
    pass_drops = []

    for _ in range(iterations):
        sample = [tasks[rng.randrange(len(tasks))] for _ in tasks]
        improvement, pass_drop = stats_for(sample)
        if improvement == improvement:  # drop NaN (0/0)
            improvements.append(improvement)
        pass_drops.append(pass_drop)

    def bounds(values):
        if not values:
            return [0.0, 0.0]
        values = sorted(values)
        low = values[int((1 - confidence) / 2 * (len(values) - 1))]
        high = values[int((1 + confidence) / 2 * (len(values) - 1))]
        return [low, high]

    return {
        "tasks": len(tasks),
        "improvement": point_improvement,
        "pass_drop": point_pass_drop,
        "improvement_ci": bounds(improvements),
        "pass_drop_ci": bounds(pass_drops),
    }


def decide(baseline: ArmSummary, candidate: ArmSummary, ci) -> Decision:
    """The gate: promote only if clearly cheaper with little accuracy lost."""
    if baseline.cost_per_success in (0.0, float("inf")):
        return Decision(False, 0.0, 0.0,
                        "baseline has no priced success; nothing to compare")

    improvement = ci["improvement"]
    pass_drop = ci["pass_drop"]
    improvement_low = ci["improvement_ci"][0]

    cheaper = improvement >= GATE_MIN_IMPROVEMENT
    established = improvement_low > 0
    accurate = pass_drop <= GATE_MAX_PASS_DROP
    promote = cheaper and established and accurate

    if promote:
        reason = (f"{improvement:.0%} cheaper per success with a "
                  f"{pass_drop:+.1%} pass-rate change")
    elif not cheaper:
        reason = (f"improvement {improvement:.0%} is below the "
                  f"{GATE_MIN_IMPROVEMENT:.0%} bar")
    elif not accurate:
        reason = (f"pass-rate drop {pass_drop:+.1%} exceeds the "
                  f"{GATE_MAX_PASS_DROP:.0%} budget")
    else:
        reason = (f"the paired interval ({improvement_low:.0%}.."
                  f"{ci['improvement_ci'][1]:.0%}) does not establish a saving")

    return Decision(promote, improvement, pass_drop, reason)


def run_benchmark(tasks, arms, runner, seed=0):
    """Run every arm on every task, arm order randomized per task."""
    rng = random.Random(seed)
    results = []

    for task in tasks:
        order = list(arms)
        rng.shuffle(order)
        for arm in order:
            results.append(runner(arm, task))

    return results


def grade_command(command, cwd="."):
    """True when the grading command exits 0. A blank command is ungraded (False)."""
    if not command.strip():
        return False

    try:
        completed = subprocess.run(command, cwd=cwd, shell=True,
                                   capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.SubprocessError):
        return False

    return completed.returncode == 0


class LiveRunner:
    """Run one arm on one task through the real agent, then grade it.

    A live run is the only thing that produces a real number. It shells out to
    ``agent.py`` with the arm's model/effort/brief, parses the billed spend from
    the run's own summary, and grades with the task's check. Nothing here is
    simulated.
    """

    SUMMARY_MARK = "spent: $"

    def __init__(self, agent_path="agent.py", python=None, cwd=".",
                 max_steps=25, env=None, timeout=3600):
        self.agent_path = agent_path
        self.python = python or sys.executable
        self.cwd = cwd
        self.max_steps = max_steps
        self.env = dict(env or {})
        self.timeout = timeout

    def _env_for(self, arm):
        env = dict(os.environ)
        env.update(self.env)
        env["AGENT_MODEL"] = arm.model
        env["AGENT_EFFORT_POLICY"] = arm.effort
        if arm.brief:
            env["AGENT_BRIEF"] = "1"
        if arm.tiers:
            free, mid, premium = (list(arm.tiers) + [arm.model] * 3)[:3]
            env["AGENT_MODEL_FREE"] = free
            env["AGENT_MODEL_MID"] = mid
            env["AGENT_MODEL_PREMIUM"] = premium
        return env

    @staticmethod
    def parse_cost(output):
        """The spend from the run's summary line, or 0.0 when it is absent."""
        for line in reversed(output.splitlines()):
            if LiveRunner.SUMMARY_MARK in line:
                tail = line.split(LiveRunner.SUMMARY_MARK, 1)[1].strip()
                try:
                    return float(tail.split()[0].strip("$"))
                except (ValueError, IndexError):
                    return 0.0
        return 0.0

    def __call__(self, arm, task):
        if arm.model.startswith("external:"):
            return TaskResult(task.id, arm.name, False, 0.0,
                              note="external arm not wired")

        command = [self.python, self.agent_path, "--task", task.prompt,
                   "--max-steps", str(self.max_steps)]

        try:
            completed = subprocess.run(command, cwd=self.cwd,
                                       env=self._env_for(arm),
                                       capture_output=True, text=True,
                                       timeout=self.timeout)
            output = (completed.stdout or "") + (completed.stderr or "")
        except (OSError, subprocess.SubprocessError) as error:
            return TaskResult(task.id, arm.name, False, 0.0, note=str(error)[:120])

        passed = grade_command(task.check, cwd=self.cwd)
        return TaskResult(task.id, arm.name, passed, self.parse_cost(output))


def load_tasks(path):
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    return [Task(id=item["id"], prompt=item["prompt"],
                 check=item.get("check", "")) for item in raw]


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="bench.py",
        description="Tamias benchmark: cost per success across arms (D17)")
    parser.add_argument("--tasks", required=True,
                        help="JSON list of {id, prompt, check} tasks")
    parser.add_argument("--out", default="bench-results.json",
                        help="where to write the results (default: %(default)s)")
    parser.add_argument("--seed", type=int, default=0,
                        help="randomizes arm order per task (default: 0)")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS,
                        help="bootstrap iterations (default: %(default)s)")
    parser.add_argument("--baseline", default="tamias-static")
    parser.add_argument("--candidate", default="tamias-full")
    parser.add_argument("--agent", default="agent.py", help="path to agent.py")
    parser.add_argument("--cwd", default=".", help="working directory for a run")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan (arms x tasks) and exit; no model calls")
    args = parser.parse_args(argv)

    tasks = load_tasks(args.tasks)
    arms = list(DEFAULT_ARMS)

    if args.dry_run:
        print(f"{len(arms)} arms x {len(tasks)} tasks = "
              f"{len(arms) * len(tasks)} runs")
        for arm in arms:
            print(f"  {arm.name:16} model={arm.model} effort={arm.effort} "
                  f"brief={arm.brief}")
        return 0

    runner = LiveRunner(agent_path=args.agent, cwd=args.cwd)
    results = run_benchmark(tasks, arms, runner, seed=args.seed)
    summaries = summarize(results, arms)

    payload = {
        "seed": args.seed,
        "iterations": args.iterations,
        "arms": [asdict(arm) for arm in arms],
        "tasks": [asdict(task) for task in tasks],
        "results": [asdict(result) for result in results],
        "summaries": [asdict(summary) for summary in summaries],
    }

    by_name = {summary.arm: summary for summary in summaries}
    baseline = by_name.get(args.baseline)
    candidate = by_name.get(args.candidate)

    if baseline and candidate:
        ci = paired_bootstrap(results, args.baseline, args.candidate,
                              iterations=args.iterations, seed=args.seed)
        decision = decide(baseline, candidate, ci)
        payload["comparison"] = {
            "baseline": args.baseline, "candidate": args.candidate,
            "ci": ci, "decision": asdict(decision),
        }
        print(f"{args.candidate} vs {args.baseline}: "
              f"{decision.improvement:.1%} cheaper per success, "
              f"pass-rate {decision.pass_drop:+.1%} -> "
              f"{'PROMOTE' if decision.promote else 'keep opt-in'} "
              f"({decision.reason})")

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
