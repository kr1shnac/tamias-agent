# Evidence log — Plan Contract, file drift and the dossier gate

**Date:** 2026-10-28
**Branch:** `feature/liquid-glass-tui`
**Scope:** the enforcement half of the second premium slice — a human-signed
Plan Contract, file-drift refusal, and a pre-write dossier gate. This log
records what was run; it does not claim editable plan steps, checkpoints or
durable receipts.

---

## 1. Full test suite

```bash
.venv/bin/python -m pytest -q
```

Result:

```
352 passed in 11.10s
```

Breakdown:

| Suite | Tests |
|---|---:|
| `test_agent.py` | 232 |
| `test_tui_features.py` | 50 |
| `test_premium_features.py` | 33 |
| `tests/` (docs integrity + model catalog) | 33 |
| Workspace demo tests | 4 |
| **Total** | **352** |

The gate's pytest check (the four files used by `demo/check_all.sh`) is:

```
329 passed in 10.87s
```

## 2. Contract behavior — core evidence

The new core tests in `test_agent.py`:

- `test_a_signed_plan_allows_the_next_write` — a signed plan lets the following
  `write_file` run and the tool result contains `contract: signed by user`.
- `test_a_denied_plan_stops_the_turn_before_the_write` — the model's next call
  is never requested; no file exists; the receipt state is a denial.
- `test_status_only_plan_updates_do_not_ask_again_but_content_does` — moving
  `[~]` to `[x]` reuses the signature; changing a step's text asks again.
- `test_an_active_plan_gate_with_no_approver_fails_closed` — an active gate with
  no human handler refuses; it never becomes an implicit yes.
- `test_a_crashing_plan_approver_fails_closed` — an exception in the approval
  path is a closed gate.
- `test_a_write_outside_the_signed_plan_stops_the_turn` — a plan declaring
  `allowed.txt` refuses a write to `other.txt`, leaves no file, and ends with a
  plan-contract message, not a boundary violation.
- `test_a_signed_plan_declares_files_risks_and_verification` — the deterministic
  result carries `files:`, `verification:`, `risk:` and the hypothetical
  `cost range:` line; `plan_write_block` enforces the file list.
- `test_the_dossier_gate_holds_the_first_write_until_evidence` — a write and a
  shell call are held before evidence; `analyze_structure` supplies evidence;
  the retried write succeeds.
- `test_finish_investigation_alone_does_not_unlock_a_write` — a summary is not
  evidence; the gate stays closed.
- `test_an_unsigned_plan_only_claims_writes_are_held_with_a_gate` — the card
  says "working plan" without a gate and "writes are held" only when the gate is
  active.

## 3. Contract behavior — TUI evidence

The new TUI tests:

- `test_plan_gate_blocks_the_worker_until_the_plan_is_signed` — the worker thread
  blocks in `PlanGate.ask`; `resolve(True)` releases it.
- `test_plan_gate_fails_closed_when_nobody_answers` — a short timeout returns
  `False`.
- `test_the_app_signs_a_plan_contract_through_a_modal` — `PlanContractModal`
  shows the steps, files, verification, risks and `$0.0000` cost range; `Y`
  resolves the gate with `True`.
- `test_the_app_denies_a_plan_contract_and_records_it` — `N` resolves `False`;
  the receipt says `plan denied`, includes `denied by user`, and says no writes
  ran.
- `test_receipt_marks_a_plan_drift_as_a_contract_block` — drift is `PLAN
  BLOCKED`, not a policy boundary.
- `test_receipt_does_not_count_a_plan_held_shell_as_a_failed_check` — a shell
  call held before signature is a plan block, not a failed verification.
- `test_receipt_records_a_dossier_hold_without_calling_it_a_failure` — a dossier
  hold is counted under `dossier holds`, not `failures`.

## 4. Offline gate

```bash
./demo/check_all.sh
```

Result:

```
13 passed   0 failed   1 skipped   23s
READY (offline) - run with --live to rehearse the real model.
```

The skip is the live rehearsal (not requested).

## 5. Live gate

```bash
./demo/check_all.sh --live
```

Run once after the contract code:

```
14 passed   0 failed   0 skipped   29s
READY (offline + live) - live model, tool call and visible switch all passed.
```

Run again immediately:

```
14 passed   0 failed   0 skipped   30s
READY (offline + live) - live model, tool call and visible switch all passed.
```

Both runs show the real free model calling a tool and the visible
`nvidia/nemotron-3.5-lightning:free → nvidia/nemotron-3-ultra-550b-a55b:free`
switch. The live gate is headless: it does not drive the Plan Contract modal or
the dossier gate. Those are proven by the core and TUI tests above.

## 6. What this proves

- A published plan is not executable until a human signs it in the TUI.
- Denial stops the turn; no write and no shell call runs.
- Status-only progress does not re-ask; contract changes do.
- An absent or crashing approver fails closed.
- A signed plan that names files refuses a write outside that list.
- The receipt distinguishes `PLAN DENIED`, `PLAN BLOCKED` and `dossier holds`
  from a policy boundary and from tool failures.
- The dossier gate holds mutating calls until evidence exists, and the model can
  recover in the same turn by investigating.

## 7. What this does not prove

- **No editing of plan steps.** The human signs or denies the agent's proposal.
- **No task-level persistence.** A contract belongs to one turn; the next turn
  starts unsigned.
- **No shell path allowlist.** Shell commands are signature-gated and
  dossier-gated, but after signature they are not scoped to the plan's files.
- **No checkpoints / Time Travel.** There is no undo, preview or restore.
- **No durable receipt/dossier storage.** Both are per-process Python objects.
- **Dossier relevance is not checked.** The gate requires some evidence, not
  proof that the evidence covers the exact write; the signed plan is the human
  check.
- **No fresh live TUI run.** The live gate does not drive the TUI; the modal and
  gate paths are tested headlessly with Textual.

## 8. Reproduction

```bash
cd /home/krish/Desktop/tamias-agent
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest test_agent.py -q -k "plan or dossier"
.venv/bin/python -m pytest test_tui_features.py -q -k "plan"
./demo/check_all.sh
./demo/check_all.sh --live   # twice, before a live demo
```

## 9. Files in this slice

| File | Role |
|---|---|
| `agent.py` | plan state, sign/deny gate, contract fields, file drift, dossier gate |
| `tui/bridge.py` | `PlanGate`, `PlanAsk` emission, TUI gate installation |
| `tui/events.py` | `PlanAsk` event |
| `tui/modals.py` | `PlanContractModal` and contract facts |
| `tui/app.py` | modal wiring, approval/denial receipt state, plan risk |
| `tui/plan.py` | signed state, files/verification/risks/cost parsing |
| `tui/receipt.py` | plan denial/block, dossier holds, policy rows |
| `test_agent.py` | core contract, drift and dossier-gate tests |
| `test_tui_features.py` | gate and modal tests |
| `test_premium_features.py` | receipt and parser tests |
| `docs/PREMIUM-AGENT.md` | thesis/status update |
| `docs/FRONTEND_REFERENCE.md` | §10A.4–10A.6 contract |
| `demo/PRESENT.md` | sign/deny/drift/dossier demo moments |
