# Reviewer 4

## 1. Strongest — **B**

B is the only answer that falsifies a probe the team believes passes: `deny_read` is per-*argument*, not per-file, so `search_in_files("token", "company/work/todoinc")` reaches `chatbot/` and `hr/` — the demo passes only because the probe supplies the denied path *as* the argument (framed §7.4, `demo/check_boundary.py`). Paired with "no `--policy` ⇒ `policy_check` returns `None`" and the anti-model-vs-anti-employee reframe, it answers the user's real question rather than counting layers. Weakness: Option D defers the decision and proposes no remediation.

## 2. Biggest blind spot — **C**

C asserts investigation tools are "correctly" inside `READ_TOOLS`/`PATH_ARG`, i.e. that `deny_read` covers them — the exact claim B refutes with line numbers — and never checks the per-file case. Worse, its remedy (reject `;`, `&&`, `|`, backticks, `>`) is another lexical denylist, the same control class that already failed; `$(...)`, newlines, and an allowed `sh -c` walk past it. It also ships an unedited draft artifact and mojibake mid-sentence, which in a document about guarantees is evidence of care level.

## 3. What all five missed

**Over-blocking.** The user asks twice that the boundary "not exceed" and be "concisely upheld to that particular task"; all five read that only as scope creep — the agent doing too much. None measured the reverse: legitimate work being refused. Because shell deny is a whole-command substring match and deny wins, `python3 -m pytest -k "confirm …"` contains `rm ` and is refused; a valid todo request that mentions a denied token in passing (`"refactor the task list to drop the openai stub"`) is refused before spend. No probe, no false-positive rate — so no answer can speak to *proportionality*, only strictness, which is half the question.

## 4. Ranking

**B > E > A > D > C** — B falsifies a claimed-passing probe and reframes the adversary; E has the sharpest exploit chain (ask-approved `conftest.py` → allowed `pytest` → arbitrary code) plus the only remedy that reduces capability instead of filtering strings; A is thorough and correctly flags the missing `[network]` layer and forgeable audit, but its shell claim is now common ground; D is honest and useful on jargon, but self-contradicts on `deny_read` coverage; C is last: corrupted text, a false assurance, and a fix in the failed idiom.

## 5. Next step I'd endorse

Not the probe-suite-first step four of five propose — that leaves a documented arbitrary-code path live while the claim is being sold. Instead: **ask-gate `run_shell` and remove `python3 -m pytest` from the allow list**, accepted by one new offline probe asserting a planted `conftest.py` is never executed. It is under a day, removes the highest-severity bypass by capability reduction rather than string matching, needs no new architecture, and keeps every deterministic gate the suite already proves. Claim "product-level, best-effort at shell" until B/OS isolation exists.
