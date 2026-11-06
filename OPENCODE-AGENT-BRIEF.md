# OPENCODE-AGENT-BRIEF.md — project status for OpenCode

Date: **2026-11-06**
Branch: **`feature/liquid-glass-tui`**
Version: **`0.1.0a7`**
Purpose: this file is the fast, self-contained status and task brief for an
OpenCode agent. It says what is completed, what is broken or missing, what is
planned, and what must happen next. For the long-form handoff, read
`HANDOFF-OPENCODE.md`.

If you are prompting OpenCode, use this:

```text
Read OPENCODE-AGENT-BRIEF.md and follow only its "Next task" section. Do not
start OS sandbox, MCP, release, or publish work. Do not claim a company
boundary guarantee. Preserve offline evidence for every claim.
```

---

## 1. The one-paragraph status

The demo/agent slice is built and offline-verified: **381 tests pass**, and the
offline gate is **13 passed, 0 failed, 1 skipped**. The boundary is a real,
per-action policy fence for canonical inputs, but it is **not** an unbypassable
company guarantee. Directory-walker `deny_read` was hardened on 2026-11-06. The
remaining hard gaps are shell capability, no-policy fail-closed behavior,
company-held audit, managed-policy trust, OS sandbox, and egress control.

---

## 2. Verified completed state

Run from repo root:

```bash
cd /home/krish/Desktop/tamias-agent
.venv/bin/python -m pytest -q
./demo/check_all.sh
.venv/bin/python demo/attack_boundary.py
```

Verified 2026-11-06:

| Item | Result |
|---|---|
| Full offline suite | **381 passed** |
| Offline gate | **13 passed · 0 failed · 1 skipped** |
| Live rehearsal | **skipped** |
| Boundary probes | `check_boundary` 17/17, `showcase` 18/18 |
| Mock model | in-scope write ask-gated, out-of-scope refused |
| Adversarial harness | **6 PASS · 4 GAP · 2 NOTE**, exit code `3` |
| PyPI publish | **not published** |

Completed functionality:

- Agent core: tool dispatch, scope gate, path fence, deny-read guard, secret
  path protection, plan gate, dossier gate, ask/fail-closed behavior.
- TUI: boundary card/modals, receipt, decision card, plan modal, checkpoint
  preview/restore, frozen diff review, model picker and credits.
- Offline demos and mock provider.
- Time Travel v1, checkpoint/diff lifecycle.
- Benchmark harness, brief compiler, context index.
- Documentation and code-truth ledger.
- Boundary council review with verification and corrections.

Boundary work completed on 2026-11-06:

- `deny_read`/secret checks now apply to every path returned by
  `list_directory`, `search_in_files`, `analyze_structure`, and
  `investigate_target`.
- `test_boundary_walkers.py` covers parent-directory denial plus legitimate
  in-product control hits.
- `demo/attack_boundary.py` records the remaining failures honestly.
- `demo/check_all.sh` now runs the full offline suite.

---

## 3. Known issues and open boundary gaps

| ID | Severity | Issue | Current status | Required outcome |
|---|---|---|---|---|
| BND-02 | Critical | Shell uses `shell=True`, substring allowlist, and `run_shell` is not ask-gated | Open | Product-root shell enforcement and capability reduction; composite commands denied/ask-denied |
| BND-03 | High | Shell can resolve a relative path outside the product root | Open | No shell command may act outside the assigned product root |
| BND-04 | High | No active policy can silently remove the gate | Open | Fail closed or emit unmistakable fence-off audit |
| BND-05 | High | Audit is local and not company-held | Open | Always-on rows with resolved path, cwd, policy hash, and off-host anchor |
| BND-06 | High | `fetch_policy` trusts gateway JSON without agent-side signature verification | Open | Pin and verify signed manifest, or state that the gateway is the trust root |
| BND-07 | Medium | Domain gate is lexical and can under-block or over-block | Open | Add proportionality/false-positive probes; keep security claims separate |
| BND-08 | Medium | Plan contract is local approval, not cryptographic signing | Documented | Do not describe it as externally signed |
| BND-09 | Medium | `fetch_url` demo probe proves unknown tools are rejected, not egress control | Documented | Fix demo wording if reused |
| BND-01 | High | OS sandbox and network egress are not built | Open | Container/egress control generated from policy |

Current `demo/attack_boundary.py` GAP rows:

1. `composite shell gate`
2. `cross-project shell path`
3. `no-policy run gate`
4. `no-policy audit row`

Do not delete these rows to make the demo look clean.

---

## 4. Missing / not built

- OS/container sandbox.
- Network egress allowlist.
- MCP boundary server.
- Client-pinned manifest verification.
- Admin-owned policy file outside the repo.
- Company-held audit sink.
- Session store + resume.
- Durable Time Travel / Flight Recorder export.
- Streaming/cancel.
- Live benchmark results.
- PyPI publish/packaging decision.

Not verified:

- Live model behavior after the latest prompt and boundary changes.
- Cost savings. All dollar figures are hypothetical.
- OS-level containment. It does not exist yet.

