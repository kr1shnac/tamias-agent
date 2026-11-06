# Evidence log — plan card and investigation dossier

**Date:** 2026-10-28
**Branch:** `feature/liquid-glass-tui`
**Scope:** the first views of the second premium slice — the `P` Plan Card and
the `D` Investigation Dossier — plus the investigation-tool crash that blocked a
real directory dossier.

**Historical note.** This log describes the view-only slice. The enforcement
slice that followed — signed Plan Contract, file drift and the pre-write dossier
gate — is recorded in `docs/audit/2026-10-28-plan-contract.md`. The counts below
are the counts at that earlier point, not the current suite.

This log records what was run. It does not claim approval gating, a pre-write
evidence gate, checkpoints, or a fresh live-model pass.

---

## 1. Full test suite

```bash
.venv/bin/python -m pytest -q
```

Result:

```
333 passed in 9.98s
```

Breakdown:

| Suite | Tests |
|---|---:|
| `test_agent.py` | 223 |
| `test_tui_features.py` | 46 |
| `test_premium_features.py` | 27 |
| `tests/` (docs integrity + model catalog) | 33 |
| Workspace demo tests | 4 |
| **Total** | **333** |

The new `test_premium_features.py` cases cover:

- plan parsing, status marks and the explicit "not signed" contract row;
- malformed / error output never becoming a plan;
- `investigate_target` evidence, limitations and unknowns;
- `trace_feature` `Step N | path:line | text` parsing;
- `analyze_structure` `[FILE]` entries;
- error results being ignored and duplicate evidence being collapsed;
- unresolved questions from `finish_investigation`;
- `P` opening the card, the `.plan-line`, and the receipt `PLAN` section;
- `/dossier` opening the card, the `.dossier-line`, and the receipt
  `INVESTIGATION` section;
- honest "nothing recorded yet" messages when no plan or dossier exists.

## 2. The investigation bug

Before this slice, a directory investigation crashed:

```
Error investigating company/work/todoinc/apps/todo: cannot access local
variable 'feature_terms' where it is not associated with a value
```

`feature_terms` was defined only inside the single-file branch but used by the
directory branch. The fix hoists a filtered `feature_terms` list above the
branch. A regression test now runs a real directory investigation:

```bash
.venv/bin/python -m pytest \
  test_agent.py::test_investigate_target_walks_a_directory_without_crashing -q
```

Result: `1 passed`.

The parser tests use a literal copy of the tool's real output; the regression
test calls the tool itself. The output includes real `file:line` evidence from
`company/work/todoinc/apps/todo`:

```
[evidence] src/todo.py:1  """TODOINC's one product: a to-do list."""
[evidence] src/todo.py:4  def add(items, title):
[evidence] tests/test_todo.py:6  from src.todo import add, complete
```

## 3. Offline gate

```bash
./demo/check_all.sh
```

Result:

```
13 passed   0 failed   1 skipped   22s
READY (offline) - run with --live to rehearse the real model.
```

The skip is the live rehearsal (not requested). The gate's pytest check runs
310 tests: `test_agent.py`, `test_tui_features.py`,
`test_premium_features.py` and `tests/test_docs_integrity.py`.

## 4. What this proves

- The plan card is parsed from the agent's own `update_plan` text; the model
  does not write a second summary.
- The dossier is parsed from the evidence tools' own `file:line` output; tool
  errors add nothing, and duplicate evidence is collapsed.
- Both cards are reachable in nav mode (`P` / `D`) and with `/plan` /
  `/dossier` while typing.
- Both surfaces add measured sections to the receipt.
- The transcript lines are quiet and only appear when the turn produced the
  corresponding surface.
- The cards are explicit about their limits: the plan is not signed; the
  dossier is static evidence, not runtime proof.
- The receipt's RISKS section repeats those limits: unsigned plan, static
  evidence, and the unknown count when the dossier left questions open.

## 5. What this does not prove

- **No approval gate.** The core still lets the model continue after
  `update_plan`; the Plan Card says "not signed".
- **No pre-write evidence gate.** A write does not fail because no dossier
  exists.
- **No checkpoints / Time Travel.** There is no undo, preview or restore.
- **No fresh live-model pass in this slice.** The previous live gate (2026-10-28,
  two consecutive passes, 14/0/0) still describes the model path; this slice
  changed the investigation helper and TUI views, not the provider path. Re-run
  `./demo/check_all.sh --live` before a live demo.
- **No durable receipt/dossier storage.** Both are per-process Python objects.

## 6. Reproduction

```bash
cd /home/krish/Desktop/tamias-agent
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest test_premium_features.py -q
./demo/check_all.sh
```

## 7. Files in this slice

| File | Role |
|---|---|
| `tui/plan.py` | deterministic `update_plan` parser and plan model |
| `tui/dossier.py` | evidence parser, dedupe, dossier model |
| `tui/modals.py` | `PlanCard`, `DossierCard`, help rows |
| `tui/app.py` | P/D bindings, work-surface lifecycle, transcript lines |
| `tui/receipt.py` | optional measured `PLAN` / `INVESTIGATION` sections |
| `tui/slash.py` | `/plan`, `/dossier` commands |
| `agent.py` | directory investigation crash fix |
| `test_premium_features.py` | 27 premium-surface tests |
| `test_agent.py` | directory investigation regression test |
| `docs/PREMIUM-AGENT.md` | thesis/status update |
| `docs/FRONTEND_REFERENCE.md` | §10A.4–10A.6 contract |
| `demo/PRESENT.md` | P/D demo moments and feature matrix |
