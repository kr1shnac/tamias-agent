# OPENCODE-AGENT-BRIEF.md — complete project status

Date: **2026-11-06**
Branch: **`feature/liquid-glass-tui`**
Version: **`0.1.0a7`**
Repo: `/home/krish/Desktop/tamias-agent`

This is the complete short-form project brief for an OpenCode agent. It includes
what is done, what is verified, what is broken or missing, what is planned, what
is pending, how to run the project, and what the next task is.

For a prompt, use exactly this:

```text
Read OPENCODE-AGENT-BRIEF.md first. Follow only its "Next task" section. Do not
start OS sandbox, MCP, packaging, publish, or long-term product work. Preserve
offline evidence for every claim. Do not claim a company boundary guarantee.
```

---

## 1. One-line status

The demo/agent slice is built and offline-verified; the boundary is a real
policy fence for canonical inputs, but it is **not** an unbypassable company
guarantee yet.

## 2. Complete current verdict

- Full offline suite: **381 passed**
- Offline gate: **13 passed · 0 failed · 1 skipped**
- Boundary probes: **17/17** and **18/18**
- Mock model: correct ask-gating and refusals
- Adversarial harness: **6 PASS · 4 GAP · 2 NOTE**, exit code `3`
- Live model path: **not re-verified after latest prompt/boundary changes**
- Live claim: **not made**
- PyPI package: **not published**
- OS sandbox: **not built**
- Network egress control: **not built**
- Client-pinned manifest: **not built**

Do not write “unbypassable”, “company guarantee”, “network is controlled”, or
“live verified today” until the P0 work is closed and two live passes succeed.

---

## 3. How to use this repo

Run every command from the repo root.

```bash
cd /home/krish/Desktop/tamias-agent
```

Primary verification commands:

```bash
.venv/bin/python -m pytest -q
./demo/check_all.sh
.venv/bin/python demo/check_boundary.py
.venv/bin/python demo/showcase.py
.venv/bin/python demo/attack_boundary.py
```

Live commands require explicit owner approval and two consecutive passes:

```bash
./demo/check_all.sh --live
./demo/live_show.sh
```

Direct agent run:

```bash
.venv/bin/python agent.py \
  --company-id todoinc \
  --policy policies/todoinc-todo.toml \
  --task "build a todo app with add() and complete()"
```

Demo instructions are in `demo/PRESENT.md`.

---

## 4. Repository map

| Path | Role |
|---|---|
| `agent.py` | Agent core: tool dispatch, scope/policy gate, shell guard, plan/dossier gates, managed mode, audit |
| `checkpoints.py` | Time Travel v1: pre-write snapshots and frozen diffs |
| `bench.py` | Cost-per-success benchmark harness |
| `brief.py` | Offline brief compiler |
| `context_index.py` | Offline symbol/name/content index |
| `model_catalog.py`, `providers.py` | Model roster and provider/rate reporting |
| `policies/` | Company/use-case boundary TOML files |
| `tui/` | Textual TUI: boundary card, modals, receipt, plan, checkpoint, diff, credits |
| `demo/` | Offline demos, boundary probes, mock provider, live gate, present script |
| `tests/`, `test_*.py` | Offline tests and doc/model-catalog integrity tests |
| `docs/` | Release status, routes, pricing, frontend reference, audit evidence, research |
| `.council/` | Five-advisor boundary council and verification |
| `README.md` | User-facing overview and handoff pointers |
| `AGENTS.md` | Repo rules |
| `AGENTIC-PART.md` | Declared single source of truth |
| `HANDOFF-OPENCODE.md` | Long-form maintainer handoff |
| `OPENCODE-AGENT-BRIEF.md` | This file |
| `opencode.json` | OpenCode permission contract |

---

## 5. Completed work

### 5.1 Agent core and boundary engine

- Tool dispatch through a per-action policy gate.
- Directory tool path fences:
  - `list_directory`
  - `search_in_files`
  - `analyze_structure`
  - `investigate_target`
  - `trace_feature` already checked followed files
