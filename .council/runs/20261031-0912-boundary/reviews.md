# Anonymous reviews

Five independent reviews of `anonymous-answers.md`. Labels A-E refer to that
file, not to the advisors' thinking styles.

---

## Reviewer 1

## Review

**1. Strongest: B.** B is the only answer that *falsifies the team's own evidence* instead of adding to it: it claims `deny_read` is enforced per-*argument*, not per-file, that only `trace_feature` re-checks (`agent.py:1769-1771`), and that `demo/check_boundary.py:87-88` passes probe #4 only because the probe supplies the denied path *as* the argument — so acceptance criterion 4 in framed §7 is untested. Combined with "no `--policy` means `policy_check` returns `None`, so there is no gate at all" (`:2786-2788`), it correctly relocates the question from layer count to *against whom the fence is drawn*, which is what the A/B/C options suppress. It is also the only answer whose next step is a probe suite designed to *fail* (xfail-documented), not a fix that presumes the diagnosis.

**2. Biggest blind spot: C.** C's diagnosis is that the sole hard boundary is the local Python process checking its own inputs — then its prescription is a regex denylist over `;`, `&&`, `|`, `>` executed by that same process, and it explicitly defers B and C. That is the same class of lexical control C just demonstrated to be bypassable (`shell_escapes_company`, `agent.py:1172-1200`), and by deferring isolation it leaves the "company guarantee" claim standing on the layer it identified as fiction. Its audit finding (the JSONL is not in `PROTECTED_PATHS`) is good but undeveloped.

**3. What all five missed: the audit has no external anchor, so there is no company-held evidence.** Framed §8 asks what would prove the boundary holds; every answer answers with a local artifact — A proposes a hash-chained JSONL, C proposes adding the audit path to `PROTECTED_PATHS`, D says it is "forgeable" and stops. A hash chain written by the same user who can edit `agent.py` and truncate the file is not tamper-evident without an off-host anchor; nothing in `RELEASE-STATUS.md` shows the gateway ingesting audit rows, so in managed mode the company still holds no record. A guarantee whose only proof sits on the constrained party's disk is not a guarantee, and only A even gestures at integrity.

**4. Ranking:** B > E > C > A > D. B diagnoses the false acceptance criterion; E names the sharpest single fix (drop `python3 -m pytest`, put `run_shell` behind ask); C has the best remediation sequence but a prescription that contradicts its own diagnosis and a garbled draft line at ¶1; A is broad and dependable but its hash-chain proposal is unsound as stated; D overlaps and contradicts itself on investigation-tool coverage.

**5. Endorsed step:** one offline day writing `demo/attacks.py` with six probes *expected to succeed today* — `search_in_files` from `company/work/todoinc` (hits `hr/`, `chatbot/`), an ask-approved `conftest.py` followed by `python3 -m pytest`, and `git status; python3 -c ...` — then pasting literal pass/fail into RELEASE-STATUS "What is blocked" and deleting the words "company guarantee." It is falsifiable, costs no architecture, and tests the criterion the demo currently reports as passing. Note one consequence E misses: gating shell behind ask makes the demo's shell probes ask-denied in headless mode, so the fix changes the demo script.

*(I discounted A's and E's confidence labels; both over-tag as "High" what §4 of the framed materials marks unverified.)*

---

## Reviewer 2

**1. Strongest: B.** It attacks the unstated premise — against whom is the fence drawn — instead of the layer count, and it is the only answer that makes a falsifiable claim about the *evidence* rather than the code: `deny_read` is per-argument, not per-file, so `search_in_files`/`list_directory`/`investigate_target` reach `chatbot/` and `hr/` when the denied path is not the argument, and framed §7 probe 4 passes only because the probe supplies the denied path as its argument. It also catches that `demo/check_boundary.py` accepts any `Error:` as a denial, which is a weak assertion the other four treat as proof.

