# 05 — Tamias terminal agent: product-surface inventory

> **Status note (27 Oct 2026):** this is the pre-fix audit snapshot. The
> stop-ship findings in §4 and §5 — investigation-tool fence leaks, the
> absolute-path `deny_read` bypass, the `update_plan` denial, headless runs
> with no policy, fabricated savings, the empty per-model spend table,
> fabricated task progress, unredacted audit bodies and the uninstallable
> package — were fixed in `docs/AGENT-LANDSCAPE.md` §8. The list below is kept
> as the audit trail, not as current status.

**Method.** Primary evidence: `agent.py` (4,183 lines), the eleven `tui/` modules
(2,988 lines), the two policy TOMLs, `models/catalog.json`, `providers.py`,
`model_catalog.py`, `brief.py`, `context_index.py`, `bench.py`, and all four test
files. I read them, ran the gate (`300 passed in 6.1s`, Python 3.14.4), and drove
the policy engine, tool dispatcher and cost ledger directly from a read-only
REPL. Documentation is treated as claims to check, not evidence: where docs and
code disagree, the code wins and the drift is recorded. Anything the tree cannot
show is marked **Inference**.

## 1. What actually ships

One Python process, one OpenAI-compatible client, one Textual frontend. No
server, daemon, database or session file.

| Layer | What it is | Where |
|---|---|---|
| Turn loop | synchronous `chat.completions` calls, tools dispatched serially | `agent.py:3491-3860` |
| Tools | 18 JSON-schema tools: 7 file/shell, 1 plan, 5 investigation, 2 measurement, 3 session records | `agent.py:482-860` |
| Policy | TOML: tool allow/deny, shell families, path globs, domain gate, model allowlist, audit path | `agent.py:2064-2260` |
| Frontend | Textual app, 11 keybindings, 12 slash commands, task board, credits modal | `tui/app.py` |
| Routing | free → mid → premium by tool failures and prompt size | `agent.py:3049-3085` |
| Catalog | 54 models: 16 free / 24 mid / 14 premium, paid gated | `models/catalog.json`; `providers.py:89-140` |
| Offline | brief compiler, symbol index, cost-per-success harness | `brief.py`, `context_index.py`, `bench.py` |

State lives in module globals (`history`, `COMPANY_ID`, the investigation and
unknown registries), so a process is the only session (`agent.py:200-410`).
The repository is not installable: `pyproject.toml` declares `tamias = "tamias.cli:main"` and there is no `tamias/` package, and its
build backend `setuptools.backends._legacy:_Backend` does not exist in setuptools
78.1.1 (verified), so `pip install .` fails twice over (`pyproject.toml:3,17`).

## 2. Capability table

`CC` = Claude Code (`01-claude-code.md`), `CX` = Codex CLI (`02-codex-cli.md`),
`OC` = OpenCode (`03-opencode.md`).