- Company fence for `company/work/<company_id>/`.
- Product write scope for `company/work/todoinc/apps/todo/**`.
- Read denylist for denied projects and HR.
- Secret/password/key file guard.
- Policy-file protection.
- Shell guard:
  - cwd inside company work area
  - token scan for `~`, `..`, and absolute escapes
  - allowed/denied shell command families
  - timeout
  - environment scrubbing
- Ask-gated writes:
  - `write_file`
  - `edit_file`
  - `create_directory`
- Headless ask fails closed.
- Domain gate before model spend.
- Plan contract:
  - signed plan required before writes
  - writes outside declared file list are refused
- Dossier gate:
  - first mutating call needs investigation evidence
- Managed mode:
  - requires gateway token
  - refuses direct provider URL
  - fetches policy from gateway
- Audit rows for gate decisions.

### 5.2 Completed boundary hardening on 2026-11-06

- Added `read_path_refusal()` in `agent.py`.
- Applied it to every path returned by directory walkers:
  - `list_directory`
  - `search_in_files`
  - `analyze_structure`
  - `investigate_target`
- Added `test_boundary_walkers.py`:
  - 7 composition tests
  - denied nested paths skipped
  - legitimate in-product paths still visible
- Added `demo/attack_boundary.py`:
  - offline report-only composition probes
  - no shell execution
  - publishes known failures instead of hiding them
- Changed `demo/check_all.sh` to run the full offline suite.

### 5.3 TUI and frontend

- Boundary card and boundary modal.
- Receipt card and copy/export behavior.
- Decision cards.
- Plan contract modal and plan status line.
- Investigation dossier gate.
- Checkpoint preview/restore.
- Frozen diff review with `V` and `/diff`.
- Model picker and credits dashboard.
- Task board and assignment display.

### 5.4 Documentation and evidence

- `docs/RELEASE-STATUS.md`
- `docs/FRONTEND_REFERENCE.md`
- `docs/audit/claims.md`
- `docs/audit/2026-11-06-boundary-hardening.md`
- `.council/runs/20261031-0912-boundary/` council artifacts
- `demo/PRESENT.md` runbook
- `HANDOFF-OPENCODE.md`
- `OPENCODE-AGENT-BRIEF.md`

---

## 6. Verified test breakdown

Verified on 2026-11-06.

| Suite | Count | Status |
|---|---:|---|
| `test_agent.py` | 246 | passed |
| `test_tui_features.py` | 50 | passed |
| `test_premium_features.py` | 40 | passed |
| `test_boundary_walkers.py` | 7 | passed |
| `tests/` docs + catalog | 34 | passed |
| Workspace demo tests | 4 | passed |
| **Full suite** | **381** | **passed** |

Offline gate details:

| Check | Result |
|---|---|
| Dependencies import | pass |
| TUI modules import | pass |
| Static tool registry / prompt budget | pass |
| Full offline pytest suite | pass |
| `check_boundary` | pass |
| `showcase` boundary table | pass |
| `todo_show` scope gate | pass |
| `show` full act | pass |
| REA lifecycle | pass |
| Final behavioral showcase | pass |
| Mock out-of-scope write | pass |
| Mock in-scope write | pass |
| Live rehearsal | skipped |

---

## 7. Architecture and trust model

The current design treats:

- Remote model: **untrusted**
  - every tool call goes through the local gate before execution
- Local Python process: **enforcement point and trusted**
- Local user/operator: **trusted today**
  - can edit `agent.py`, policy, or environment
- Gateway: **trusted in managed mode**
  - the agent currently does not verify the manifest signature
- OS/kernel: **not a containment layer yet**
  - no OS sandbox or network egress control exists

Dispatch order for a tool call:

1. Plan gate
2. Dossier gate
3. Policy gate: allow/deny, read-only, shell families, path globs
4. Ask gate: fail closed with no handler
5. Checkpoint capture
6. Execute tool

Important consequence: the local process is defending against a bad model, not
against a determined local operator. Saying “people cannot bypass” is only true
if the boundary is enforced below the process, which is not built yet.

---

## 8. Boundary contract currently implemented

Policy file: `policies/todoinc-todo.toml`

### Active product

- Company: `todoinc`
- Company work area: `company/work/todoinc/`
- Product root: `company/work/todoinc/apps/todo`
- Write scope: `company/work/todoinc/apps/todo/**`

