# Council transcript — 2026-10-31 boundary review

Run: `20261031-0912-boundary`
Mode: five isolated thinking styles; fresh context for each advisor,
reviewer, and chairman.
Run notes: no simulated roles; two advisor retries are recorded in
`mapping.json` because the configured advisor model was unavailable.

## Contents

1. Framed question
2. Advisor mapping
3. Advisor answers (anonymous labels revealed after aggregation)
4. Reviews
5. Aggregate
6. Chairman verdict
7. Verification

---


## Framed question

## Decision

Review the boundary model in this repository and decide what should change, if anything, before the boundary is presented as a company guarantee. Assess whether a boundary set by a company can be bypassed or exceeded, and whether enforcement is proportionate and limited to the assigned task.

## Options

- **A. Keep the in-process dispatcher as the authority.** Close concrete gaps inside the current policy/company/product/tool/path/ask model; do not add a new isolation layer.
- **B. Keep the dispatcher as the policy layer, and add mandatory OS/container isolation plus network egress control below it.** The local process is treated as fallible; the kernel/container becomes the hard boundary.
- **C. Move authority to a trusted gateway with a client-pinned signed manifest, and treat the local agent as an untrusted UI.** Combine this with B where the work actually executes.
- **D. Something else / none of these.**

## Constraints and context given by the user

> "This boundary issue has been the part of this project for a very long time."

> "making sure that this boundary should not be bypassed if the company sets the boundary. The boundary should be concisely upheld to that particular task. It should not exceed."

> "people should not be able to bypass that."

The repository's own rule: live claims need two consecutive passes; offline and mock runs must be labelled; do not commit or push without explicit instruction.

## Materials

Read these files in the repository. Paths are relative to `/home/krish/Desktop/tamias-agent`. The excerpts below are verbatim where quoted; the files are authoritative.

### 1. The policy under review — `policies/todoinc-todo.toml`

```toml
version = "1"

[use_case]
name      = "todo-app"
root      = "company/work/todoinc/apps/todo"
company   = "todoinc"
read_only = false

[domain]
allow = ["todo", "to-do", "to do", "task", "task list", "checklist", "item", "due date"]
deny  = ["chatgpt", "chat gpt", "chatbot", "chat bot", "llm", "gpt", "openai",
         "build an agent", "crypto", "trading bot", "rag", "clone", "linkedin",
         "facebook", "instagram", "netflix", "uber", "amazon", "twitter"]

[tools]
allow = ["read_file", "search_in_files", "list_directory", "create_directory", "edit_file", "write_file", "run_shell", "update_plan", "investigate_target", "trace_feature", "analyze_structure", "build_similar", "record_unknown", "record_comparison", "finish_investigation", "boundary_accuracy", "model_performance_comparison", "reasoning_chain"]
ask   = ["write_file", "edit_file", "create_directory"]

[run_shell]
allow   = ["python3 -m pytest", "git status", "git diff", "git log"]
deny    = ["rm ", "mv ", "curl ", "wget ", "git push", "chmod ", "cat ", "ssh "]
timeout = 30

[paths]
allow_write = ["company/work/todoinc/apps/todo/**"]
deny_read   = [
  "company/work/todoinc/apps/chatbot",
  "company/work/todoinc/apps/chatbot/**",
  "company/work/todoinc/hr",
  "company/work/todoinc/hr/**",
  "**/*.pem",
]

[audit]
path = "policies/todoinc-todo.audit.jsonl"
```

### 2. The probes the team uses — `demo/check_boundary.py`

The file wires the company fence (`company/work/acme/`) and the product fence (`bots/codefix/`) and asserts:

| Probe | Expected |
|---|---|
| read/list/search/run tests inside the product | ran |
| read/search/write another project in the same company | deny |
| read `hr/salaries.csv` | deny |
| write into the product headless | ask-denied |
| shell `rm`, `curl`, `ls -la` | deny |
| read the policy file, `.env`, or a repo file outside the company | refused below the policy |
| the same write after a human says yes | ran |

### 3. The to-do probes — `demo/showcase.py`

