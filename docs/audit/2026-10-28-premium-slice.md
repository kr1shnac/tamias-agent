# Evidence log — premium accountability slice

**Date:** 2026-10-28
**Branch:** `feature/liquid-glass-tui`
**HEAD:** `d537a7c` (working tree carries the uncommitted slice)
**Scope:** Boundary Card, per-turn Receipt, structured Decision Card; the
supporting `docs/PREMIUM-AGENT.md` thesis and the demo runbook update.

This log records what was run, not what was intended. The live gate is claimed
only because it passed twice consecutively. It is the historical first-slice
record; the later Plan Card / Dossier slice is in
`docs/audit/2026-10-28-work-surfaces.md` (333 tests, 310 in the gate).

---

## 1. Full test suite

```bash
.venv/bin/python -m pytest -q
```

Result:

```
323 passed in 10.30s
```

Breakdown:

| Suite | Tests |
|---|---:|
| `test_agent.py` | 222 |
| `test_tui_features.py` | 46 |
| `test_premium_features.py` | 18 |
| `tests/` (docs integrity + model catalog) | 33 |
| Workspace demo tests | 4 |
| **Total** | **323** |

`test_premium_features.py` covers the receipt accounting rules, the honest
unknown-cost path, the refusal receipt, verification-command detection,
boundary-card formatting with and without a policy, the `B`/`R` keys, the
`/receipt` command, a plan-level denial with no tool card, an early error, and
the decision card.

## 2. Offline gate

```bash
./demo/check_all.sh
```

Result:

```
13 passed   0 failed   1 skipped   25s
READY (offline) - run with --live to rehearse the real model.
```

The skip is the live rehearsal (not requested). The gate's pytest check runs
300 tests (the 323 above minus the workspace demo tests and the model-catalog
tests not in the gate).

## 3. Live gate — two consecutive passes

```bash
./demo/check_all.sh --live
```

Result:

```
attempt 1 (one model, real tool call): exit 0
       ▶ nvidia/nemotron-3.5-lightning:free
       compactions: 0 · spent: $0.0000
attempt 2 (rotation: two models, switch card): exit 0
       ▶ nvidia/nemotron-3.5-lightning:free
       ◀ nvidia/nemotron-3.5-lightning:free
       ▶ nvidia/nemotron-3-ultra-550b-a55b:free
PASS  live: two consecutive passes, including a visible model switch

14 passed   0 failed   0 skipped   52s
READY (offline + live) - live model, tool call and visible switch all passed.
```

Why this is claimed:

- two consecutive attempts exited 0;
- a real free model called a tool;
- rotation moved the turn onto a second model and the switch card was visible;
- the run reported `$0.0000`, which is accurate for the free tier.

What this does **not** prove:

- the live gate does not drive the TUI, so the Boundary Card and Receipt were
  verified by the TUI tests, not by the live run;
- the receipt is per-process, not durable;
- there is no diff capture, checkpoint, undo or tamper-evident audit yet;
- the free tier can still 429 on stage; the offline fallback remains mandatory.

## 4. Reproduction

```bash
cd /home/krish/Desktop/tamias-agent
.venv/bin/python -m pytest -q
./demo/check_all.sh
./demo/check_all.sh --live        # when the free tier is available
```

The live gate requires a resolvable API key and network access. It never prints
the key. The `.env` file is not read or rendered by the premium surfaces.

## 5. Files in this slice

| File | Role |
|---|---|
| `tui/receipt.py` | deterministic per-turn receipt model |
| `tui/policy_view.py` | policy-to-human boundary sections |
| `tui/modals.py` | `BoundaryCard`, `ReceiptModal`, structured `ConfirmModal` |
| `tui/app.py` | B/R bindings, receipt lifecycle, decision details |
| `tui/slash.py` | `/boundary`, `/receipt` |
| `test_premium_features.py` | 18 focused tests |
| `docs/PREMIUM-AGENT.md` | product thesis and experience architecture |
| `docs/FRONTEND_REFERENCE.md` | UI contract for the new surfaces |
| `demo/PRESENT.md` | faculty runbook with the premium moments |
| `demo/check_all.sh` | gate includes the premium tests |