### Topic/use-case gate

Allowed examples:

- `build a todo app with add() and complete()`
- `sort tasks by due date`
- `refactor the task list`

Refused examples:

- `build a chatbot`
- `crypto`
- `trading bot`
- `clone linkedin`
- `weather`
- `hi`

The domain gate is lexical. It is a scope guard for spend and UX, not a security
boundary.

### Path denial

Denied or protected:

- `company/work/todoinc/hr/`
- `company/work/todoinc/apps/chatbot/`
- `**/*.pem`
- `.env`
- policy file
- repository root as a project path
- paths outside the company work area

### Tools

Write tools:

- `write_file`
- `edit_file`
- `create_directory`

Ask-gated in policy:

- `write_file`
- `edit_file`
- `create_directory`

Read tools:

- `read_file`
- `search_in_files`
- `list_directory`
- `investigate_target`
- `trace_feature`
- `analyze_structure`
- `build_similar`

### Shell policy

Current allowed families:

- `python3 -m pytest`
- `git status`
- `git diff`
- `git log`

Current denied families:

- `rm `
- `mv `
- `curl `
- `wget `
- `git push`
- `chmod `
- `cat `
- `ssh `

This is a substring gate and is **not sufficient**.

### Boundary query set the team focused on

1. In-scope todo/task work must run.
2. Off-topic/personal requests must be refused before model spend.
3. Out-of-product paths must be denied.
4. In-product writes must be allowed but ask-gated.
5. Headless in-product writes must fail closed.
6. Invalid company IDs must be refused.
7. `.env`, keys, and policy files must be protected.
8. Shell path escapes must be refused.
9. Plan/dossier gates must gate mutations.
10. Managed mode must refuse direct provider URLs.
11. Audit must record gate decisions.
12. `.` must not silently bypass the product fence.

---

## 9. Known issues

| ID | Severity | Issue | Evidence/Status | Required fix |
|---|---|---|---|---|
| BND-02 | Critical | Shell `shell=True` with substring allowlist | `demo/attack_boundary.py` GAP: composite shell gate | Product-root shell enforcement, capability reduction, or ask-gate |
| BND-03 | High | Cross-project shell path passes gate | `demo/attack_boundary.py` GAP: cross-project shell path | Shell command paths must be bound to product root |
| BND-04 | High | No active policy can leave gate off | `policy_check` returns `None`; `demo/attack_boundary.py` GAP | Fail closed or emit undeniable fence-off audit |
| BND-05 | High | Audit is local and not company-held | Audit rows lack resolved path, cwd, policy hash; disappear with no policy | Always-on anchored audit or gateway sink |
| BND-06 | High | Managed policy trust is asserted, not verified | `fetch_policy` parses gateway JSON; no agent-side signature | Client-pinned signed manifest or explicit gateway trust statement |
| BND-07 | Medium | Domain gate is lexical and can under-block/over-block | `domain_check` self-describes as “scope guard, not security boundary” | Add proportionality probes and separate scope from security |
| BND-08 | Medium | Plan contract is local approval, not cryptographic signing | `contract_line = "signed by user"` | Stop calling it signed without key material, or add signing |
| BND-09 | Medium | `fetch_url` probe proves unknown tools rejected, not egress control | `demo/showcase.py` probe | Fix demo wording and separate unknown tools from egress |
| BND-01 | High | OS sandbox and egress not built | `docs/RELEASE-STATUS.md` blocked row | Container/egress control generated from policy |
| OPS-01 | Medium | Free-tier live quota can 429 | Latest live retry 0/2 rate-limited | Only claim live after two consecutive passes |
| OPS-02 | Medium | PyPI package not published | `pip install tamias` 404s | Keep checkout install or publish deliberately |

### Attack harness current rows

| Row | Status |
|---|---|
| Search from company root | PASS |
| Analyze from company root | PASS |
| Investigate from company root | PASS |
| List apps tree | PASS |
| Direct read of denied app | PASS |
| Direct search of denied app | PASS |
| Composite shell gate | GAP |
| Cross-project shell path | GAP |
| No-policy run gate | GAP |
| No-policy audit row | GAP |
| Managed policy signature | NOTE |
| OS sandbox and egress | NOTE |