| Capability | Status | Evidence | Notes |
|---|---|---|---|
| Multi-step tool loop | have | `agent.py:3491-3860` | 25 steps per turn by default (`agent.py:2835-2838`); sequential dispatch |
| Tool breadth | partial | `agent.py:482-860` | No web fetch, LSP, notebook, image input; investigation tools are keyword scans (§5.3) |
| Streaming output | missing | no `stream=True`; one `emit("message")` at `agent.py:3853` | CC, CX and OC stream tokens |
| Turn cancellation | missing | `tui/app.py:337`; `tui/bridge.py:174-245` | Turns queue; nothing can abort one |
| Session persistence | missing | `agent.py:200` | No list, resume, fork; closing the TUI loses the transcript |
| Project instructions | missing | `agent.py:146,195` mention `AGENTS.md` only in comments | CC, CX and OC all load project rule files |
| MCP / hooks / skills / subagents | missing | no client, loader or scheduler in tree | All three competitors have at least MCP |
| Headless interface | partial | `agent.py:2830-2834,4156` | Text only; no JSON/SDK; exit 1 lumps refused, error, cap and ceiling (`agent.py:3904-3914`) |
| Policy engine | have | `agent.py:2335-2455` | Deterministic and offline; the domain gate runs before the model; three bypasses in §5.1 |
| Ask gate, fail-closed | have | `agent.py:2397,2522`; `tui/bridge.py:167` | No handler → deny; the TUI supplies one |
| Managed policy | partial | `agent.py:2264-2315` | TLS trust only; the gateway verifies the signature (`docs/BOUNDED-AGENT.md:146-149`) |
| Workspace fence | partial | `agent.py:1414-1429,1251-1474` vs `1578,1688,1783,1886` | Enforced on six path tools; investigation tools call only the company fence |
| Secret denylist | have | `agent.py:1059-1065,1102-1120,1176-1195` | `.env` refused; shell gets a scrubbed environment |
| Cost accounting | partial | `agent.py:2947-2965,3317-3360`; `tui/credits.py:110-143` | Reads provider `usage.cost`; missing cost is `None`, never `$0`; ceilings checked after the spend |
| Model routing | have | `agent.py:3049-3085` | Escalates only on failures or context size; no failover |
| Compaction | have | `agent.py:2690-2735` | 40,000-char trigger; LLM summary with structural fallback |
| Plan | partial | `agent.py:2025-2065`; `policies/todoinc-todo.toml:26` | A tool, not a mode; the shipped policy denies it |
| Diff / undo / checkpoints | missing | `agent.py:1300-1303` | First-match string replace, no preview, no checkpoint |
| Spend UI | partial | `tui/credits.py:193-203`; `tui/app.py:780`; `tui/bridge.py:125-133` | Per-model rows never populate; savings are invented |
| Tests | have | 300 passed | Two blind spots and a stale count (§5.5) |

The shape is a Claude Code-class loop with a governance layer bolted on, minus
the table stakes the other three treat as baseline: streaming, resume, MCP,
project rules and machine output. Architecturally it is closer to Aider: one
process, one model at a time, no extension surface.

## 3. What is genuinely differentiated

**The policy file is the product boundary, not a mode.** Rules are declarative,
offline, and evaluated before any model call (`agent.py:3455,2491-2522`). Denial is
terminal: a policy refusal is classified as a deliberate refusal and ends the
turn (`agent.py:1079-1083,3830-3838`), and an ask-gated call with no human is
denied rather than allowed (`agent.py:2397,2522`). CC, CX and OC treat denial as
feedback for the model to route around; Tamias treats it as a stop. Coherent for
a supervised boundary demo; hostile for interactive work (§4.6).

**A cost ledger that refuses to guess.** `usage_cost` returns `None` for a
missing, malformed or negative provider cost, and the turn counts an
`unpriced_steps` total instead of folding it in as free (`agent.py:2947-2965`,
`3317-3360`). The UI can therefore say "cost unknown" rather than lie, and the
compaction call is billed into the same tally (`agent.py:2709-2711`). The figure is what the provider
billed, not an estimate from a local price table.

**Investigation-before-build is enforced, not suggested.** `build_similar`
refuses unless an investigation has been recorded in the session registry
(`agent.py:1877-1885`); no competitor blocks a write on "you have not
investigated". The catch is that the investigation is a keyword scan (§5.3), so
the gate enforces a ritual more than a method.

**Boundary refusal has its own outcome.** A blocked turn returns `"refused"`,
not an exception or a generic error (`agent.py:3838`), the CLI prints
`REFUSED` and exits 1 (`agent.py:3904-3913`), and the task board records
`blocked` instead of 100% (`tui/tasks.py:152-159`). That vocabulary survives to the UI.

**Measurable governance, offline.** `bench.py` pre-registers a 20% cost-per-
success gate with a 2-point pass-rate tolerance and ships no results
(`bench.py:1-31`). The brief compiler and symbol index are offline and testable
(`brief.py:1-20`, `context_index.py`). Together they are the honest core of the
"cheaper per success" claim: a harness, not a result.

## 4. Top 20 gaps vs a production terminal agent

Ordered by user impact.

1. **Investigation tools are an unfenced read primitive.** `investigate_target`,
   `trace_feature`, `analyze_structure` and `build_similar` never call
   `resolve_in_workspace`, and their company check no-ops without a company id
   (`agent.py:1578,1688,1783,1886`; `1414-1429`). Verified:
   `investigate_target("/etc/hostname", ...)` returns findings while
   `read_file("/etc/hostname")` refuses.