`DOMAIN_PROBES` includes allowed requests (`build a todo app`, `sort by due date`, `refactor the task list`) and refused requests (`chatbot`, `clone linkedin`, `weather`, `hi`). `TOOL_PROBES` includes product read (allow), product write (ask), chatbot write (block), HR read (block), private key read (block), product tests (allow), `rm -rf company` (block), `git push` (block), `fetch_url` (block). The exact lists are in `demo/showcase.py`.

### 4. Enforcement code — `agent.py`

The relevant functions are:

- `resolve_in_workspace(path)` and `resolve_in_company_workspace(path, company_id)` — realpath containment, with the company id checked as a single path segment.
- `shell_escapes_company(command, company_workspace)` — token scan for `~`, `..`, and absolute paths outside the company.
- `run_shell(command)` — `subprocess.run(..., shell=True, cwd=company_workspace, env=scrubbed_env())`, with the company and secret checks before execution.
- `policy_check(tool_name, args)` — tool allow/deny, read-only, shell command-family substring allow/deny, `allow_write` / `deny_read` globs, and the `.` project-root hint.
- `policy_ask(tool_name, args)` and `_policy_gate(...)` — ask-gated tools, deny wins, audit rows.
- `dispatch_tool(tool_name, args)` — plan gate, dossier gate, policy gate, ask, checkpoint, then the tool.
- `domain_check(text)` — lexical allow/deny gate over the request text before a model call.
- `policy_audit(...)` — in-memory rows plus optional JSONL append.
- `protect_path` / `is_sensitive_path` / `refuse_secret` — `.env`, key files, and the local policy path.
- `fetch_policy` / `enter_managed_mode` — `GET /policy` from the gateway; refuses direct provider URL and non-gateway token; parses the served policy; does not verify a signature in the agent.
- `plan_write_block` — signed plan, file-list drift for writes; shell is in `PLAN_GATED_TOOLS` but is not path-scoped by the signed file list.
- `dossier_write_block` — first mutating call held until an investigation tool returns evidence.

### 5. The design's own statement — `docs/BOUNDED-AGENT.md`

Sections 3–4 and "Honest limits" state the intended layers: tool allowlist → filesystem scope → network scope → secret control → shell sandbox → audit log. The same document says: "`run_shell` is the sharp edge: without an OS sandbox ... a determined prompt-injected command can still find unguarded operators." It also says the gateway verifies the manifest signature, and "the agent does not itself check the signature — that is the gateway's job."

### 6. Current release state — `docs/RELEASE-STATUS.md`

The "What is blocked" table currently lists: live model path (latest 0/2, rate-limited), live benchmark, MCP boundary server (not built), OS sandbox (not built; "best-effort shell guard only"), and client-pinned manifest (not built; "'Bring your own gateway' bypass possible"). The full suite is 374 passing tests; the offline gate is 13 passed, 0 failed, 1 skipped.

### 7. The boundary queries the team is focusing on

These are the current acceptance probes. They are evidence of intent, not a claim that every probe is sufficient.

1. **Topic / use case:** in-scope `todo`/`task` requests reach the model; off-topic (`chatbot`, `crypto`, `clone linkedin`, `weather`, `hi`) are refused before spend; deny wins over allow.
2. **Company:** `company/work/todoinc/**` is reachable; another company id, a traversal id, or a path outside the company is refused.
3. **Product:** writes are only `company/work/todoinc/apps/todo/**`; another app, `hr/`, `*.pem`, `.env`, the policy file, and repo-root paths are refused.
4. **Read denial:** `hr/`, `chatbot/`, `*.pem` are not read, listed, searched, or returned by investigation tools.
5. **Tools:** only the allowlist runs; hard deny wins; read-only blocks every write and shell.
6. **Ask:** `write_file`, `edit_file`, `create_directory` are ask-gated; TUI **Y** runs, **N** refuses; headless refuses fail-closed; deny wins over ask.
7. **Shell:** only the named command families run; `rm`, `mv`, `curl`, `wget`, `git push`, `chmod`, `cat`, `ssh`, absolute paths outside the company, `..`, and `~` are refused; cwd is the company area; the environment is scrubbed; timeout is 30s.
8. **Paths:** absolute, relative, `..`, `~`, symlink, and `.` are resolved with realpath; a symlink pointing outside is refused.
9. **Plan / dossier:** writes outside the signed file list stop the turn; a mutating call before evidence is held; shell is signature-gated but not path-scoped.
10. **Managed policy:** `--require-proxy` refuses a direct provider URL, a provider key, or no policy; the gateway serves the policy; local policy and managed policy cannot be combined.
11. **Audit:** every gate decision is recorded (allow/deny/ask-allowed/ask-denied), bodies are redacted, and JSONL is appended when configured.
12. **Secrets:** `.env`, key files, and the policy file are never read, written, searched, or printed by the tools; the shell environment is scrubbed.