**2. Biggest blind spot: C.** C asserts "Investigation tools are correctly inside `READ_TOOLS`/`PATH_ARG` … so `deny_read` covers them at the policy layer" — the direct opposite of B's finding, and stated as High confidence from a line citation that does not address nested reads. That false reassurance is worse than an omission: it would let the team keep probe 4 as-is. C also carries a visibly garbled passage inside bypass 1 ("— wait, `[design's promise🗂 in §4 example]`"), which reads as spliced rather than checked.

**3. What all five missed.** Every answer repeats framed §4/#9 — shell is signature-gated but not path-scoped — and none asks **who signs the plan and where that key lives**. The plan contract is the *only* task-scoping control; if its signing key sits in the same local user/process domain, the gate is self-attestation and the user's actual constraint ("limited to that particular task") has no enforcement at all, only prose. None noticed the corollary: `demo/showcase.py` lists `fetch_url` (block) in `TOOL_PROBES`, but no `fetch_url` tool exists in `policies/todoinc-todo.toml` — the demo's egress pass is vacuous, so "no egress layer" is even less evidenced than A–E assume.

**4. Ranking: B > E > A > D > C.** B reframes and diagnoses the evidence; E has the best composition chain (ask-approved write plants `conftest.py`, allowed pytest executes it) and the cheapest proportionate fix; A has the sharpest single payload (chained-after-allow-family, base64, data-dependent globs) plus audit integrity; D is honest and the only one naming buyer-facing legibility, but technically derivative; C is specific yet internally inconsistent.

**5. Next step.** I'd disagree with the B/C verdicts: OS isolation built over an unchanged `run_shell` still inherits the substring allowlist and still permits intra-company cross-project reads inside the container. Endorse E's minimal move, plus C's regex: drop `python3 -m pytest` from `[run_shell].allow`, put `run_shell` behind ask, and reject any second shell operator (`;`, `&&`, `|`, backtick, `>`) in one fail-closed check in `shell_escapes_company`, then rerun the 17 probes and publish B's per-file `deny_read` result as a named blocked row. That is proportionate, offline, and removes the one bypass all five agree on before anything is called a company guarantee.

---

## Reviewer 3

**1. Strongest — B.** It reframes the question correctly (against whom is the fence drawn?) instead of counting layers, and its two central findings are the only ones I verified as structurally true in code: `policy_check` globs `deny_read` against a *single argument path* (agent.py:2811–2818), and `search_in_files` (1516–1554) walks the tree checking only `is_sensitive_path` per file. So probe #4 in framed §7 ("not read, listed, searched") is false whenever the argument is the parent directory — which is precisely why the demo passes. B is also alone in attacking the probes' assertion strength ("denied-below" accepting any `Error:`) and in naming "don't opt in" as bypass #1.

**2. Biggest blind spot — C.** Its primary remedy, rejecting `;`, `&&`, `|`, `>` inside `shell_escapes_company`, does not touch the escape that matters: one allowed `python3 -m pytest` executing a planted `conftest.py`. C lists that escape as bypass #1 and then defers OS isolation, so its sequencing ships a "company guarantee" resting on a regex. A broken sentence mid-argument ("— wait, `[design's promise…") also signals unfinished reasoning.

**3. What all five missed — the audit trail cannot serve as evidence.** `policy_audit` (2936–2958) returns silently when `_ACTIVE_POLICY is None`, so the ungated "don't opt in" mode B, D and E flag produces *no rows at all* — not even a record that the fence was off. Even when active it stores raw `args`, tool, decision, reason: no cwd, no resolved realpath, no policy version/hash, no session or plan binding. Hence a parent-directory search and the `hr/`/`chatbot/` reads it caused are indistinguishable from the legitimate call, and a forged row is unattributable. A proposes hash-chaining, C notes forgeability, but neither names this: the guarantee has no evidentiary substrate even after every gate is fixed — framed §8's actual question.

**4. Ranking — B > A > E > C > D.** B: verified structure plus the right reframe. A: best novel point (company code is shipped to OpenRouter by design, so reads are exfiltration) and tamper-evidence. E: the only proportionate fix (strip pytest or ask-gate shell) and a novel `git log -p apps/chatbot` probe. C: concrete but its remedy misses. D: competent summary, least new.

**5. Next step.** Run E's two-case attack file today — ask-approved `conftest.py` then `python3 -m pytest`; cwd-relative `git log -p apps/chatbot/<file>` — then either remove `python3 -m pytest` from `[run_shell].allow` (E's fix) or publish both as named rows in RELEASE-STATUS "What is blocked." Immediately after, add resolved path, cwd, policy hash and an always-on row to the audit. One edit removes the sharpest bypass; the audit change is what makes any future claim checkable.

---

## Reviewer 4

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

---

## Reviewer 5

## 1. Strongest

**Answer B.** It is the only answer that finds a bypass which survives the team's *intended* probes and then explains why the suite is green: `deny_read` is checked per argument, not per returned file, so `search_in_files("token", "company/work/todoinc")` reaches `chatbot/` and `hr/` while `demo/check_boundary.py` passes only because the probe hands in the denied path *as* the argument (framed §7 probe 4). That is a claim about the evidence, not another restatement of the "sharp edge" line `docs/BOUNDED-AGENT.md` already concedes. Its reframing — "against whom is the fence drawn?" — is the right question, and it is the only answer that treats the local user's trust status as the load-bearing assumption rather than a footnote.

## 2. Biggest blind spot

**Answer C.** Its headline remedy — reject commands containing `;`, `&&`, `|`, backticks, `>` — is another lexical denylist, exactly the class of guard C just showed failing, and it leaves the strongest escape untouched: an ask-approved `conftest.py` executed by the allowed `python3 -m pytest` contains no operator at all. C then defers OS isolation as work that "would be built on an unfixed shell layer," letting the weakest fix justify postponing the fix that would hold. (¶1 also ships a visible unfinished fragment — `— wait, [design's promise…]` — which weakens trust in the rest of its line citations.)

## 3. What all five missed

Every answer answers framed §8's "what evidence would prove the boundary holds?" with **local** artifacts: tests, probes, a tamper-evident log. None notices that the party setting the boundary never receives any of it. A hash-chains the JSONL, but the same user writes, truncates and re-seeds that chain; C would add the audit path to `PROTECTED_PATHS`, which binds the agent, not the user. Combined with `fetch_policy` verifying nothing and pinning no version, the company cannot detect a downgraded policy or a rewritten trail. So even after B's or E's fixes land, "the company set this boundary" remains unverifiable *by the company* — no anchored log head, no attestation, no signed policy version. The guarantee is unobservable to its owner.

## 4. Ranking

**B, E, A, C, D.** B for the evidence-beating finding; E for the cheapest correct fix (drop `python3 -m pytest` from `[run_shell].allow`, put shell behind ask) and the novel `git log -p apps/chatbot/…` relative read; A for solid shell forensics that nonetheless recommends the kernel layer while missing the read gap; C for a real escape and a self-defeating remedy; D for restating others and contradicting itself on `deny_read` within one paragraph.

## 5. Next step

Run three probes offline — B's `search_in_files` from the company root, E's ask-approved `conftest.py` + `python3 -m pytest`, E's `git log -p apps/chatbot/<file>` — and publish pass/fail rows in `RELEASE-STATUS.md` before any "company guarantee" sentence is drafted. They need no architecture change, and their outcome decides the label under the repo's own two-pass rule; ship the `[run_shell].allow` edit in the same commit.
