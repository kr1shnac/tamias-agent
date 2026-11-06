"""A receipt for one agent turn (docs/PREMIUM-AGENT.md).

The receipt is deliberately deterministic. It is built from the same events
the transcript sees - tool starts/ends, asks, model switches and the provider
billed turn end - and it never asks the model to summarise itself. A model can
be wrong; a receipt cannot quietly invent work.

Pure Python, no Textual, so the accounting rules can be tested on their own.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional


# Tools whose arguments name a path the receipt should show. Kept local so the
# TUI accounting layer does not import the agent core (and its network stack).
_PATH_KEYS = {
    "read_file": "file_path",
    "write_file": "file_path",
    "edit_file": "file_path",
    "create_directory": "path",
    "list_directory": "path",
    "search_in_files": "directory",
    "investigate_target": "target",
    "trace_feature": "entry_point",
    "analyze_structure": "directory",
    "build_similar": "target_location",
}

# A verification command is one whose exit status is evidence about the work.
# These are executables that check code, not any command that happens to
# contain the word "pytest" (``pip install pytest`` is not a test run).
_VERIFICATION_EXES = {
    "pytest", "py.test", "unittest", "ruff", "flake8", "pylint", "mypy",
    "pyright", "eslint", "tsc", "tox", "nox", "jest", "vitest", "mocha",
    "ava", "tap", "phpunit", "rspec",
}
_PACKAGE_RUNNERS = {"uv", "poetry", "pdm", "hatch"}
_NODE_RUNNERS = {"npm", "pnpm", "yarn", "bun"}
_NODE_SCRIPTS = ("test", "build", "lint", "typecheck", "check")
_SEGMENT_SPLIT = re.compile(r"\s*(?:&&|\|\||;|\n|\|)\s*")
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
_SHELL_PREFIXES = {"sudo", "time", "command", "env", "nohup"}


def is_verification(command: str) -> bool:
    """True when this shell command is a check whose exit status matters.

    The command is split into simple segments (``&&``, ``;``, ``|``), and each
    segment must start with a known test/check runner. This is deliberately
    conservative: ``pip install pytest`` and ``echo pytest`` are not checks.
    """
    if not command:
        return False
    for segment in _SEGMENT_SPLIT.split(str(command)):
        if _is_verification_segment(segment):
            return True
    return False


def _is_verification_segment(segment: str) -> bool:
    try:
        tokens = shlex.split(segment, posix=True)
    except ValueError:
        return False
    if not tokens:
        return False

    while tokens and (tokens[0] in _SHELL_PREFIXES
                      or _ENV_ASSIGNMENT.match(tokens[0])):
        tokens = tokens[1:]
    if not tokens:
        return False

    exe = os.path.basename(tokens[0]).lower()
    args = tokens[1:]

    if exe in _VERIFICATION_EXES:
        return True
    if exe.startswith("python"):
        return (len(args) >= 2 and args[0] == "-m"
                and args[1] in _VERIFICATION_EXES)
    if exe in _PACKAGE_RUNNERS:
        return (len(args) >= 2 and args[0] == "run"
                and _is_verification_segment(" ".join(shlex.quote(a) for a in args[1:])))
    if exe in _NODE_RUNNERS:
        if args and args[0] in _NODE_SCRIPTS:
            return True
        if len(args) >= 2 and args[0] == "run":
            return args[1].startswith(_NODE_SCRIPTS)
        if len(args) >= 2 and args[0] == "exec":
            return _is_verification_segment(" ".join(shlex.quote(a) for a in args[1:]))
        return False
    if exe in ("npx", "bunx"):
        return bool(args) and _is_verification_segment(
            " ".join(shlex.quote(a) for a in args))
    if exe in ("cargo", "go") and args:
        return args[0] in ("test", "build", "check", "vet", "clippy")
    if exe in ("deno", "dotnet", "mvn", "gradle", "swift") and args:
        return args[0] == "test"
    if exe == "make" and args:
        return args[0] in ("test", "check", "build")
    if exe in ("bash", "sh") and len(args) == 1:
        return os.path.basename(args[0]).lower() == "check_all.sh"
    return exe == "check_all.sh"


def _as_usd(value: object) -> Optional[float]:
    """A finite, non-negative provider cost, or ``None`` when it is unknown."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if value < 0 or value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def _first_line(text: object) -> str:
    line = str(text or "").strip().splitlines()
    return line[0][:240] if line else ""


