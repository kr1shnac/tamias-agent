# HANDOFF-OPENCODE.md — read this before touching the code

This is the hand-off file for the incoming maintainer. It is written so it can be
given directly to another coding agent (including OpenCode) as part of the task
prompt. It says what is finished, what is only apparently finished, what is
pending, and what order to work in.

Date of this update: **2026-11-06**.
Branch: **`feature/liquid-glass-tui`**.
Version: **`0.1.0a7`**.
Status: **offline verified; live model path not re-verified after the latest
prompt/boundary changes; `company guarantee` must not be claimed yet.**

Companion quick brief for OpenCode: **`OPENCODE-AGENT-BRIEF.md`**.

---

## 1. Read this in this order

1. `AGENTS.md` — repo rules, hard `.env` rule, test commands.
2. `docs/RELEASE-STATUS.md` — what is built, published, blocked.
3. `docs/BOUNDED-AGENT.md` — boundary design and its honest limits.
4. `.council/runs/20261031-0912-boundary/transcript.md` — full five-advisor
   council review of the boundary.
5. `.council/runs/20261031-0912-boundary/verification.md` — checked with code
   and tests. Read the correction section before repeating any council claim.
6. `demo/PRESENT.md` and `demo/live_show.sh` — demo/rehearsal instructions.
7. `docs/FRONTEND_REFERENCE.md` — TUI and boundary contract.
8. `docs/audit/claims.md` — code-truth ledger.

---

## 2. Verified state of the repo

Verified on 2026-11-06:

```bash
cd /home/krish/Desktop/tamias-agent
.venv/bin/python -m pytest -q
./demo/check_all.sh
```

Results:

- **Full suite:** `381 passed in 16.10s`.
- **Offline gate:** `13 passed · 0 failed · 1 skipped · 31s`.
  The skip is `live rehearsal`.
- Static check: 18 tools, prompt within budget, policies loaded.
- Boundary probes: `check_boundary` 17/17, `showcase` 18/18.
- Mock model: out-of-scope write refused; in-scope write ask-gated and headless
  fail-closed.
- **No live model run was performed for this handoff.** The latest recorded live
  state is the blocked/rate-limited one in `docs/RELEASE-STATUS.md`; do not
  upgrade that sentence without two consecutive passes.

Offline evidence files:

- `.council/runs/20261031-0912-boundary/report.html`
- `.council/runs/20261031-0912-boundary/transcript.md`
- `.council/runs/20261031-0912-boundary/verification.md`

---

## 3. What is done

The core demo/agent slice exists and is tested:

- Agent tool dispatch, scope gate, path fence, deny-read/sensitive-path guard,
  shell guard, plan contract, dossier gate, ask/fail-closed behaviour.
- TUI: boundary card/modals, receipt, decision card, plan modal, checkpoint
  preview/restore, frozen diff review (`V` / `/diff`), model picker and credits.
- Offline demos and mock provider for honest non-live rehearsal.
- Benchmark harness, brief compiler, context index, Time Travel v1.
- Documentation for the demo runbook, boundary contract, release status,
  routes, pricing, and audit claims.
- A five-advisor boundary council review with verification. The output is not
  marketing; it says what the boundary does not prove.

If a future change claims something new, it needs a command and a saved output
in `docs/audit/`, not prose.

---

## 4. The boundary verdict you must not skip

The council verdict, after verification:

> The dispatcher is a sound policy fence against the model and a fiction
> against the operator — fix the false read claim and the shell capability now,
> and earn the word “guarantee” only with kernel isolation, egress control, and
> an off-host audit anchor.

Verified findings:

- **Directory-walker deny_read is now enforced per returned path.** The original
  parent-search bypass is fixed in `list_directory`, `search_in_files`,
  `analyze_structure`, and `investigate_target`; `trace_feature` already
  checked followed files. Regressions are covered by
  `test_boundary_walkers.py`.