### 8. The trust questions the team wants checked

- Who is trusted: the remote model, the local user, the local Python process, the company gateway, the OS?
- Is the fence per action and fail-closed, or can one tool/shell/investigation path exceed it?
- Is the boundary the company, the product, or the task? Where do those three diverge?
- Can a model that is allowed to run tests or shell commands use that capability to mutate another project, read a denied path, reach the network, or rewrite the policy/audit?
- What is the real guarantee when the policy is a local TOML file, when managed mode trusts the gateway response, and when the agent itself can be modified by the local user?
- Which gaps are demo-blocking, which are production-blocking, and which are honest limitations that should be stated rather than "fixed" by prose?
- What evidence would prove the boundary holds, beyond the current 374-test suite and 17-probe demo?

## Current facts

No web search was used. The repository is the source of truth for this review.

## Advisor mapping


| Label | Style |
|---|---|

| A | `expansionist` |

| B | `first_principles` |

| C | `executor` |

| D | `outsider` |

| E | `contrarian` |


---


## Answer A — expansionist

# Advisor: expansionist — Answer A

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


## Answer B — first_principles

# Advisor: first_principles — Answer B

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


## Answer C — executor

# Advisor: executor — Answer C

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


## Answer D — outsider

# Advisor: outsider — Answer D

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


## Answer E — contrarian

# Advisor: contrarian — Answer E

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


## Reviews

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


## Reviewer 1

# Reviewer 1

## Review

**1. Strongest: B.** B is the only answer that *falsifies the team's own evidence* instead of adding to it: it claims `deny_read` is enforced per-*argument*, not per-file, that only `trace_feature` re-checks (`agent.py:1769-1771`), and that `demo/check_boundary.py:87-88` passes probe #4 only because the probe supplies the denied path *as* the argument — so acceptance criterion 4 in framed §7 is untested. Combined with "no `--policy` means `policy_check` returns `None`, so there is no gate at all" (`:2786-2788`), it correctly relocates the question from layer count to *against whom the fence is drawn*, which is what the A/B/C options suppress. It is also the only answer whose next step is a probe suite designed to *fail* (xfail-documented), not a fix that presumes the diagnosis.

**2. Biggest blind spot: C.** C's diagnosis is that the sole hard boundary is the local Python process checking its own inputs — then its prescription is a regex denylist over `;`, `&&`, `|`, `>` executed by that same process, and it explicitly defers B and C. That is the same class of lexical control C just demonstrated to be bypassable (`shell_escapes_company`, `agent.py:1172-1200`), and by deferring isolation it leaves the "company guarantee" claim standing on the layer it identified as fiction. Its audit finding (the JSONL is not in `PROTECTED_PATHS`) is good but undeveloped.

**3. What all five missed: the audit has no external anchor, so there is no company-held evidence.** Framed §8 asks what would prove the boundary holds; every answer answers with a local artifact — A proposes a hash-chained JSONL, C proposes adding the audit path to `PROTECTED_PATHS`, D says it is "forgeable" and stops. A hash chain written by the same user who can edit `agent.py` and truncate the file is not tamper-evident without an off-host anchor; nothing in `RELEASE-STATUS.md` shows the gateway ingesting audit rows, so in managed mode the company still holds no record. A guarantee whose only proof sits on the constrained party's disk is not a guarantee, and only A even gestures at integrity.

**4. Ranking:** B > E > C > A > D. B diagnoses the false acceptance criterion; E names the sharpest single fix (drop `python3 -m pytest`, put `run_shell` behind ask); C has the best remediation sequence but a prescription that contradicts its own diagnosis and a garbled draft line at ¶1; A is broad and dependable but its hash-chain proposal is unsound as stated; D overlaps and contradicts itself on investigation-tool coverage.

