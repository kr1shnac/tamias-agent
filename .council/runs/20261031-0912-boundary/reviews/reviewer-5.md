# Reviewer 5

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