`demo/attack_boundary.py` correctly exits `3` while gaps remain.

---

## 10. Missing / not built

- OS/container sandbox
- Network egress allowlist
- MCP boundary server
- Client-pinned manifest verification
- Admin-owned policy file outside repo
- Company-held audit anchor
- Session store + resume
- Durable Time Travel
- Flight Recorder / audit export
- Streaming/cancel
- Live benchmark
- PyPI publication
- Multi-agent concurrency story
- Offline time-machine session resume

---

## 11. Plan

### Phase 1 — finish P0 boundary hardening

1. Shell capability reduction
2. Policy omission fail-closed / fence-off audit
3. Company-held audit
4. Managed policy verification

### Phase 2 — production hardening

5. OS/container sandbox and egress allowlist
6. MCP boundary server
7. Admin-owned, shell-protected policy/audit paths
8. Proportionality/false-positive probes

### Phase 3 — product depth

9. Session store + resume
10. Durable Time Travel
11. Flight Recorder export
12. Streaming/cancel
13. Live benchmark with two passes

### Phase 4 — release

14. Decide PyPI publish vs checkout-only
15. Reconcile README/packaging claims

---

## 12. Pending task list

### Done on 2026-11-06

- `deny_read` on returned walker paths
- `test_boundary_walkers.py`
- `demo/attack_boundary.py`
- Full offline suite in `demo/check_all.sh`
- Council verification follow-up
- Documentation/status update

### Open P0

| Task | Done when |
|---|---|
| Shell product scope and capability reduction | Composite and cross-project shell GAP rows become PASS; legitimate product pytest still works |
| Policy omission fail-closed or audited | No run can silently lose the gate |
| Company-held audit | Rows contain resolved path, cwd, policy hash, and are received off-device |
| Managed policy verification | Downgraded/BYO gateway policy cannot start a bounded run |

### Open P1

| Task | Done when |
|---|---|
| OS/container sandbox | In-container attack harness cannot escape policy |
| Egress allowlist | Allowed commands cannot make arbitrary network calls |
| MCP boundary server | Remote MCP client cannot exceed local boundary |
| Admin-owned policy/audit outside agent reach | Agent cannot rewrite its own boundary/trail |
| False-positive probes | `pytest -k "confirm parser"` is not refused because it contains `rm ` |

### Open P2

| Task | Done when |
|---|---|
| Session store + resume | Assignment and evidence survive restart |
| Durable Time Travel | Checkpoints persist across sessions |
| Flight Recorder export | Company receives verifiable evidence |
| Streaming/cancel | Turn can stop safely without losing evidence |
| Live benchmark | Two consecutive live passes recorded |
| PyPI decision | README matches reality |

---

## 13. Next task

**Task: implement P0 shell product scope and capability reduction.**

Requirements:

1. Keep legitimate in-product commands working.
2. Prevent any shell command from reading or mutating outside
   `company/work/todoinc/apps/todo` unless the policy explicitly allows it.
3. Do not rely only on rejecting `;`, `&&`, `|`, backticks, or `>`; those are
   lexical guards and already demonstrably insufficient.
4. Prefer:
   - narrower shell command prefixes,
   - ask-gating `run_shell` when it can mutate,
   - executing only inside the product cwd,
   - resolving shell paths against the product root,
   - blocking interpreter families that can execute arbitrary code.
5. Add tests for both hostile and legitimate command forms.
6. Rerun:
   ```bash
   .venv/bin/python -m pytest -q
   ./demo/check_all.sh
   .venv/bin/python demo/attack_boundary.py
   ```
7. Update:
   - `HANDOFF-OPENCODE.md`
   - `OPENCODE-AGENT-BRIEF.md`
   - `docs/RELEASE-STATUS.md`
   - add `docs/audit/2026-MM-DD-shell-boundary.md`

Acceptance:

- Full suite remains at or above 381 passes.
- No tests are weakened.
- `demo/attack_boundary.py` shell GAP rows become PASS.
- Legitimate `pytest` commands still work or produce an explicit ask flow.
- No boundary guarantee wording is added.