**5. Endorsed step:** one offline day writing `demo/attacks.py` with six probes *expected to succeed today* — `search_in_files` from `company/work/todoinc` (hits `hr/`, `chatbot/`), an ask-approved `conftest.py` followed by `python3 -m pytest`, and `git status; python3 -c ...` — then pasting literal pass/fail into RELEASE-STATUS "What is blocked" and deleting the words "company guarantee." It is falsifiable, costs no architecture, and tests the criterion the demo currently reports as passing. Note one consequence E misses: gating shell behind ask makes the demo's shell probes ask-denied in headless mode, so the fix changes the demo script.

*(I discounted A's and E's confidence labels; both over-tag as "High" what §4 of the framed materials marks unverified.)*


## Reviewer 2

# Reviewer 2

**1. Strongest: B.** It attacks the unstated premise — against whom is the fence drawn — instead of the layer count, and it is the only answer that makes a falsifiable claim about the *evidence* rather than the code: `deny_read` is per-argument, not per-file, so `search_in_files`/`list_directory`/`investigate_target` reach `chatbot/` and `hr/` when the denied path is not the argument, and framed §7 probe 4 passes only because the probe supplies the denied path as its argument. It also catches that `demo/check_boundary.py` accepts any `Error:` as a denial, which is a weak assertion the other four treat as proof.

**2. Biggest blind spot: C.** C asserts "Investigation tools are correctly inside `READ_TOOLS`/`PATH_ARG` … so `deny_read` covers them at the policy layer" — the direct opposite of B's finding, and stated as High confidence from a line citation that does not address nested reads. That false reassurance is worse than an omission: it would let the team keep probe 4 as-is. C also carries a visibly garbled passage inside bypass 1 ("— wait, `[design's promise🗂 in §4 example]`"), which reads as spliced rather than checked.

**3. What all five missed.** Every answer repeats framed §4/#9 — shell is signature-gated but not path-scoped — and none asks **who signs the plan and where that key lives**. The plan contract is the *only* task-scoping control; if its signing key sits in the same local user/process domain, the gate is self-attestation and the user's actual constraint ("limited to that particular task") has no enforcement at all, only prose. None noticed the corollary: `demo/showcase.py` lists `fetch_url` (block) in `TOOL_PROBES`, but no `fetch_url` tool exists in `policies/todoinc-todo.toml` — the demo's egress pass is vacuous, so "no egress layer" is even less evidenced than A–E assume.

**4. Ranking: B > E > A > D > C.** B reframes and diagnoses the evidence; E has the best composition chain (ask-approved write plants `conftest.py`, allowed pytest executes it) and the cheapest proportionate fix; A has the sharpest single payload (chained-after-allow-family, base64, data-dependent globs) plus audit integrity; D is honest and the only one naming buyer-facing legibility, but technically derivative; C is specific yet internally inconsistent.

**5. Next step.** I'd disagree with the B/C verdicts: OS isolation built over an unchanged `run_shell` still inherits the substring allowlist and still permits intra-company cross-project reads inside the container. Endorse E's minimal move, plus C's regex: drop `python3 -m pytest` from `[run_shell].allow`, put `run_shell` behind ask, and reject any second shell operator (`;`, `&&`, `|`, backtick, `>`) in one fail-closed check in `shell_escapes_company`, then rerun the 17 probes and publish B's per-file `deny_read` result as a named blocked row. That is proportionate, offline, and removes the one bypass all five agree on before anything is called a company guarantee.


## Reviewer 3

# Reviewer 3

**1. Strongest — B.** It reframes the question correctly (against whom is the fence drawn?) instead of counting layers, and its two central findings are the only ones I verified as structurally true in code: `policy_check` globs `deny_read` against a *single argument path* (agent.py:2811–2818), and `search_in_files` (1516–1554) walks the tree checking only `is_sensitive_path` per file. So probe #4 in framed §7 ("not read, listed, searched") is false whenever the argument is the parent directory — which is precisely why the demo passes. B is also alone in attacking the probes' assertion strength ("denied-below" accepting any `Error:`) and in naming "don't opt in" as bypass #1.

**2. Biggest blind spot — C.** Its primary remedy, rejecting `;`, `&&`, `|`, `>` inside `shell_escapes_company`, does not touch the escape that matters: one allowed `python3 -m pytest` executing a planted `conftest.py`. C lists that escape as bypass #1 and then defers OS isolation, so its sequencing ships a "company guarantee" resting on a regex. A broken sentence mid-argument ("— wait, `[design's promise…") also signals unfinished reasoning.

**3. What all five missed — the audit trail cannot serve as evidence.** `policy_audit` (2936–2958) returns silently when `_ACTIVE_POLICY is None`, so the ungated "don't opt in" mode B, D and E flag produces *no rows at all* — not even a record that the fence was off. Even when active it stores raw `args`, tool, decision, reason: no cwd, no resolved realpath, no policy version/hash, no session or plan binding. Hence a parent-directory search and the `hr/`/`chatbot/` reads it caused are indistinguishable from the legitimate call, and a forged row is unattributable. A proposes hash-chaining, C notes forgeability, but neither names this: the guarantee has no evidentiary substrate even after every gate is fixed — framed §8's actual question.

**4. Ranking — B > A > E > C > D.** B: verified structure plus the right reframe. A: best novel point (company code is shipped to OpenRouter by design, so reads are exfiltration) and tamper-evidence. E: the only proportionate fix (strip pytest or ask-gate shell) and a novel `git log -p apps/chatbot` probe. C: concrete but its remedy misses. D: competent summary, least new.

**5. Next step.** Run E's two-case attack file today — ask-approved `conftest.py` then `python3 -m pytest`; cwd-relative `git log -p apps/chatbot/<file>` — then either remove `python3 -m pytest` from `[run_shell].allow` (E's fix) or publish both as named rows in RELEASE-STATUS "What is blocked." Immediately after, add resolved path, cwd, policy hash and an always-on row to the audit. One edit removes the sharpest bypass; the audit change is what makes any future claim checkable.


