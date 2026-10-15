# AGENTS.md — tamias-agent (the demo's agent interface)

**Read `/home/krish/Desktop/HANDOFF-CODEX.md` first, in full.** This repo is
covered by its §1 (identity), §2 (inventory) and §14.3 (live rehearsal).

## Supersession notice

**Ignore `AGENT-RULES.md`** anywhere in this project — obsolete (written for a
five-parallel-agent phase that forbade merging). Keep its rules 3–9 (project
venv only, never weaken a test, never `git add -A`, never print secrets, evidence
for every claim).

## This repo's role

- `agent.py` (~2.4k lines) + `tui/` — the terminal agent that is demoed
  **through** the Tamias proxy on port 8000.
- `test_agent.py` (~3.2k lines) + `test_tui_features.py` (~600 lines) — the two
  suites, run separately (one process hangs); see "Run it".
- `brief.py` — the offline brief compiler (D13, `docs/BRIEF.md`).
- `context_index.py` — the offline symbol/name/content index (D14,
  `docs/CONTEXT-INDEX.md`).
- `bench.py` — the cost-per-success benchmark harness (D17, `docs/BENCHMARK.md`).
- Not part of the published `tamias` package. It is a **demo dependency**.

## Hard rules specific to this repo

1. **`.env` is off-limits.** It holds `OPENROUTER_API_KEY`. Never `cat`, `grep`,
   `printenv`, `echo`, or include it in any output, log, commit or report.
2. **Never commit `.env`.** It is ignored (`.gitignore:1`) — keep it that way.
3. **Live rehearsal rule:** Tier B (live agent through the proxy) is shown only
   after **two consecutive passes**. Free models 429. If it fails twice, drop to
   the offline act and say so honestly — never claim a run you did not do.
4. **Do not push.** The repo *does* have a remote (`github-https` →
   github.com/kr1shnac/tamias-agent), but nothing has been pushed. Do not push,
   retag or force anything without explicit instruction.

## Run it

```bash
cd /home/krish/Desktop/tamias-agent
.venv/bin/python -m pytest test_agent.py -q        # suite
.venv/bin/python agent.py --task "..."             # non-interactive
```
