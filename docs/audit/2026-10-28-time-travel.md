# Evidence log — Time Travel v1 (file checkpoints)

**Date:** 2026-10-28
**Branch:** `feature/liquid-glass-tui`
**Scope:** the first rewind slice — capture the pre-write bytes of tracked
files, preview them, and restore after explicit confirmation. This log records
what was run. It does not claim conversation restore, durable storage, shell
capture or a live pass at the time. The later diff slice passed the live gate
twice consecutively; see `docs/audit/2026-10-29-diff-capture.md`.

---

## 1. Full test suite

```bash
.venv/bin/python -m pytest -q
```

Result:

```
366 passed in 14.41s
```

Breakdown:

| Suite | Tests |
|---|---:|
| `test_agent.py` | 241 |
| `test_tui_features.py` | 50 |
| `test_premium_features.py` | 37 |
| `tests/` (docs integrity + model catalog) | 34 |
| Workspace demo tests | 4 |
| **Total** | **366** |

The gate's pytest check (the four files used by `demo/check_all.sh`) is:

```
343 passed in 14.49s
```

## 2. Core evidence

New tests in `test_agent.py`:

- `test_a_write_creates_a_restorable_checkpoint` — a created file is captured
  and removed by restore; the checkpoint id starts `cp-`.
- `test_a_created_directory_is_removed_by_restore` — `create_directory` is
  captured as a directory even when it does not exist yet; restore removes it.
- `test_a_checkpoint_restores_an_overwritten_file` — the original bytes, not
  the agent's new bytes, are restored.
- `test_a_shell_call_marks_the_checkpoint_incomplete` — a shell call sets
  `shell_ran`; restore warns that shell changes are not captured.
- `test_a_read_only_turn_has_no_checkpoint` — a read does not create an empty
  checkpoint.
- `test_a_checkpoint_never_restores_outside_its_workspace` — a manually forged
  outside path fails and leaves the outside file untouched.
- `test_restore_refuses_a_symlink_that_replaced_the_file` — a target replaced
  by a symlink is refused; the link target is untouched.
- `test_a_failed_restore_can_be_retried` — a non-empty created directory fails
  and leaves `restored_at` unset; after the blocker is removed, the retry
  succeeds.
- `test_bridge_carries_the_checkpoint_facts` — the bridge carries
  `checkpoint_id`, `checkpoint_files` and `checkpoint_shell` on `TurnEnd`.

The checkpoint is captured only after the plan, dossier and policy gates allow
the call, so a held or denied write never produces a checkpoint.

## 3. TUI evidence

New tests in `test_premium_features.py`:

- `test_z_previews_and_restores_the_last_checkpoint` — `Z` opens the
  `ConfirmModal`, shows the path and `modified`, `Y` restores the original
  bytes, clears the active id and marks the checkpoint restored.
- `test_z_cancel_leaves_the_checkpoint_files_untouched` — `N` leaves the
  changed file alone and keeps the checkpoint available.
- `test_z_keeps_a_failed_checkpoint_available_for_retry` — a non-empty created
  directory fails, the active id stays, and `restored_at` remains unset.
- `test_receipt_records_the_checkpoint_and_shell_limit` — the receipt has a
  `CHECKPOINT` section, the id, `shell: ran — not captured`, the
  `Z / /checkpoint` hint and the shell risk.

The receipt's `RESTORE` section is written by `TurnReceipt.note_restore`; a
failed path is listed there and added to RISKS. A restore with any failure does
not set `restored_at`, so the human can fix the blocker and retry.

## 4. Wheel packaging

`pyproject.toml` now lists `checkpoints` in `py-modules`. A wheel built with
`python -m pip wheel . --no-deps` contains `agent.py` and `checkpoints.py`; the
clean-install check remains blocked by the PyPI timeout noted in
`docs/RELEASE-STATUS.md`.

## 5. Offline gate

```bash
./demo/check_all.sh
```

Result:

```
13 passed   0 failed   1 skipped   29s
READY (offline) - run with --live to rehearse the real model.
```

The skip is the live rehearsal (not requested).

## 6. Live gate — attempted, rate-limited

```bash
./demo/check_all.sh --live
```

Result after the checkpoint code (two attempts, 30s and 31s):

```
13 passed   0 failed   1 skipped   30s
SKIP  live: 0/2 passed - rate-limited (free tier); not claimed as proven
```

Both attempts stopped at the provider's free-tier daily model limit
(`429`/rate-limit). A manual run with a different free model
(`google/gemma-4-31b-it:free`) hit the same provider limit. **No live pass is
claimed for this slice.**

The last live pass was the contract/dossier core immediately before the
checkpoint wrapper: two consecutive runs, `14 passed   0 failed   0 skipped`
(29s and 30s), with a visible switch. That evidence is in
`docs/audit/2026-10-28-plan-contract.md`; it does not prove the checkpoint
wrapper live. The checkpoint wrapper is exercised by the offline mock loop and
the tests above.

## 7. Limits

- Files only: `write_file`, `edit_file`, `create_directory`.
- In memory for the session, last 20 retained; the v1 UI exposes the latest;
  no durable store.
- A shell call marks the checkpoint incomplete; shell changes are not captured.
- No conversation restore, diff preview or selective per-file restore.
- Empty parent directories created by a new file may remain.
- A restore overwrites current edits to tracked files; the confirmation says so.
- The checkpoint is not a substitute for version control.