## Reviewer 4

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


## Reviewer 5

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


## Aggregate

# Aggregate

Anonymous labels map to styles in `mapping.json`; the mapping was hidden from
the reviewers. Votes are advisory, not proof.

## Ranking aggregation

| Answer | R1 | R2 | R3 | R4 | R5 | Average position | Rank |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 1 | 1 | 1 | 1 | 1 | 1.00 | 1 |
| E | 2 | 2 | 3 | 2 | 2 | 2.20 | 2 |
| A | 4 | 3 | 2 | 3 | 3 | 3.00 | 3 |
| C | 3 | 5 | 4 | 5 | 4 | 4.20 | 4 |
| D | 5 | 4 | 5 | 4 | 5 | 4.60 | 5 |

Source orders:

1. B > E > C > A > D
2. B > E > A > D > C
3. B > A > E > C > D
4. B > E > A > D > C
5. B > E > A > C > D

## Tallies

- Strongest answer: **B** — 5/5.
- Biggest blind spot: **C** — 5/5.
- Answer blamed most for the false reassurance that investigation tools are
  covered by `deny_read`: **C** (and **D** by two reviewers).

## What the reviewers said all five missed

1. **No external audit anchor / no company-held evidence.** R1, R3 and R5 all
   noted that a hash-chained local JSONL is still written by the audited party;
   the company receives nothing. R3 added that rows vanish when no policy is
   active and do not carry resolved path, cwd, policy hash, or plan binding.
2. **The egress demo probe is partly vacuous.** R2 noted `demo/showcase.py`
   blocks `fetch_url`, but `fetch_url` is not in the policy allow list; it
   proves unknown tools are rejected, not that network egress is controlled.
3. **The plan-signed “task” is not off-host attestation.** R2 asked who signs
   the plan and where the key lives. Verification confirmed it is a local
   `signed by user` flag, not cryptographic signing.
4. **Over-blocking / proportionality.** R4 noted the same substring deny that
   blocks malicious commands also blocks legitimate ones (`pytest -k
   "confirm parser"` contains `rm `). No advisor measured false positives.

## Interpretation

The council's strongest useful output is not a vote. It is that the team’s
evidence does not test composition or adversarial input, and that the request
“should not exceed” also has a false-positive side: work is wrongly refused.


## Chairman verdict

# Chairman verdict (raw)

