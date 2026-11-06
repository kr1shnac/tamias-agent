# The benchmark (D17)

**Does routing actually save credits per success?** `bench.py` is the harness
that answers it. It holds the *method*, not the *result*: never quote a number
this did not measure.

## The metric

`cost_per_success = total provider-billed USD / tasks that passed`.

Cheaper tokens are not the claim. An arm that saves money by failing more is not
cheaper, it is worse. So an arm that passes nothing has `cost_per_success = inf`,
and the comparison is always **paired** — the same tasks, run by every arm.

## The arms

| arm | model | effort | brief | what it is |
|---|---|---|---|---|
| `plain-strong` | one strong model | static | off | naive, no routing |
| `plain-cheap` | one cheap model | static | off | naive, no routing |
| `tamias-static` | the routing base model | static | off | control (routing off) |
| `tamias-full` | the routing base model | auto | on | routing + brief |
| `external-codex` | external | — | — | skipped unless wired |

`tamias-full` is the only arm with tier models configured, so it is the only one
that can switch engines. The headline comparison is `tamias-full` vs
`tamias-static`: same base model, same tasks, routing the only difference.

## The method

- Every arm runs every task; **arm order is randomized per task** (seeded, so a
  run is reproducible).
- The comparison uses a **paired bootstrap**: tasks are resampled with
  replacement and both arms are re-measured on the same resample, so the
  interval reflects task difficulty, not arm-to-arm noise.
- The output carries the point estimates **and** the CIs for the improvement and
  the pass-rate change.

## The decision gate

Routing becomes the default only if **all** hold:

1. `cost_per_success` improves by **≥ 20%**, **and**
2. the paired interval's lower bound is **> 0** (the saving is established, not a
   fluke), **and**
3. the pass-rate drop is **≤ 2 percentage points**.

If it does not clear the gate it stays **opt-in**, and the negative result is
published. A benchmark that can only ever say "yes" is not a benchmark.

## Running it

```bash
# 1. show the plan (no model calls)
.venv/bin/python bench.py --tasks bench-tasks.example.json --dry-run

# 2. a live run. Point the agent at the tamias gateway so the proxy meters it:
TAMIAS_BASE_URL=http://127.0.0.1:8000/v1 \
TAMIAS_API_KEY=vk-... \
.venv/bin/python bench.py --tasks my-tasks.json --out bench-results.json
```

A task is `{"id", "prompt", "check"}` where `check` is a shell command whose
exit status grades the run (`0` = passed). `bench-tasks.example.json` is a
template — replace its prompts and checks with tasks that a check can really
grade.

## Status — honest

**The harness and its maths are implemented and tested; no live benchmark run
has been recorded here.** Free models rate-limit (HTTP 429), so a live run must
be done deliberately, with retries, and its `bench-results.json` committed as
the evidence. Until then the routing default stays **opt-in** — which is the
correct posture: the gate has not been cleared because it has not been run.

## Tests

`test_agent.py` covers the harness: `cost_per_success` divides by successes, an
arm that passes nothing is `inf`; the paired bootstrap sees a real saving; the
gate promotes a clear saving at equal quality and refuses a saving bought with
accuracy, one too small to matter, and one not established by the interval;
`run_benchmark` runs every arm exactly once per task in a seeded order; the live
runner parses the spend line, carries the arm's model/effort/brief/tiers into the
environment, and reports the external arm as not-run rather than as a failure.