- Offline adversarial harness: `demo/attack_boundary.py` currently reports
  **6 PASS · 4 GAP · 2 NOTE** and exits `3`. The remaining gaps are shell
  composition, cross-project shell, no-policy fail-closed mode, and no-policy
  audit rows.
- `run_shell` uses `shell=True`, the shell allowlist is substring-based, and
  `run_shell` is not ask-gated in `policies/todoinc-todo.toml`.
- There is no OS sandbox, container, or network egress control.
- A run with no active policy can fall back to an ungated mode.
- `fetch_policy` trusts gateway JSON; the agent does not verify a signature.
- The audit trail is local, incomplete, and not received by the company.
- The plan contract is local human approval (`signed by user`), not
  cryptographic signing.
- `fetch_url` in the demo proves unknown tools are rejected, not that egress is
  blocked.

Therefore, until P0 work is complete, say:

- ✅ “offline policy fence; canonical probes blocked”
- ✅ “per-action fail-closed asks for the listed write tools”
- ❌ “unbypassable”
- ❌ “company guarantee”
- ❌ “network is controlled”
- ❌ “live path verified today”

---

## 5. Pending work, in order

### P0 — before claiming any boundary guarantee

| # | Task | Done when |
|---|---|---|
| 1 | Add `demo/attack_boundary.py`: offline, report-only composition probes. | **Done 2026-11-06.** Report-only harness exits `3` with known gaps instead of pretending the boundary is complete. |
| 2 | Make `deny_read`/secret checks apply to every **returned** path from directory, search, investigate, analyze, and list tools. | **Done 2026-11-06.** `test_boundary_walkers.py` covers parent-directory searches, analysis, listing, and investigation with in-product control hits. |
| 3 | Reduce shell capability: enforce the policy root for shell cwd/relative paths; ask-gate `run_shell`, or restrict to an explicit non-interpreter prefix. | A composite command is denied/ask-denied headless; no model-written code path is silently executable. |
| 4 | Make policy omission fail closed, or emit an unmistakable “fence off” audit row with resolved policy/company state. | No run can execute with the gate silently absent. |
| 5 | Make the audit useful and company-held: always-on rows, resolved path, policy hash, cwd, plan/session binding, off-host anchor or gateway sink. | The company can detect downgrade, stop, or missing rows independent of the endpoint. |
| 6 | Managed mode: client-pinned signed manifest verification, or state plainly that the gateway is the trust root. | A BYO-gateway/downgraded policy cannot start a bounded run. |

### P1 — production hardening

| # | Task | Done when |
|---|---|---|
| 7 | OS/container sandbox and egress allowlist generated from the same policy. | In-container attack harness cannot read outside product or reach the network. |
| 8 | MCP boundary server integration. | A remote agent cannot exceed the local boundary through the MCP path. |
| 9 | Admin-owned policy file outside the repo; policy/audit protected from the agent's shell. | The agent cannot rewrite its own boundary or trail. |
| 10 | False-positive/proportionality probes for the domain and shell denylists. | `pytest -k "confirm parser"` is not refused because it contains `rm `. |

### P2 — product and release

| # | Task | Done when |
|---|---|---|
| 11 | Session store + resume; durable Time Travel; Flight Recorder export. | Resume preserves assignment and evidence; export is verifiable. |
| 12 | Streaming/cancel; AGENTS.md as project rules. | Turn can be stopped safely without losing receipt integrity. |
| 13 | Live benchmark with two consecutive passes. | Cost/success results recorded honestly. |
| 14 | PyPI publish or keep checkout-only deliberately. | README matches reality. |

---

## 6. Do not do these yet

- Do not start OS/container isolation before the P0 code fixes. The chairman’s
  reason: isolation over a wrong policy inherits the read gap and the substring
  shell gate.
- Do not add another lexical deny for `;`, `&&`, `|`, `>` as the main shell
  fix. It is the same control class that already fails.
- Do not call the audit “tamper-evident” because it has a local hash chain.
  The company is not the hashing party.