**1. Verdict.** Partly. The dispatcher is a real per-action policy layer: plan → dossier → policy → ask on every tool (`agent.py:2984-3010`), deny beats ask, headless ask fails closed, realpath containment, scrubbed shell environment. [FACT] It is not a company guarantee. A company-set boundary can be bypassed **and** exceeded today, four independent ways:

- **The read fence is per-argument, not per-file.** `policy_check` globs `deny_read` against one argument (`agent.py:2811-2818`); `search_in_files` then walks the tree checking only `is_sensitive_path` (`1550-1554`). `search_in_files("salary", "company/work/todoinc")` returns `hr/` content. Probe #4 (framed §7) is false whenever the denied path is not the argument — and `demo/check_boundary.py:87-88` passes only because it is. This is the strongest evidence because the demo reports it as passing.
- **Opt-out by omission.** No policy → `policy_check` returns `None` (`2786-2788`) and `policy_audit` writes nothing (`2939-2940`); no company id → the company fence degrades to the workspace fence (`1473-1478`).
- **Shell.** `python3 -m pytest` is allowed (`policies/todoinc-todo.toml:30`) and `run_shell` is not ask-gated (`:27`); it runs `shell=True` (`1251-1258`). A planted `conftest.py` is arbitrary code, and no egress layer exists.
- **Managed mode.** `fetch_policy` verifies nothing (`2698-2723`); bring-your-own-gateway is conceded (`RELEASE-STATUS.md:41`).

Company ≠ product ≠ task: product is write-scope only (`toml:36`); task is lexical `domain_check`, self-declared "not a security boundary" (`2873-2875`), with shell outside the plan's file list (`2306-2311`). The scope asked to be "concise" is the weakest.

**2. Direction: A→B.** Keep the dispatcher as the policy layer and close the concrete gaps now (A); make OS/container isolation plus egress control the mandatory gate before any guarantee (B). This is a sequence, not a compromise. Reject pure A: a process that owns its TOML can never satisfy "people cannot bypass." Reject pure B now: a container over an unchanged `run_shell` still permits intra-company cross-project reads inside it, and it would be generated from policy semantics that are currently wrong. Reject C now: right only if the adversary is the employee, and client pinning is unbuilt (`RELEASE-STATUS.md:41`). Strongest counter — "B is the only thing that makes the guarantee true, so don't spend a day on A" — fails because the demo can be honest today, and B is required before the *word* "guarantee," not before the demo.

**3. Agreement and disagreement.** Agreed: the deterministic gates work for the probed forms; shell is the sharp edge; the operator is trusted and can bypass; task scope is lexical; no egress layer exists. Genuine disagreement: E calls the conftest escape and cross-project read demo-blocking; A, C and D say nothing is if labelled. I take E's fact but not his conclusion — the sentence "the boundary does not exceed" is false and must go or be fixed, but the demo is not blocked by showing the failure honestly. On order I take C over A/D: cut capability first, isolate second.

**4. Blind spots.** Biggest single error: C (and D) assert that `READ_TOOLS`/`PATH_ARG` membership means `deny_read` covers investigation tools. It does not — only the argument is globbed (`2811-2818`), while the walker checks only `is_sensitive_path` (`1550-1554`). That false reassurance is what keeps probe #4 green.

What all five missed:
- **The audit has no external anchor.** Rows are written by the audited process, vanish when no policy is active (`2939-2940`), carry no resolved path, cwd or policy hash (`2942-2949`), and append errors are swallowed (`2956-2958`). The company holds no evidence; a hash chain written by the same user is not tamper-evident. Consequence: the guarantee is unobservable to its owner, and the anchor is production-blocking.
- **Over-blocking / proportionality.** Deny is whole-command substring: `pytest -k "confirm parser"` contains `rm ` and is refused (`2804`); `domain_check("refactor the storage layer")` contains `rag` and is refused (`2852-2860`). No advisor measured false positives. "Should not exceed" also means not refusing legitimate work; add a false-positive probe set.
- **Whose key signs the plan.** The plan is the only task control; a local key makes task scope self-attestation. "Limited to this task" stays prose until verified off-host.
- **The egress probe is vacuous:** `demo/showcase.py:211` blocks `fetch_url`, absent from the policy allowlist (`toml:26`) — it proves unknown tools are rejected, not that egress is controlled.