2. **`deny_read` and `allow_write` are ignored for absolute paths.** `_glob_any`
   checks `abspath` only when the input is relative (`agent.py:2326-2333`).
   Verified: the relative `company/work/todoinc/apps/chatbot/x.py` is denied; the
   absolute form returns `None` from `policy_check`.
3. **No streaming.** The reply is emitted once, after the whole turn
   (`agent.py:3853`). A 30-second tool-heavy turn is a frozen screen; CC, CX
   and OC all stream.
4. **No way to stop a turn.** `ctrl+c` quits the app (`tui/app.py:337`), and the
   worker blocks on `run_turn` (`tui/bridge.py:241`). A runaway loop can only be
   killed, taking the session with it.
5. **Tool results are invisible in the TUI.** `ToolCard.finish` accepts `result`
   and renders only a status glyph (`tui/widgets.py:51-62`). The plain REPL
   prints 800 characters (`agent.py:3390`); the flagship UI prints none.
6. **Planning is mandated but denied.** The prompt says to publish a plan first
   (`agent.py:878`), while the shipped policy's allowlist omits `update_plan`
   (`policies/todoinc-todo.toml:26`). Verified: `policy_check("update_plan", …)`
   returns a deny, and any denial ends the turn (`agent.py:3800-3838`).
7. **Headless `--task` runs with no policy at all.** The deployment default is
   applied only when `not args.task` (`agent.py:4100-4105`). With no `--policy`,
   `policy_check` returns `None`, `run_shell` is enabled by default
   (`agent.py:1140-1142`), and writes are ungated — contradicting
   `demo/README.md:35`.
8. **No resume.** `history` is a module global (`agent.py:200`); there is no
   `--continue`, no session id, no transcript on disk.
9. **No project instructions.** `AGENTS.md` is never read; only the agent's own
   hardcoded prompt is sent (`agent.py:872-895`). The model cannot learn a
   repository's conventions.
10. **No MCP, hooks, skills or subagents.** Zero extension points; the 18 tools
    are the whole world.
11. **No machine-readable interface.** `--task` prints prose and a banner
    (`agent.py:4145-4156`); nothing parses: no `--output-format`, no SDK, no
    server.
12. **A 429 ends the turn.** The error is classified and reported
    (`agent.py:3655-3679`) but there is no retry, backoff or failover to
    another catalog model.
13. **Limits destroy the turn.** The step cap, prompt ceiling and API error all
    run `del history[checkpoint:]` (`agent.py:3493,3619,3656`), so hitting a
    limit erases the work instead of pausing it.
14. **`edit_file` replaces the first match blindly** with no uniqueness check and
    no diff (`agent.py:1276-1303`); there is no undo and no checkpoint.
15. **Tools run strictly serially** inside one response (`agent.py:3735-3835`),
    so the prompt's "independent calls can go out together" buys nothing.
16. **The spend UI contradicts itself.** Every `turn_end` emit omits
    `model`/`tier` (e.g. `agent.py:3855-3860`), and the bridge drops them anyway
    (`tui/bridge.py:125-133`), so `model_spend` is always empty
    (`tui/credits.py:133-143`) while the modal still shows premium-equivalent
    and "money saved".
17. **Progress is fabricated.** Each tool call adds 9% capped at 95%, and any
    finished reply sets 100% (`tui/tasks.py:142-150`). A turn that changed
    nothing reads as complete.
18. **The shell policy is substring matching over `shell=True`.** `"rm "` misses
    `rm\t`, `/bin/rm` and interpreter payloads, and there is no OS sandbox
    (`agent.py:2355-2362,1224-1236`). The code calls this best-effort
    (`agent.py:1148-1152`); it is still the fence for `run_shell`.
19. **No configuration surface.** No config file, no `--model`, no theme or
    keybinding: behaviour is env vars (`AGENT_MODEL`, `TAMIAS_ALLOW_SHELL`)
    plus TUI cycling (`agent.py:35,143`).