---

## 14. OpenCode-specific rules

The repo has `opencode.json`. Do not try to bypass it.

Important permission rules:

- Deny read/edit:
  - `.env`
  - `.env.*`
  - `.pypirc`
  - `.ssh/**`
- Deny bash:
  - `sudo *`
  - `rm -rf *`
  - `rm -fr *`
  - `git push*`
  - `git remote*`
  - `git reset*`
  - `git clean*`
  - `git tag*`
  - `git switch*`
  - `git checkout*`
  - `git merge*`
  - `git rebase*`
  - `git stash*`
  - `git branch*`
  - `git worktree*`
  - `git add -A*`
  - `git add --all*`
  - `git add .`
  - `*pip install*`
  - `*pip3 install*`
  - `npm *`
  - `twine *`
  - `curl *`
  - `wget *`
  - `env`
  - `printenv*`

Therefore the agent must:

- Stage files explicitly:
  ```bash
  git add path/to/file
  ```
- Stop and report if a command is denied.
- Let the user run push commands.
- Not ask permission questions; write the proposed command in the final report.
- Not assume old skill IDs remain available.

---

## 15. Hard repo rules

- Use `.venv/bin/python`.
- Never read, print, commit, or log `.env`.
- Never weaken tests to make a demo pass.
- Never use `git add -A`.
- Never force-push, retag, reset, or clean without explicit owner instruction.
- Never present offline/mock runs as live.
- Live runs need owner approval and two consecutive passes.
- Free models are default. Paid models require `--allow-paid` or
  `AGENT_ALLOW_PAID=1`.
- Every material claim needs a command and saved evidence file.
- Keep the boundary honest: label limits instead of hiding them.

---

## 16. Allowed claims

Current truthful claims:

- “Offline policy fence with per-action gate.”
- “Canonical boundary probes refuse denied paths.”
- “Directory walkers now enforce deny_read on returned paths.”
- “Headless writes are fail-closed.”
- “Full offline suite passes: 381.”
- “Adversarial harness names remaining failures.”

Current forbidden claims:

- “Unbypassable.”
- “Company guarantee.”
- “Network is controlled.”
- “OS sandboxed.”
- “Plan contract is cryptographically signed.”
- “Live path verified today.”
- “Measured cost savings.”

---

## 17. Evidence files

Read these before changing boundary code:

1. `HANDOFF-OPENCODE.md`
2. `docs/RELEASE-STATUS.md`
3. `docs/audit/2026-11-06-boundary-hardening.md`
4. `.council/runs/20261031-0912-boundary/verification.md`
5. `.council/runs/20261031-0912-boundary/transcript.md`
6. `.council/runs/20261031-0912-boundary/report.html`
7. `test_boundary_walkers.py`
8. `demo/attack_boundary.py`
9. `docs/BOUNDED-AGENT.md`
10. `docs/FRONTEND_REFERENCE.md`
11. `demo/PRESENT.md`

---

## 18. Demo instructions

Offline full verification:

```bash
./demo/check_all.sh
```

Boundary-only:

```bash
.venv/bin/python demo/check_boundary.py
.venv/bin/python demo/showcase.py
```

Boundary attack report:

```bash
.venv/bin/python demo/attack_boundary.py
```

Live TUI only with approval:

```bash
./demo/live_show.sh
```

TUI keys:

- `Y` approves an ask-gated write
- `N` refuses an ask-gated write
- `Esc` leaves nav mode before action keys
- `V` opens the frozen diff
- `Z` previews a checkpoint
- `R` opens the receipt

Demo negative probe:

```text
create todo in desktop
```

That must be blocked as an out-of-project path, not quietly rewritten into the
product root.

---

## 19. Product design questions still open

1. Is the boundary against the remote model only, or also against the local
   operator?
2. Is the product a governed local agent or a trusted-proxy companion?
3. Container-first or native sandbox?
4. What is the smallest credible alpha claim?
5. Does the plan contract need real cryptographic signing?
6. What evidence must reach the company rather than the endpoint?
7. Should model spend show hypothetical, provider-billed, and measured costs as
   separate labels?