**5. The real guarantee.** (a) Today, offline, operator-controlled, with a policy loaded: a per-action, deny-wins, fail-closed policy fence against a non-adversarial model — canonical tool/path/domain/ask probes refused, realpath containment, secrets and policy file refused, scrubbed shell env, audit rows per gate decision. Evidence: 374 tests (`RELEASE-STATUS.md:52`) and the 17-probe demo (framed §8); I ran neither, and the live path is 0/2 rate-limited (`:37`). Claim "product-level policy fence, best-effort at shell." (b) Production-blocking: no-policy default; per-argument `deny_read`; shell interpreter escape and absent egress; unpinned managed policy/BYO gateway; unanchored audit; local plan key. (c) Document, don't fix: the operator is root of trust and can edit `agent.py`; `domain_check` is lexical; shell cannot be fully sandboxed from Python (`1175-1179`); company code goes to the remote model by design.

**6. One day, then two weeks.** Ship `demo/attacks.py` (offline, no model) plus the capability cuts. **Pass** = exit 0 with: a search from `company/work/todoinc` returns zero `hr/`/`chatbot/` lines but at least one legitimate `apps/todo/` hit; a planted `conftest.py` followed by `python3 -m pytest` is ask-denied headless and writes no marker; a bounded run with no active policy refuses rather than returning `None`; `run_shell` is ask-gated. **Fail** = any attack prints ALLOWED, or the legitimate control hit disappears. Then rerun the suite and update the probes' expectations (shell allow → ask). Two weeks: day 1 as above; days 2-3 always-on audit rows with resolved path/cwd/policy hash and an off-host sink, audit path protected; days 4-5 manifest verification and pinning plus a downgrade test; week 2 container/egress spike generated from the same policy, attacks harness inside it, proportionality probes, two consecutive live passes before any guarantee sentence.

**7. Not yet.** Not isolation first — it inherits the read gap and substring shell. Not the pinned manifest before the audit anchor — a pinned policy over a forgeable trail proves nothing. Not a hash-chained JSONL as the integrity fix. Not another lexical denylist (`;`, `&&`, `|`, `>`) — the same failing class; cut capability instead. No "company guarantee," "people cannot bypass," or shell-containment claims; no push, retag, or live-pass claim.

Chairman's one-line verdict: The dispatcher is a sound policy fence against the model and a fiction against the operator — fix the false read claim and the shell capability now, and earn the word "guarantee" only with kernel isolation, egress control, and an off-host audit anchor.

Next action: Run the day-1 `demo/attacks.py` offline and publish its literal pass/fail rows in `RELEASE-STATUS.md` before any guarantee language is drafted.


## Verification

# Verification of high-impact council claims

Checked on 2026-10-31 against this repository. Line numbers are approximate
because this file is evidence for a hand-off, not a substitute for reading the
code.

Full suite after the check: **374 passed in 16.74s**
(`.venv/bin/python -m pytest -q`). No live model call was made.

## 1. `deny_read` is per-argument, not per-file

**Status: CONFIRMED, with a correction to the council wording.**

Evidence in code:

- `policy_check` globs the `deny_read` list against the single path argument
  passed to the tool (`agent.py`, policy path section around `DENY READ`).
  It does not glob or filter the paths a directory tool later returns.
- `search_in_files` resolves only its `directory` argument, then walks the tree
  and skips only `is_sensitive_path(file_path)` per file.
- `analyze_structure` walks a directory and includes `.py`, `.js`, `.ts`
  files under it with no per-file `deny_read` check.

Offline check (policy `policies/todoinc-todo.toml`, `COMPANY_ID=todoinc`):

```text
policy_check(search_from_company_root): None
chatbot_py_returned: True
hr_csv_returned: False
analyze_from_company_root: None
analyze_lists_chatbot: True
```

Confirmed consequence: a call like `search_in_files("def ",
"company/work/todoinc")` or `analyze_structure("company/work/todoinc")`
passes the policy gate when the denied directory is nested rather than supplied
as the argument.