- Do not weaken tests to make a demo pass. Add adversarial tests instead.
- Do not commit or push unless the repo owner explicitly asks in that session.

---

## 7. Hard rules inherited from this repo

- `.env` is off-limits. Never read, print, cat, grep, export, log, or commit it.
- Use the project venv: `.venv/bin/python`.
- Never weaken a test to make a boundary pass.
- Never use `git add -A`; never force-push or retag without explicit owner
  instruction.
- Offline/mock runs must be labelled. Never present them as live.
- Free models are default. Paid models only via `--allow-paid` or
  `AGENT_ALLOW_PAID=1`.
- If a command is unverified, write `unverified`, not a confident sentence.

---

## 8. Commands

```bash
# fast full suite
.venv/bin/python -m pytest -q

# offline gate; adds static, boundary, demos, mock model
./demo/check_all.sh

# boundary-only checks
.venv/bin/python demo/check_boundary.py
.venv/bin/python demo/showcase.py

# local agent with the to-do policy
.venv/bin/python agent.py \
  --company-id todoinc \
  --policy policies/todoinc-todo.toml \
  --task "build a todo app with add() and complete()"

# demo TUI (offline until quota allows live)
./demo/live_show.sh
```

`--live` needs the owner’s approval, a valid network/key state, and two
consecutive passes before any live claim changes.

---

## 9. Design questions the next owner should answer

1. Who is the boundary against?
   - remote model only, or also the local employee/operator?
2. Is the product story a governed local agent or a trusted-proxy companion?
3. Container-first or native sandbox? Where does egress policy live?
4. What is the smallest credible claim for an alpha demo?
   - “policy fence with honest limits” is the defensible one today.
5. Does the plan contract need real cryptographic signing, or is the UI
   approval enough for the demo?
6. What should the user see when the shell needs approval?
7. What evidence must reach the company rather than the endpoint?

---

## 10. First three days for the incoming maintainer

### Day 1

- Run the commands in §8.
- Read the council verification.
- `demo/attack_boundary.py` already exists; run it and publish any new literal
  failures in `docs/RELEASE-STATUS.md`.
- Do not remove known failure rows to make the report look cleaner.

### Day 2

- ~~Implement P0 #2 and #3.~~ P0 #2 is complete:
  `test_boundary_walkers.py` passes.
- Next: implement P0 #3 only (shell product scope / capability reduction), with
  composition tests that include a legitimate hit. Do not replace it with a
  fragile lexical denylist.
- Rerun full suite, offline gate, and `demo/attack_boundary.py`; the shell GAP
  rows should become PASS, not disappear from the report.

### Day 3

- Implement P0 #4 and #5.
- Decide and document the managed-policy trust story (#6).
- Stop before P1 unless the owner asks.

---

## 11. Git handoff note

The current branch is `feature/liquid-glass-tui`. This file is intended to be
committed with the council artifacts, the boundary status update, and the other
currently uncommitted project work. Push only when the owner has explicitly
requested it. Do not rewrite history or force-push.

## 12. Finalization state

Verified local state at finalization:

- Full suite: **381 passed**
- Offline gate: **13 passed · 0 failed · 1 skipped**
- `demo/attack_boundary.py`: **6 PASS · 4 GAP · 2 NOTE**, exit `3`
- Boundary probes: `check_boundary` 17/17, `showcase` 18/18
- No live run claimed

Known-unfinished security work that must **not** be marked complete from this
file alone:

- Shell product-scope and capability reduction
- No-policy fail-closed behavior
- Company-held audit anchor
- Managed-policy signature/pinned manifest
- OS sandbox and egress control

The branch is ready for handoff, but not ready for public security guarantees.

Because `opencode.json` denies `git push`, the owner must run:

```bash
git push -u github-https feature/liquid-glass-tui
```

After push, the incoming maintainer should start with `OPENCODE-AGENT-BRIEF.md`.
