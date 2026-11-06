# Boundary hardening evidence — 2026-11-06

This is the recorded evidence for the first boundary-hardening batch, after the
2026-10-31 council review. It intentionally records failures, not only passes.

## What was run

```bash
cd /home/krish/Desktop/tamias-agent
.venv/bin/python -m pytest -q
./demo/check_all.sh
.venv/bin/python demo/attack_boundary.py
```

## Results

- Full suite: **381 passed in 16.10s**.
- Offline gate: **13 passed · 0 failed · 1 skipped · 31s**. The skip is
  `live rehearsal`.
- Adversarial boundary harness: **6 PASS · 4 GAP · 2 NOTE**, exit code `3`.
- `check_boundary`: 17/17 probes still pass.
- `showcase`: 18/18 to-do boundary probes still pass.
- Mock model: in-scope write still ask-gated, out-of-scope write refused.
- No live model run was claimed.

## What changed

1. `read_path_refusal` in `agent.py` applies the secret/path fence to every
   returned path from `list_directory`, `search_in_files`,
   `analyze_structure`, and `investigate_target`.
2. `test_boundary_walkers.py` adds composition tests for parent-directory reads.
   They assert both denial and the presence of a legitimate in-product control
   hit.
3. `demo/attack_boundary.py` adds an offline adversarial harness that reports
   literal `PASS`, `GAP`, and `NOTE` rows.
4. `demo/check_all.sh` now runs the full offline suite, not just the agent and
   TUI subsets.

## Remaining attack findings

The following rows are still `GAP` in `demo/attack_boundary.py`:

- `composite shell gate`: an allowed shell family can be followed by another
  command tail.
- `cross-project shell path`: `git log -p apps/chatbot/...` passes the policy
  gate from the company cwd.
- `no-policy run gate`: `policy_check` returns `None` when no policy is active.
- `no-policy audit row`: `policy_audit` writes no row when no policy is active.

These are production-blocking gaps, not demos. Do not report “unbypassable” or
“company guarantee” until they are closed.