Correction: for the current sample tree, `search_in_files` did **not** return
`company/work/todoinc/hr/salaries.csv`, because `search_in_files` scans only
`.py`, `.txt`, `.md`, `.json`, `.js`, `.ts`, `.html`, `.css` and `salaries.csv`
is a `.csv`. It did return `apps/chatbot/src/bot.py`, which is in
`paths.deny_read`. So the council's read-bypass claim is confirmed; its
specific claim that `search_in_files` returns HR salary CSV content is
contradicted for this fixture.

## 2. Shell allow/deny is substring-based and `run_shell` is not ask-gated

**Status: CONFIRMED.**

Evidence:

- `policy_check` accepts a `run_shell` command if it contains any
  `[run_shell].allow` substring, and denies it if it contains any
  `[run_shell].deny` substring.
- `run_shell` executes `subprocess.run(command, shell=True, cwd=..., env=...)`.
- `policies/todoinc-todo.toml` puts only `write_file`, `edit_file`, and
  `create_directory` in `[tools] ask`; `run_shell` is absent.
- `shell_escapes_company` scans tokens for `~`, `..`, absolute paths and secret
  names. It does not reject shell operators after an allowed family.

Offline gate check (command not executed):

```text
policy_check(shell_composite): None
policy_ask(run_shell): None
policy_check(shell_log_other_app): None
```

Confirmed consequence: the policy layer currently passes
`python3 -m pytest -q; python3 -c ...` and
`git log -p apps/chatbot/src/bot.py` before execution. Whether the operating
system allows the later action to succeed is a separate, unbuilt layer.

## 3. Managed mode does not verify a signed manifest in the agent

**Status: CONFIRMED by code inspection.**

- `fetch_policy` performs `GET /policy`, parses JSON, and returns
  `payload["policy"]`.
- A grep of `agent.py` for `verify/signature/public_key/pin` in the policy-fetch
  path found no signature verification.
- `docs/RELEASE-STATUS.md` already records `Client-pinned manifest: not built`.

Consequence: managed mode is only as strong as the transport plus the gateway
trust boundary. Saying the manifest is verified by the gateway is honest; saying
the agent verifies it is not.

## 4. No active policy means no policy gate and no audit row

**Status: CONFIRMED.**

- `policy_check` returns `None` when `_ACTIVE_POLICY is None`.
- `policy_audit` returns immediately when `_ACTIVE_POLICY is None`.
- `resolve_in_company_workspace` degrades to the workspace fence when no
  company id is set.

Consequence: a run that omits or bypasses policy (for example `--unbounded`, or
a checkout whose deployment default policy path is absent) has no tool/path/
shell gate and is not recorded in the policy audit trail as “fence off.”

## 5. The plan contract is local human approval, not cryptographic signing

**Status: CONFIRMED.**

- `agent.py` records `contract_line = "contract: signed by user"` when a user
  approves a plan.
- No key material, signature, public-key pin, or off-host attestation was
  found in the plan-contract path.

Consequence: the plan contract can scope writes when the TUI is used, but it is
self-attested in the same local trust domain. Do not describe it as externally
signed.

## 6. The `fetch_url` demo probe does not prove egress control

**Status: CONFIRMED.**

- `demo/showcase.py` contains a `fetch_url` probe.
- `fetch_url` is not in `policies/todoinc-todo.toml` `[tools].allow`, so the
  probe shows an unknown/disallowed tool is rejected.
- It does not show that a shell network command is blocked.

Consequence: describe that probe as “unknown tool rejected,” not as “network
egress blocked.”

## 7. Test counts and claims

**Status: CONFIRMED for this run only.**

- `.venv/bin/python -m pytest -q`: **374 passed in 16.74s**.
- No live model run was executed for this council/report, so no live-pass claim
  is made.
- The adversarial composition probes above were code inspection and a
  read-only/offline Python helper, not `demo/check_all.sh`.

## Final correction applied to the council verdict

The council's central conclusion stands: the in-process fence is real per
action for canonical probes, but it is not a company guarantee and can be
exceeded. The wording must be narrowed:

- Confirmed: nested denied reads and company-wide shell are real gaps.
- Corrected: `search_in_files` did not return `.csv` HR content in the sample
  tree; the commission was denial of nested non-CSV sensitive files, notably
  `chatbot/src/bot.py`, and path listing in analysis.
- Unverified by execution: the exact network/execution effect of the permitted
  composite shell commands. Running them was deliberately not part of this
  verification.