---

## 5. Plan and priorities

### Phase 1 — finish boundary hardening: P0

1. **Shell capability reduction**
   - Enforce the policy root for shell cwd and relative paths.
   - Ask-gate `run_shell`, or remove broad interpreter execution from the shell
     allowlist.
   - Add legitimate-flight tests, not only hostile tests.
   - Do not rely on a lexical denylist for `;`, `&&`, `|`, `>`, backticks.

2. **Policy omission must be visible or impossible**
   - Either fail closed when no policy is active, or emit an obvious
     “fence off” audit row with resolved policy/company state.

3. **Audit must be checkable by the company**
   - Always-on audit rows, resolved path, cwd, policy hash, plan/session binding.
   - Add an off-host or gateway anchor. Local hash chains alone are insufficient.

4. **Managed policy trust**
   - Verify a client-pinned signed manifest, or state plainly that the gateway is
     the trust root.

### Phase 2 — production hardening: P1

5. OS/container sandbox plus egress allowlist.
6. MCP boundary server.
7. Admin-owned, shell-protected policy/audit paths.
8. Proportionality/false-positive probes.

### Phase 3 — product depth: P2

9. Session store + resume.
10. Durable Time Travel and Flight Recorder export.
11. Streaming/cancel and live benchmark.

### Phase 4 — release

12. Decide and document PyPI publish vs checkout-only.

### Product/design questions to settle

- Is the fence against the remote model, or also against the local operator?
- Governed local agent or trusted-proxy companion?
- Container-first or native sandbox?
- What is the smallest credible alpha claim?
- Does the plan contract need real cryptographic signing?

---

## 6. Next task for the next OpenCode agent

Start here. Do not skip ahead.

**Task: implement P0 #3, shell product scope and capability reduction.**

Scope:

- Keep read/search/list behavior intact.
- Make shell commands unable to reach outside the assigned product root.
- Prefer capability reduction over another lexical denylist.
- Ask-gate `run_shell` if it can mutate the product or read outside it.
- Add tests for both hostile and legitimate commands.
- Run:
  ```bash
  .venv/bin/python -m pytest -q
  ./demo/check_all.sh
  .venv/bin/python demo/attack_boundary.py
  ```
- Update `HANDOFF-OPENCODE.md`, `docs/RELEASE-STATUS.md`, and add an evidence
  file under `docs/audit/`.
- Done when:
  - composite and cross-project shell GAP rows become PASS,
  - legitimate product test commands still work,
  - the full suite has no weakened tests,
  - no text claims “unbypassable” or “company guarantee”.

Do not start OS sandbox, MCP, publishing, session resume, or P2 product depth
until this task is committed and evidence is written.

---

## 7. OpenCode-specific rules for this workspace

The repo has an `opencode.json` permission contract. Obey it; do not try to
bypass it.

Important effects:

- `.env`, `.env.*`, `.pypirc`, and `.ssh/**` are denied for reading and editing.
- `sudo`, destructive `rm -rf`, npm, pip installs, curl, wget, `env`, and
  `printenv` are denied.
- `git push`, `git remote`, `git reset`, `git clean`, `git tag`, `git switch`,
  `git checkout`, `git merge`, `git rebase`, `git stash`, `git branch`, and
  `git worktree` are denied.
- `git add -A`, `git add --all`, and `git add .` are denied.
- External directory writes are denied except `/tmp/**`.

Therefore:

- When you need to stage files, stage explicit paths only:
  ```bash
  git add path/to/file path/to/other/file
  ```
- Do not ask the user for permission if a tool call is denied; stop, report the
  denied command, and propose the user-run command.
- If a push is needed, report this command and let the user run it:
  ```bash
  git push -u github-https feature/liquid-glass-tui
  ```
- Skills and tool names change across OpenCode versions. Do not assume a
  historical skill ID still exists; list or query available skills first.

---

## 8. Hard rules from the repo

- Use the project venv: `.venv/bin/python`.
- Never print, read, commit, or log `.env`.
- Never weaken tests to force a boundary pass.
- Never use `git add -A`.
- Never present offline/mock runs as live.
- Live runs require owner approval and two consecutive passes.
- Free models are default; paid models require explicit opt-in.
- Every substantive claim needs a command and saved evidence.

---

## 9. Evidence artifacts to read before changing code

Read these in order:

1. `HANDOFF-OPENCODE.md`
2. `docs/RELEASE-STATUS.md`
3. `docs/audit/2026-11-06-boundary-hardening.md`
4. `.council/runs/20261031-0912-boundary/verification.md`
5. `.council/runs/20261031-0912-boundary/report.html`
6. `test_boundary_walkers.py`
7. `demo/attack_boundary.py`

---

## 10. Git status at time of writing

Branch `feature/liquid-glass-tui` contained local work that had not been pushed
because OpenCode denies `git push`. Do not rely on stale commit hashes; run
`git log -6 --oneline` and report the actual state before pushing.