def _add_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _join(items: Iterable[str], empty: str = "none") -> str:
    values = [value for value in items if value]
    return ", ".join(values) if values else empty


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"


@dataclass(frozen=True)
class ShellRun:
    """One shell command that actually ran, with its observed status."""

    command: str
    success: bool
    duration_sec: float = 0.0
    verification: bool = False


@dataclass
class _PendingTool:
    name: str
    args: dict
    target: str = ""
    command: str = ""


@dataclass
class TurnReceipt:
    """Everything measured about one user turn.

    ``status`` is a fact, not a promise: "checks passed" only means the named
    verification commands exited successfully. It never means the change is
    correct, and it never means the task is complete.
    """

    number: int = 0
    prompt: str = ""
    session_id: str = ""
    started_at: float = field(default_factory=time.monotonic)
    ended_at: Optional[float] = None
    model: str = ""
    tier: str = ""
    policy_name: str = ""

    tools: dict[str, int] = field(default_factory=dict)
    files_read: list[str] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    files_edited: list[str] = field(default_factory=list)
    dirs_created: list[str] = field(default_factory=list)
    shell_runs: list[ShellRun] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)
    refusals: list[tuple[str, str]] = field(default_factory=list)

    asks: int = 0
    ask_denials: int = 0
    policy_denials: int = 0
    dossier_blocks: int = 0
    boundary: bool = False
    refused: bool = False
    plan_denied: bool = False
    plan_approved: bool = False
    plan_blocked: bool = False
    plan_block_reason: str = ""
    checkpoint_id: str = ""
    checkpoint_files: int = 0
    checkpoint_shell: bool = False
    checkpoint_added: int = 0
    checkpoint_removed: int = 0
    checkpoint_diff_paths: int = 0
    checkpoint_diff_truncated: bool = False
    checkpoint_restored: str = ""
    error: str = ""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: Optional[float] = None
    unpriced_steps: int = 0
    model_switches: list[dict] = field(default_factory=list)
    extra_sections: list[tuple[str, list[tuple[str, str]]]] = field(
        default_factory=list, repr=False)
    extra_risks: list[str] = field(default_factory=list, repr=False)

    _pending: dict[str, _PendingTool] = field(default_factory=dict, repr=False)

    # ---------------------------------------------------------------- ingest
    def note_tool_start(self, tool_id: str, name: str, arguments: object) -> None:
        """Remember a tool before it runs; nothing is counted as changed yet."""
        args = _parse_args(arguments)
        path_key = _PATH_KEYS.get(name)
        target = str(args.get(path_key, "")) if path_key else ""
        command = str(args.get("command", "")) if name == "run_shell" else ""

        self.tools[name] = self.tools.get(name, 0) + 1
        self._pending[tool_id] = _PendingTool(
            name=name, args=args, target=target, command=command)

    def note_tool_end(self, tool_id: str, tool_name: str, result: object,
                      success: bool = True, duration_sec: float = 0.0) -> None:
        """Fold a finished call in. Only a successful call may claim a change."""
        pending = self._pending.pop(tool_id, None)
        name = (pending.name if pending else tool_name) or "(unreported call)"
        target = pending.target if pending else ""
        command = pending.command if pending else ""

        text = str(result or "")
        failed = (not success) or text.startswith("Error:")
        boundary = _is_boundary(text)
        ask_denied = "policy ask denied" in text.lower()
        dossier_block = "dossier gate" in text.lower()
        plan_hold = text.startswith("Error: plan contract")

        if boundary:
            self.boundary = True
            self.policy_denials += 1
            self._note_refusal(name, text)
        elif ask_denied:
            self.ask_denials += 1
            self._note_refusal(name, text)
        elif plan_hold:
            # A plan denial is recorded by the modal callback; a drift/no-
            # approver hold only arrives as the tool result. Neither is a
            # failed tool call, and neither is a policy boundary.
            if not self.plan_denied:
                self.note_plan_block(text)
            self._note_refusal(name, text)
        elif dossier_block:
            self.dossier_blocks += 1
            self._note_refusal(name, text)
        elif failed:
            self.failures.append((name, _first_line(text)))

        # A denied call never touched the filesystem, so it must not appear in
        # the changed-file lists. A failed edit is not a change either.
        if name == "run_shell" and command and not (
                boundary or ask_denied or plan_hold or dossier_block):
            self.shell_runs.append(ShellRun(
                command=command,
                success=not failed,
                duration_sec=max(0.0, float(duration_sec or 0.0)),
                verification=is_verification(command),
            ))
        elif not failed:
            self._record_success(name, target)

    def note_ask(self, tool_name: str = "", reason: str = "") -> None:
        """One human decision was requested; the answer arrives as a tool end."""
        self.asks += 1

    def note_model_switch(self, old_model: str, new_model: str,
                          old_tier: str = "", new_tier: str = "",
                          reason: str = "") -> None:
        self.model_switches.append({
            "old_model": old_model,
            "new_model": new_model,
            "old_tier": old_tier,
            "new_tier": new_tier,
            "reason": reason,
        })

    def note_plan_decision(self, approved: bool) -> None:
        """Record the human's answer to a Plan Contract request."""
        self.plan_approved = bool(approved)
        self.plan_denied = not bool(approved)

    def note_plan_block(self, message: str) -> None:
        """Record a write held by the signed plan (drift or no approver)."""
        self.plan_blocked = True
        self.plan_block_reason = _first_line(message)

    def note_checkpoint(self, checkpoint_id: str, files: int,
                        shell_ran: bool = False, added: int = 0,
                        removed: int = 0, diff_paths: int = 0,
                        diff_truncated: bool = False) -> None:
        """Attach the turn's file checkpoint and its measured diff summary."""
        self.checkpoint_id = str(checkpoint_id or "")
        self.checkpoint_files = max(0, int(files or 0))
        self.checkpoint_shell = bool(shell_ran)
        self.checkpoint_added = max(0, int(added or 0))
        self.checkpoint_removed = max(0, int(removed or 0))
        self.checkpoint_diff_paths = max(0, int(diff_paths or 0))
        self.checkpoint_diff_truncated = bool(diff_truncated)
        if self.checkpoint_diff_truncated:
            self.add_risk(
                "The checkpoint diff is truncated; review the files directly.")

    def note_restore(self, result) -> None:
        """Record an explicit restore; a failure is never hidden."""
        self.checkpoint_restored = result.summary()
        rows = [("result", result.summary())]
        for warning in result.warnings:
            rows.append(("warning", warning))
            self.add_risk(warning)
        for path, reason in result.failed:
            rows.append(("failed", f"{path}: {reason}"))
            self.add_risk(f"Checkpoint restore failed for {path}: {reason}")
        self.add_section("RESTORE", rows)

    def note_boundary(self, message: str) -> None:
        """A boundary status (including a refusal before any model call)."""
        self.boundary = True
        self._note_refusal("turn", message)
        if (not self.tools and not self.prompt_tokens
                and "outside use case" in str(message).lower()):
            self.refused = True

    def add_section(self, title: str,
                    rows: list[tuple[str, str]]) -> None:
        """Attach a measured work surface (plan, investigation) to the record."""
        if rows:
            self.extra_sections.append((title, list(rows)))

    def add_risk(self, text: str) -> None:
        """Attach a measured limitation the reviewer must see."""
        if text and text not in self.extra_risks:
            self.extra_risks.append(text)

    def note_error(self, message: str) -> None:
        text = _first_line(message)
        if text.startswith("Error: "):
            text = text[len("Error: "):]
        self.error = text
        if _is_boundary(message):
            self.boundary = True

    def finish(self, prompt_tokens: int = 0, completion_tokens: int = 0,
               cost_usd: object = None, unpriced_steps: int = 0,
               model: str = "", tier: str = "") -> None:
        """Close the receipt with the provider-billed turn figures."""
        self.ended_at = time.monotonic()
        self.prompt_tokens = max(0, int(prompt_tokens or 0))
        self.completion_tokens = max(0, int(completion_tokens or 0))
        self.cost_usd = _as_usd(cost_usd)
        self.unpriced_steps = max(0, int(unpriced_steps or 0))
        if self.cost_usd is None:
            self.unpriced_steps = max(1, self.unpriced_steps)
        if model:
            self.model = model
        if tier:
            self.tier = tier
        if not self.model and self.model_switches:
            self.model = self.model_switches[-1].get("new_model", "")
        if not self.tier and self.model_switches:
            self.tier = self.model_switches[-1].get("new_tier", "")

    # -------------------------------------------------------------- derived
    @property
    def duration_sec(self) -> float:
        end = self.ended_at if self.ended_at is not None else time.monotonic()
        return max(0.0, end - self.started_at)

    @property
    def duration_hms(self) -> str:
        total = int(self.duration_sec)
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def changed_files(self) -> list[str]:
        values: list[str] = []
        for path in self.files_written + self.files_edited + self.dirs_created:
            _add_unique(values, path)
        return values

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_files)

    @property
    def verification_runs(self) -> list[ShellRun]:
        return [run for run in self.shell_runs if run.verification]

    @property
    def checks_passed(self) -> int:
        return sum(1 for run in self.verification_runs if run.success)

    @property
    def checks_failed(self) -> int:
        return sum(1 for run in self.verification_runs if not run.success)

    @property
    def status(self) -> str:
        # a request refused before any model call is a deliberate refusal, not
        # a mid-turn boundary incident; label it as such
        if self.refused:
            return "refused"
        if self.plan_denied:
            return "plan denied"
        if self.plan_blocked:
            return "plan blocked"
        if self.boundary:
            return "blocked"
        if self.checks_failed:
            return "checks failed"
        if self.error:
            return "error"
        if self.has_changes or self.failures:
            return "needs review"
        if self.verification_runs:
            return "checks passed"
        return "answered"

    @property
    def status_label(self) -> str:
        return self.status.upper()

    @property
    def status_color(self) -> str:
        return {
            "blocked": "#fca5a5",
            "refused": "#fbbf24",
            "plan denied": "#fbbf24",
            "plan blocked": "#fbbf24",
            "checks failed": "#fca5a5",
            "error": "#fca5a5",
            "needs review": "#00b8ff",
            "checks passed": "#00ff9f",
            "answered": "#94a3b8",
        }[self.status]

    def cost_text(self) -> str:
        """Provider-billed cost, or a plain admission that it is unknown."""
        if self.cost_usd is None:
            if self.unpriced_steps:
                return f"cost unknown ({_plural(self.unpriced_steps, 'unpriced step')})"
            return "cost unknown"
        if (self.cost_usd == 0 and self.prompt_tokens == 0
                and self.completion_tokens == 0 and not self.tools):
            return "$0.0000 (no model call)"
        text = f"${self.cost_usd:.4f} (provider-billed)"
        if self.unpriced_steps:
            text += f" + {_plural(self.unpriced_steps, 'unpriced step')}"
        return text

    def risks(self) -> list[str]:
        """Facts the reviewer needs; never a claim that the work is safe."""
        risks: list[str] = []
        if self.refused:
            risks.append("The request was refused before any model call.")
        elif self.plan_denied:
            risks.append("The human denied the published plan; no writes ran.")
        elif self.plan_blocked:
            risks.append(
                "The plan contract stopped this turn: "
                f"{self.plan_block_reason or 'write held'}")
        elif self.boundary:
            risks.append("A policy boundary stopped this turn; "
                         "nothing outside the boundary was run.")
        if self.checkpoint_shell:
            risks.append(
                "Shell commands ran this turn; checkpoint restore does not "
                "capture changes they made outside tracked files.")
        if self.error:
            risks.append(f"The turn ended with an error: {self.error}")
        if self.failures:
            risks.append(f"{_plural(len(self.failures), 'tool call')} failed.")
        if self.dossier_blocks:
            risks.append(
                f"{_plural(self.dossier_blocks, 'write call')} held until "
                "investigation evidence existed.")
        if self.checks_failed:
            risks.append(f"{_plural(self.checks_failed, 'verification command')} "
                         "did not exit successfully.")
        if not self.verification_runs and self.has_changes:
            risks.append("No verification command was run for the changed files.")
        if self.unpriced_steps:
            risks.append(f"Cost is incomplete: "
                         f"{_plural(self.unpriced_steps, 'step')} unpriced.")
        risks.extend(self.extra_risks)
        if not risks:
            return []
        return _dedupe(risks)

    def summary_line(self) -> str:
        """One calm line for the transcript after a turn."""
        parts: list[str] = []
        if self.refused:
            parts.append("request refused")
        elif self.plan_denied:
            parts.append("plan denied")
            parts.append(
                f"{_plural(len(self.changed_files), 'file')} changed"
                if self.has_changes else "no files changed")
        elif self.plan_blocked:
            parts.append("plan blocked")
            parts.append(
                f"{_plural(len(self.changed_files), 'file')} changed"
                if self.has_changes else "no files changed")
        elif self.boundary:
            parts.append(
                f"{_plural(self.policy_denials, 'policy denial')}"
                if self.policy_denials else "policy boundary hit")
            parts.append(
                f"{_plural(len(self.changed_files), 'file')} changed"
                if self.has_changes else "no files changed")
        elif self.has_changes:
            parts.append(f"{_plural(len(self.changed_files), 'file')} changed")
        else:
            parts.append("no files changed")

        checks = self.verification_runs
        if checks:
            parts.append(f"{self.checks_passed}/{len(checks)} checks passed")
        elif not self.refused:
            parts.append("no checks run")

        parts.append(self.cost_text())
        return f"receipt · {self.status_label} · " + " · ".join(parts) + " · R to open"

    def sections(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """Plain rows for the receipt modal; no markup, no invented fields."""
        sections: list[tuple[str, list[tuple[str, str]]]] = []

        sections.append(("REQUEST", [
            ("prompt", self.prompt or "(not recorded)"),
        ]))

        model_rows = [
            ("model", self.model or "unknown"),
            ("tier", self.tier or "unknown"),
        ]
        for switch in self.model_switches:
            model_rows.append((
                "switch",
                f"{switch.get('old_model', '?')} → "
                f"{switch.get('new_model', '?')} "
                f"({switch.get('reason', 'unknown')})",
            ))
        sections.append(("MODEL", model_rows))

        work_rows = [
            ("tools", _join(
                [f"{name} ×{count}" for name, count in self.tools.items()],
                "none")),
            ("read / listed", _join(self.files_read)),
            ("written", _join(self.files_written)),
            ("edited", _join(self.files_edited)),
            ("directories", _join(self.dirs_created)),
        ]
        other_shell = [run for run in self.shell_runs if not run.verification]
        if other_shell:
            work_rows.append((
                "shell",
                _join([f"{run.command} {'✓' if run.success else '✗'}"
                       for run in other_shell]),
            ))
        sections.append(("WORK", work_rows))

        check_rows: list[tuple[str, str]] = []
        for run in self.verification_runs:
            check_rows.append((
                run.command,
                f"{'✓ passed' if run.success else '✗ failed'}"
                f" · {run.duration_sec:.1f}s",
            ))
        if not check_rows:
            check_rows.append(("none", "no verification command ran"))
        sections.append(("CHECKS", check_rows))

        plan_state = "denied" if self.plan_denied else (
            "blocked" if self.plan_blocked else (
                "signed" if self.plan_approved else "not requested"))
        policy_rows = [
            ("use case", self.policy_name or "none"),
            ("approvals", str(self.asks)),
            ("approval denials", str(self.ask_denials)),
            ("plan contract", plan_state),
            ("dossier holds", str(self.dossier_blocks)),
            ("policy denials", str(self.policy_denials)),
            ("refusals", str(len(self.refusals))),
            ("boundary", "hit" if self.boundary else "clear"),
        ]
        sections.append(("POLICY", policy_rows))

        cost_rows = [
            ("spent", self.cost_text()),
            ("tokens", f"{self.tokens:,} "
                       f"({self.prompt_tokens:,} prompt · "
                       f"{self.completion_tokens:,} completion)"),
            ("duration", f"{self.duration_hms} ({self.duration_sec:.1f}s)"),
        ]
        sections.append(("COST", cost_rows))

        if self.checkpoint_id:
            diff_text = (
                f"+{self.checkpoint_added} -{self.checkpoint_removed} "
                f"across {_plural(self.checkpoint_diff_paths, 'path')}"
                if self.checkpoint_diff_paths else "none")
            if self.checkpoint_diff_truncated:
                diff_text += " · truncated"
            checkpoint_rows = [
                ("id", self.checkpoint_id),
                ("files", str(self.checkpoint_files)),
                ("shell", "ran — not captured" if self.checkpoint_shell
                 else "none"),
                ("diff", diff_text),
                ("view", "V / /diff"),
                ("restore", "Z / /checkpoint"),
            ]
            if self.checkpoint_restored:
                checkpoint_rows.append(("restored", self.checkpoint_restored))
            sections.append(("CHECKPOINT", checkpoint_rows))

        for title, rows in self.extra_sections:
            sections.append((title, rows))

        risks = self.risks()
        sections.append((
            "RISKS",
            [("risk", risk) for risk in risks] or [("none", "none recorded")],
        ))

        return sections

    def to_text(self) -> str:
        """A plain-text receipt that can be pasted into a review or a PR."""
        lines = [
            f"TAMIAS RECEIPT · turn {self.number}",
            f"status: {self.status_label}",
            "",
        ]
        for title, rows in self.sections():
            lines.append(title)
            for label, value in rows:
                lines.append(f"  {label}: {value}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    # --------------------------------------------------------------- private
    def _record_success(self, name: str, target: str) -> None:
        if not target:
            return
        if name == "read_file":
            _add_unique(self.files_read, target)
        elif name in ("list_directory", "search_in_files"):
            _add_unique(self.files_read, target)
        elif name == "write_file":
            _add_unique(self.files_written, target)
        elif name == "edit_file":
            _add_unique(self.files_edited, target)
        elif name == "create_directory":
            _add_unique(self.dirs_created, target)
        elif name == "build_similar":
            _add_unique(self.files_written, target)

    def _note_refusal(self, name: str, message: object) -> None:
        line = _first_line(message) or "refused"
        if (name, line) not in self.refusals:
            self.refusals.append((name, line))


def _parse_args(arguments: object) -> dict:
    if isinstance(arguments, dict):
        return arguments
    try:
        parsed = json.loads(str(arguments or "{}"))
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _is_boundary(text: object) -> bool:
    lowered = str(text or "").lower()
    return (
        "outside company work area" in lowered
        or "outside the workspace" in lowered
        or "policy deny" in lowered
        or lowered.startswith("error: boundary")
    )


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