20. **It cannot be installed.** Dangling console script and a non-existent build
    backend (`pyproject.toml:3,17`); even run from source, the `Queue` annotation
    in `tui/app.py:345` only works on 3.14 while the project claims `>=3.11`
    (`pyproject.toml:8`).

## 5. Rough edges visible in code

### 5.1 The fence leaks in three places

- `resolve_in_company_workspace` returns the path unchanged when `company_id` is
  falsy — the comment says it "reject[s] nothing here" (`agent.py:1426-1429`).
  Every path tool pairs it with `resolve_in_workspace`; the four investigation
  tools do not (`agent.py:1578,1688,1783,1886`). Verified against `/etc/hostname`.
- `_glob_any` cannot match an absolute path against a relative glob: it tests
  the absolute form only for relative inputs (`agent.py:2326-2333`), so
  `deny_read` fails open for exactly the paths an agent tends to emit.
- `PATH_ARG` maps six tools (`agent.py:2072-2079`); `investigate_target`,
  `trace_feature`, `analyze_structure` and `build_similar` are absent, so the
  path rules are never even consulted for them.

### 5.2 Accounting and UI honesty

- All seven `turn_end` emits omit `model` and `tier`; the dataclass has the fields
  (`tui/events.py:81-93`) and the ledger only records model spend when `model` is
  non-empty (`tui/credits.py:133`). Passed through the real event path,
  `model_breakdown()` is empty while `estimated_savings_usd()` is not.
- `tui/app.py:780` computes `estimated_savings = self.ledger.spent_usd * 0.5`
  and labels it "conservative" — a number with no baseline.
- `tui/credits.py:271` renders a `💰 VS PREMIUM` row, and `tui/app.py:460-465`
  renders `💰 saved: $X`, while `docs/FRONTEND_REFERENCE.md:114,719,749` says
  there is no savings rate and no emoji.
- The guard test asserts the *word*: `test_tui_features.py:123` rejects
  `"savings"`/`"SAVINGS"` in the dashboard text, which the `VS PREMIUM` label
  does not contain. The test passes; the behaviour it names does not exist.

### 5.3 "Investigation" is grep with headers

`investigate_target` lowercases the feature string and substring-matches every
line, capped at 15–20 hits (`agent.py:1600-1665`). `trace_feature` does the same
and follows imports by rewriting `a.b` to `a/b.py` relative to the *cwd*, not the
file (`agent.py:1717-1745`). `build_similar` writes nothing; it prints a
"records the build intent" report and tells the model to use `write_file`
(`agent.py:1909-1922`). The tool descriptions promise call chains and
implementation (`agent.py:642-736`); the code delivers keyword context.

### 5.4 Lifecycle and portability

- `WORKSPACE = os.getcwd()` at import time (`agent.py:870`): the fence is fixed
  to the launch directory, and every tool reads `COMPANY_ID` through
  `globals().get` rather than a parameter.
- The audit row stores full tool arguments (`agent.py:2478`), including file
  content for writes, and a failed audit write is swallowed (`agent.py:2486-2488`).
- `tui/app.py:345` annotates with `Queue`, which is never imported; it survives
  only under PEP 649 (3.14). On the declared minimum, the class body raises at
  import.

### 5.5 Test and document integrity

The gate is real (300 tests: 221 + 46 + 14 + 19 by file) and does not test the
bypasses in §5.1: the policy path tests use relative paths only
(`test_agent.py:2192`). The docs still say 264 (`docs/RELEASE-STATUS.md:47`,
`docs/audit/claims.md:14`), and `tests/test_docs_integrity.py:83-96` hardcodes
`"264"` while only rejecting the older 932/963/934/988 — so it cannot notice the
number it is supposed to guard.

## 6. What this inventory does not cover

Live model quality, latency, and the gateway's Ed25519 verification
(`docs/BOUNDED-AGENT.md:146-149`) are outside this tree; the signing, metering
proxy is another repository. No cost claim here is measured beyond the ledger
arithmetic above. The strongest honest summary
is that Tamias has a real, unusual governance spine and a competent single-agent
loop, and that the frontend and the fence both need one more pass before either
can be demoed as finished.
