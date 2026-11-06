# Evidence log — frozen diff review (Diff v1)

**Date:** 2026-10-29
**Branch:** `feature/liquid-glass-tui`
**Scope:** the review half of Time Travel — a bounded, read-only unified diff
frozen at turn end, linked from the checkpoint receipt. This log records what
was run. It does not claim editable patches, per-file selection or a durable
diff store.

---

## 1. Full test suite

```bash
.venv/bin/python -m pytest -q
```

Result:

```
374 passed in 13.63s
```

Breakdown:

| Suite | Tests |
|---|---:|
| `test_agent.py` | 246 |
| `test_tui_features.py` | 50 |
| `test_premium_features.py` | 40 |
| `tests/` (docs integrity + model catalog) | 34 |
| Workspace demo tests | 4 |
| **Total** | **374** |

The gate's pytest check (the four files used by `demo/check_all.sh`) is:

```
351 passed in 13.59s
```

## 2. Core evidence

New tests in `test_agent.py`:

- `test_turn_end_reports_the_checkpoint_diff_counts` — a real turn reports
  `checkpoint_added=2`, `checkpoint_removed=1`, `checkpoint_diff_paths=1` on
  `turn_end`; the stored checkpoint is frozen.
- `test_a_checkpoint_freezes_the_turns_diff` — the diff is computed once and
  does not change when the file is edited after the turn.
- `test_a_created_file_diff_is_all_added` — a created file has `+1 -0`, a
  `/dev/null` source header and the added line.
- `test_a_binary_file_has_no_inline_diff` — a NUL-containing file is marked
  `binary`, carries no patch text, and explains the size change.
- `test_a_checkpoint_diff_does_not_read_a_replaced_symlink` — a target replaced
  by a symlink is `unavailable`; the outside target's content is never read or
  included.
- `test_bridge_carries_the_checkpoint_facts` — the bridge carries the new diff
  counts and the truncated flag as serializable `TurnEnd` facts.

The diff is computed from the checkpoint's pre-write bytes and the current file
bytes. It never runs a command or writes a file.

## 3. TUI evidence

New tests in `test_premium_features.py`:

- `test_v_shows_the_frozen_checkpoint_diff` — pressing `V` in nav mode opens
  `DiffModal`; it shows `frozen at turn end`, `note.txt · modified · +1 -1`,
  `-original` and `+changed`. The same test closes it and opens it again via
  `/diff`, so the composer command path is covered too.
- `test_receipt_records_the_checkpoint_diff_summary` — the receipt has
  `diff: +2 -1 across 1 path` and `view: V / /diff`.
- `test_turn_end_carries_diff_summary_to_the_receipt` — the app wiring from
  `EndAgentTurn` to `TurnReceipt.note_checkpoint` carries the diff counts and
  adds the truncation risk to the receipt.

`DiffModal` is read-only: `C` copies, `V`/`Esc` closes. It has no edit, apply or
per-file restore action.

## 4. Offline gate

```bash
./demo/check_all.sh
```

Result:

```
13 passed   0 failed   1 skipped   26s
READY (offline) - run with --live to rehearse the real model.
```

The skip is the live rehearsal (not requested).

## 5. Live gate — two consecutive passes

After the diff change, with the free tier available again:

```bash
./demo/check_all.sh --live
./demo/check_all.sh --live
```

Both runs:

```
attempt 1 (one model, real tool call): exit 0
attempt 2 (rotation: two models, switch card): exit 0
14 passed   0 failed   0 skipped   34s
READY (offline + live) - live model, tool call and visible switch all passed.
```

The second run took 36s with the same result. This is a real free model calling
a tool and a visible switch card at `$0.0000`; it is not a mock run. The live
gate is headless and does not press `V`; the diff card itself is verified by the
TUI tests above.

## 6. Limits

- Diff text is bounded: 600 lines per file, 1,200 lines total, 256 KB per side.
- Binary files, oversized files and truncated diffs are named; the card never
  implies the whole file was reviewed.
- Symlinks and paths outside the checkpoint workspace are refused before read.
- The diff is frozen at turn end; later edits do not rewrite the receipt's
  evidence.
- No editable patch, no per-file selection, no patch export beyond plain-text
  copy, no durable diff store.
- The diff is not a replacement for `git diff` or a code review.