8. Is MCP boundary depth required for the first release or a later phase?

---

## 20. Future plans: lag, performance, and pending sequence

This section is the roadmap the next maintainer should follow. Security P0 work
comes before performance work because a fast bypass is still a bypass. Do not
micro-optimize before measuring.

### 20.1 Current measured performance baseline

Measured on 2026-11-06 on this machine:

| Operation | Measured time | Status |
|---|---:|---|
| Full pytest suite | about `15.85s` | pass |
| Offline gate `check_all.sh` | about `31s` | pass |
| `demo/attack_boundary.py` | `522ms`, exit `3` | report-only, gaps remain |
| `demo/check_boundary.py` | `771ms` | pass |

Not measured yet:

- TUI startup and first render
- TUI turn latency while modal is open
- Policy gate cost on a large tree
- Live model latency and free-tier 429 frequency
- Shell timeout frequency
- Multi-file search/investigate cost on 10k+ files

Do not quote a performance improvement until a before/after file exists in
`docs/audit/`.

### 20.2 Lag risk areas

These are suspects, not confirmed bottlenecks:

1. **Policy checks on every returned path**
   - After the 2026-11-06 hardening, `read_path_refusal()` calls
     `policy_check()` for each path returned by directory walkers.
   - `_glob_any()` currently computes `realpath` and runs `fnmatch` repeatedly.
   - On a large tree this can become the dominant tool-dispatch cost.
2. **Repeated directory walks**
   - `search_in_files`, `analyze_structure`, and `investigate_target` walk the
     same tree again on each call.
3. **TUI refresh frequency**
   - The app has a spinner interval, credit refresh, task-board refresh, and
     transcript updates. Large tool output can make redraws expensive.
4. **Large evidence rendering**
   - The frozen diff, checkpoint, and receipt cards need explicit size caps and
     truncation-level warnings.
5. **Blocking shell execution**
   - `run_shell` can block up to 60 seconds. The TUI should make that visible.
6. **Model provider latency and quota**
   - Free tier can return HTTP 429. This is external latency, not local lag.
7. **Verification time**
   - The suite is currently acceptable, but new tests should not let it grow
     past a stated budget without a reason.

### 20.3 Performance work plan

#### Perf-1: Build a performance baseline harness

Task:

- Add `demo/perf_boundary.py`.
- Keep it offline and deterministic.
- Create synthetic trees only under `/tmp` using `tempfile`; never mutate the
  demo company fixture.
- Measure at least:
  - policy gate for allowed and denied paths
  - `search_in_files` on in-scope and denied subtrees
  - `analyze_structure` on in-scope and denied subtrees
  - checkpoint capture
  - diff generation
  - full offline pytest time
- Support a check mode:
  ```bash
  .venv/bin/python demo/perf_boundary.py --check
  ```
- Save output as JSON under `demo/runs/` or a documented evidence path.

Initial budget placeholders to confirm, not final truth:

| Metric | Initial budget target |
|---|---:|
| `policy_check(allowed path)` | under `1ms` median after warmup |
| Parent-directory search on 1k files | under `500ms` |
| Parent-directory analyze on 1k files | under `500ms` |
| Checkpoint + diff for small file | under `250ms` |
| Full pytest suite | under `25s` |

#### Perf-2: Instrument before optimizing

Task:

- Reuse the existing `time.perf_counter()` timing already present in agent turns.
- Add optional per-tool timing events where missing.
- Record policy gate time separately from tool execution time.
- Include a “policy gate ms” field in receipts or audit events.

Done when:

- A single controlled run can show where time went:
  model wait, policy gate, tool execution, TUI queue.

#### Perf-3: Optimize policy-path checks

Priority: high, because 2026-11-06 added per-path checks.

Task:

- Precompile policy globs when the policy is loaded.
- Avoid repeated `realpath` calls for unchanged paths where safe.
- Cache decisions by process, real path, and policy identity.
- Invalidate cache when `set_active_policy()` runs.
- Add tests proving denial does not become stale after:
  - policy replacement
  - symlink change
  - workspace change
- Do not cache across processes without a documented cache key and policy hash.

Done when:

