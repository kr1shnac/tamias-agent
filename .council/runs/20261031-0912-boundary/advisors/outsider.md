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