- `demo/perf_boundary.py` shows a measured improvement or proves no change is
  needed.
- `test_boundary_walkers.py` and all 381 tests still pass.

#### Perf-4: Reduce output redraw cost

Task:

- Cap search/analyze/investigate output more aggressively for parent
  directories.
- Prefer a summary plus explicit drill-down over dumping every nested file.
- Add a `truncated` marker and a count of omitted denied/allowed entries.
- Ensure TUI never renders an uncapped giant document.

Done when:

- A large directory result returns in bounded time and bounded memory.

#### Perf-5: TUI responsiveness

Task:

- Measure TUI mount and first prompt render.
- Debounce or batch:
  - credits refresh
  - task-board refresh
  - status line updates
- Avoid full transcript rebuild for each chunk.
- Move shell execution feedback into a visibly throttled status event.

Done when:

- No visible stall over `250ms` during typing, scrolling, or receipt open in
  the recorded manual test.

#### Perf-6: Provider and quota resilience

Task:

- Continue using free models by default.
- Handle HTTP 429 as a distinct, honest state.
- Do not silently rotate into paid models.
- Add a retry/backoff ceiling and report it clearly.
- Never hide a 429 as a model answer.

Done when:

- A mock 429 test proves the user sees “rate-limited; no run claimed” instead of
  a false success.

### 20.4 Full future pending sequence

Follow this order.

#### Now: P0 security completion

1. Shell product-scope and capability reduction.
2. No-policy run must fail closed or emit an undeniable fence-off audit row.
3. Audit must include:
   - resolved path
   - cwd
   - policy hash
   - plan/session binding
   - always-on mode
4. Managed policy must be verified with a pinned manifest, or docs must state
   the gateway is the trust root.

#### Next: performance and lag remediation

5. `demo/perf_boundary.py` baseline.
6. Policy-path optimization after profiling.
7. Output size limits and truncation markers.
8. TUI batching/debounce.
9. Provider 429 resilience and honest quota handling.

#### Then: production hardening

10. OS/container sandbox.
11. Network egress allowlist.
12. MCP boundary server.
13. Admin-owned, shell-protected policy/audit files.
14. False-positive/proportionality probes.

#### Then: product depth

15. Session store + resume.
16. Durable Time Travel.
17. Flight Recorder export.
18. Streaming/cancel.
19. Live benchmark with two consecutive passes.

#### Finally: release

20. Decide and document PyPI publish vs checkout-only.
21. Reconcile README/packaging claims with actual install behavior.
22. Add public performance/security status that is generated from evidence.

### 20.5 What to do next from Monday

Day 1:

- Read this file and `HANDOFF-OPENCODE.md`.
- Run:
  ```bash
  .venv/bin/python -m pytest -q
  ./demo/check_all.sh
  .venv/bin/python demo/attack_boundary.py
  ```
- Build `demo/perf_boundary.py` if shell work is already complete.

Day 2:

- Implement shell product-scope/capability reduction.
- Add hostile and legitimate tests.

Day 3:

- Rerun all offline evidence.
- Update `docs/RELEASE-STATUS.md` with before/after times.
- If shell is complete, start no-policy fail-closed.

Day 4:

- Audit rows and managed-policy trust decision.
- No “company guarantee” wording.

Day 5:

- Performance baseline and one measured optimization.
- Write evidence in `docs/audit/YYYY-MM-DD-performance.md`.

### 20.6 Performance change rules

- No optimization without a measured before/after.
- Never optimize by deleting a boundary check.
- Never cache a deny decision across a policy change without invalidation.
- Never make denial stale to make performance look better.
- Keep every budget number labeled as measured or placeholder.
- If a budget cannot be measured yet, write `unverified`.

---

## 21. Git state

Branch: `feature/liquid-glass-tui`

Use commands, not assumptions:

```bash
git status -sb
git log -6 --oneline
git diff --check
```

The OpenCode config denies `git push`, so if a push is required, report:

```bash
git push -u github-https feature/liquid-glass-tui
```

and let the user execute it.

Before commit:

```bash
.venv/bin/python -m pytest -q
./demo/check_all.sh
git diff --check
```

Stage explicit paths only. Commit message must include the verification result.
