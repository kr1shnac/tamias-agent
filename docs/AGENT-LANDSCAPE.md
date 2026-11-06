# The agent landscape and Tamias

**Decision review — 27 October 2026**

This is the "what should Tamias become?" document. It is based on shipped
artifacts, source code and official docs for 13 terminal agents and 7 hosted or
IDE agents, plus a line-by-line audit of this repository. Per-agent evidence
lives in `docs/research/01-claude-code.md` … `05-tamias-inventory.md`; file and
URL citations below point there.

The experience architecture that follows from this survey is in
[`docs/PREMIUM-AGENT.md`](PREMIUM-AGENT.md): the accountable-agent thesis, the
user's inner monologue, the signature system and the keep/cut/add decisions.

---

## 0. Verdict

**Tamias has the strongest governance story in this survey and the weakest
table stakes of any product it will be compared with.**

The policy file, fail-closed ask gate, honest cost ledger, model roster and
audit trail are genuinely differentiated. Twelve of the thirteen terminal
agents studied here have MCP (Aider is the exception); Tamias has none. Most
have durable sessions; Tamias loses the transcript when the TUI closes. Every
serious competitor streams tokens; Tamias emits the whole reply at the end.
Those gaps are not "polish". They are the door through which a buyer decides
whether the governance argument is worth hearing.

The good news: the moat is hard to copy and the table stakes are well
understood. The bad news: the current build also had defects that made the demo
less honest than its own documentation. Those are fixed in this round (§8).

**One-line strategy:** close the table-stakes gap with a small, auditable Python
implementation, then sell the one thing the field does not have — a signed,
project-bound policy with real cost accounting and an audit trail that joins
tool decisions to metered calls.

**Do not** try to out-feature Claude Code, Codex or OpenCode. They are runtimes
with hundreds of engineer-years behind them. Beat them on a narrower promise:
*the agent a company can actually bound, audit and afford.*

---

## 1. Scope and method

### What was studied

| Terminal agents | Hosted / IDE agents |
|---|---|
| Claude Code 2.1.289 | Devin |
| OpenAI Codex CLI 0.162.1 | Cursor (GUI) |
| OpenCode 2.0.32 | Windsurf / Devin Desktop |
| Gemini CLI | Replit Agent |
| Aider | Lovable |
| Cline | Bolt.new |
| Continue | v0 |
| Cursor CLI | |
| Goose | |
| Crush | |
| Amp | |
| Warp Agent CLI | |
| GitHub Copilot CLI | |

### Evidence classes

1. **Shipped artifacts** — the Claude Code prompt corpus (827 files extracted
   from the npm package, v2.1.289); the installed Codex and OpenCode binaries
   and their `--help` surfaces.
2. **Upstream source** — Codex (`openai/codex`), OpenCode (`sst/opencode`), and
   the open-source cohort, read at file:line level.
3. **Official docs/READMEs** — for closed products (Claude Code's UX docs,
   Cursor, Amp, Warp, Copilot, hosted agents).
4. **This repository** — `agent.py`, `tui/`, policies, tests, demo scripts.

### Honesty about limits

- The REA MCP server was not connected in this session, so no `rea` binary
  analysis was run. The Claude Code evidence is the shipped prompt corpus plus
  docs, not a decompiled bundle. Codex/OpenCode were read from source, which is
  stronger for their open parts.
- Closed products (Claude Code's internal loop, Cursor, Amp, Warp, Copilot,
  hosted agents) are described at the product/behavior level, not internals.
- Scores in §5 are judgment, not measurement. They are labeled as such.
- No competitor was run against a benchmark. This is a product review, not an
  eval.

### Why this shape

The field splits into three architectural families:

- **Prompt-and-loop products** (Claude Code, Aider): the value is the prompt
  build, the tool descriptions and the editing loop.
- **Event-runtime products** (Codex, OpenCode, Crush, Goose): the value is a
  typed event log and a server that many clients can attach to.
- **Environment products** (Devin, Cursor GUI, Replit, Bolt, v0): the value is
  the sandbox, preview and review surface, not the chat.

Tamias is currently a fourth thing: **a policy kernel with a demo agent around
it.** That is a viable category, but only if the agent is credible enough to
carry the kernel.

---

## 2. What the field has converged on

These are not differentiators anymore. They are the expected surface. Ranking
is by how many of the ten terminal agents document the feature and how
load-bearing it is.

| # | Table stake | Best implementation | Why it is load-bearing | Tamias before this round | Tamias now |
|---|---|---|---|---|---|
| 1 | **MCP client** (stdio/HTTP, OAuth) | Codex, Goose | The extension economy; 12/13 agents here have it | missing | missing |
| 2 | **Per-tool allow/ask/deny, persisted** | Codex, Cursor CLI | Approval fatigue is the adoption killer | policy file, not interactive; no persistence | partial |
| 3 | **Selective checkpoints** (files/chat/both) | Cline, Gemini CLI | Undo is the safety net for autonomy | missing | missing |
| 4 | **Resume, list, fork** | OpenCode, Codex | A session that dies with the terminal is a toy | missing | missing |
| 5 | **Plan mode** (read-only before writes) | Cline, Copilot CLI | Separates investigation from mutation | plan tool, not a mode; was denied by policy | partial |
| 6 | **`AGENTS.md` / project rules** | Codex, Claude Code | The model must learn the repo, not just the task | missing | missing |
| 7 | **Headless JSON** for CI | Codex `exec --json`, OpenCode `run --format json` | Makes the agent scriptable and testable | text only, exit 1 lumps outcomes | missing |
| 8 | **Context meter + compaction** | Codex, OpenCode | Long tasks die without it | compaction exists; no meter | partial |
| 9 | **Subagents** with isolated context | Claude Code, Codex | Keeps the main window clean; parallel work | missing | missing |
| 10 | **Hooks and skills** | Claude Code, Codex | Team-specific behavior without forking | missing | missing |
| 11 | **OS sandbox + network control** | Codex (Seatbelt/bwrap), Claude Code | A permission prompt is not containment | substring shell rules only | weak |
| 12 | **Model picker + BYOK** | OpenCode (230 providers) | Cost/quality control | catalog + rotation + free/paid gate | good |
| 13 | **Per-turn cost display** | Claude Code, Codex | Trust and budgeting | ledger exists; UI was partially fabricated | good |

Two more have become table stakes in the TUI cohort even though they are not
"features" in the docs:

| # | Expectation | Best implementation | Tamias |
|---|---|---|---|
| 14 | **Streaming + cancellation** | all ten | missing |
| 15 | **Diff review + undo** | OpenCode "last turn" diff, Aider git commits | missing |

**Conclusion:** Tamias is fully missing 9 of these 15 and only partial on 3
more. The governance layer cannot compensate for a product that cannot resume,
stream, undo or connect to MCP. This is the order of the roadmap in §9.

---

## 3. Deep dives

### 3.1 Claude Code — the prompt build system

**Architecture.** The shipped prompt is not one prompt; it is 827 fragments
(281 `system-*`, 256 `tool-description-*`, 137 `data-*`, 82 `agent-*`) with
version headers, variables and conditional slots. `CLAUDE.md` is delivered as a
user message *after* the system prompt, which makes it advisory rather than
configuration. Permission precedence is the product: deny rules win in every
mode, ask rules outrank allow rules, then mode, then sandbox, then the
auto-mode classifier, then hooks. Subagents, compaction, JSONL sessions,
checkpoints and hooks are all first-class (`01-claude-code.md:15-190`).

**UX details worth stealing.**

- **Permission prompts** annotate Yes/No with Tab; Shift+Tab cycles modes; a
  Bash denial offers "Yes, and switch to auto mode".
- **Plan mode** is read-only; the plan file is the only writable artifact;
  `Ctrl+G` opens it in `$EDITOR`.
- **Todo list** sits above the prompt on `Ctrl+T`; it is not the task board.
- **Queue with takeback:** Enter queues, `Ctrl+Enter` sends now, `↑` takes the
  queued message back, Esc interrupts and keeps the queue. This is the best
  interaction detail in the survey.
- **Rewind:** 100 checkpoints, one per turn-starting prompt, with four restores
  — code + conversation, conversation only, code only, summarize from here.
- **Cost meter:** spinner shows output tokens; `/context` shows consumers;
  `/usage` is a list-price estimate, explicitly not an invoice.

**Production.** OAuth/keychain/API key/Bedrock/Vertex; telemetry with code and
prompts excluded; opt-in sandbox with credential masking; enterprise managed
settings that outrank project settings; headless `-p` with JSON/stream-JSON,
`--allowedTools`, `--max-turns`, `--max-budget-usd`; IDE bridge that feeds open
file, selection and diagnostics into context (`01-claude-code.md:238-267`).

**Weaknesses.** Prompt churn is enormous (827 files, 305 tracked versions;
2.1.288 alone added ~4,051 tokens). Context bloat is admitted. Permission
fatigue forced auto mode to become the default in 2.1.283. Rewind does not
restore Bash-only edits, most subagent edits, symlinks or mid-turn messages.
Read/Edit/WebFetch/MCP run outside the sandbox, which is the most misread
security property in the product. `/usage` dollars are estimates, not bills
(`01-claude-code.md:303-333`).

**Verdict for Tamias.** Copy the *disciplines*, not the sprawl: fragment-based
prompts with golden tests, tool descriptions that teach the decision boundary,
a truthfulness section with an observed-evidence rule, read-before-edit with
uniqueness failure, split rewind, and queue-with-takeback. Avoid 827-file
prompt churn and 100+ flags.

### 3.2 Codex CLI — the typed event runtime

**Architecture.** A 164-crate Rust workspace (5,556 `.rs` files, ~2.17M lines).
The TUI is a JSON-RPC *client* of a shared local `app-server` daemon; the same
typed `EventMsg` stream drives TUI, `exec --json`, IDE and desktop. The turn
loop drains `pending_input` before each model step, so mid-turn messages become
"pending steers" delivered at the next tool boundary. Everything is a typed
event; widgets emit intents, never mutate state. Redraws coalesce at 120 fps
(`02-codex-cli.md:25-82`).

**UX details.** No fixed grid: a variable-height inline viewport with typed
history cells (exec, patch, plan, approval, notice), each with
`compact()/display()/raw()`. 65 slash commands grouped by intent, not alphabet.
A configurable status line with ~29 items. A 20-segment rate-limit bar with
local reset times. Data-driven approval modals: the server sends
`available_decisions`, and labels are consequence-bearing ("Yes, just this
once", "Yes, and don't ask again for commands that start with `cargo test`").
Plan display is a first-class checklist cell; plan *mode* is separate. Images
paste mid-session. Notifications coalesce by priority and self-disable after a
failure. Onboarding includes a folder-trust modal that disables project config,
hooks and exec policies for untrusted folders (`02-codex-cli.md:84-136`).

**Safety.** Two orthogonal axes: sandbox (`read-only`, `workspace-write`,
`danger-full-access`) and approval (`on-request`, `never`, `granular`). macOS
Seatbelt, Linux bwrap + seccomp + `no_new_privs`, Windows MXC. Protected paths
inside writable roots: `.git` (including `gitdir:` targets), `.agents`,
`.codex`, `.aws`. Network off by default; allowlist-first proxy; DNS-rebinding
check fails closed; credentials injected at the proxy. Execpolicy is Starlark
`prefix_rule` with `match`/`not_match` unit tests. Auto-review routes approvals
to a reviewer model and fails closed on parse errors (`02-codex-cli.md:139-170`).

**Weaknesses.** Enormous. Responses-API lock-in. 167 feature flags. Default
environment passthrough does not filter `*KEY*/*TOKEN*/*SECRET*`. Base
instructions are server-delivered, so behavior is not fully auditable from
source. Session JSONL grows unbounded. Guardian adds model calls to approve
model calls — probabilistic, not enforcement (`02-codex-cli.md:200-208`).

**Verdict for Tamias.** Copy at small scale: one event bus, typed history
cells, protected paths, approval-as-data, pending-steer queue, layered config
with provenance, append-only JSONL sessions, `exec --json`, policy self-tests,
per-policy prompt fragments, configurable status line, feature registry. Do not
copy the daemon, 164 crates, 167 flags or Guardian.

### 3.3 OpenCode — the durable session server

**Architecture.** One shared local server per user with a `0600` registration
file holding URL, PID, version and password. TUI, `mini`, `run`, ACP, `api` and
web clients attach to it; version skew is refused. Sessions are event-sourced:
a durable `event` + `event_sequence` log is projected into `session_v2`,
`session_message`, `session_pending` and `session_inbox`, with strict replay
checks. Forks copy settled history at a boundary. A global SSE feed gives each
subscriber a 4,096-frame queue (`03-opencode.md:29-54`).

**UX details.** 241 bindable actions, `ctrl+x` leader, `ctrl+p` palette,
which-key panel. Session tabs with unread/error/attention state; attention
sorts first; closed-tab stack retains 25. Tail-first transcript mounts only the
newest rows, older rows on demand. Diff viewer with branch/committed/working/
**last turn** scopes, split/unified, file tree, hunk navigation, per-file
reviewed. Embedded terminal pane, editor handoff, 33 themes plus a
terminal-derived system theme. `opencode mini` is a split-footer client for
SSH/tmux, not a mode (`03-opencode.md:55-81`).

**Configuration and permissions.** Two planes: `opencode.json(c)` for
agent/project behavior; `~/.config/opencode/cli.json` for terminal
preferences. Merge order is surprising: global → direct configs from farthest
ancestor → `.opencode` configs → system; every `.opencode` file outranks every
direct file regardless of depth, and discovery walks above the repo root.
Rules are ordered `{action, resource, effect}`; last match wins; any deny
denies, else any ask asks; no match falls back to ask. Approvals are data:
once, always (save proposed patterns), or reject; reject rejects every pending
request; saved approvals are project-scoped and never override deny. The
default is allow-all except `.env` filename heuristics; there is no local
sandbox (`03-opencode.md:85-147`).

**Sessions and models.** Durable steer-vs-queue inbox; compaction with fixed
headings (`Objective`, `Requirements`, `Decisions`, `Work State`,
`Next Move`, `Relevant Files`, `Important Context`); sanitized JSON export;
`run --format json` typed records; `stats --json`. Bundled 5.4 MiB models.dev
snapshot with 230 providers and 8,894 models, plus local Ollama/LM Studio/vLLM
discovery; `provider/model#variant`; model-specific prompt overlays; a
small-model title agent. Retries: 2s → 4s → 8s, then 10s, 10 retries, honoring
`retry-after` up to 15 minutes (`03-opencode.md:150-173`).

**Weaknesses.** 35 packages, 50 migrations, 119 API paths; maximalism. Config
discovery above the repo. Allow-all defaults. "Permissions" without a sandbox
is a UX layer, not containment. 241 actions are hard to learn. LSP and share
are schema residue without a runtime (`03-opencode.md:177-218`).

**Verdict for Tamias.** The highest-leverage architectural copy is the
event-sourced session log + projections, but scaled to one SQLite file. Then
the durable steer/queue inbox, tabs/attention, "last turn" diff, two-plane
config, ordered rule data model (with deny-by-default), plan mode with one
writable directory, structured compaction headings, bundled model catalog and
`run --format json`. Do not copy allow-all defaults or perms-without-sandbox.

### 3.4 The rest of the terminal cohort

| Agent | What it is | Standout | What Tamias should take | What to avoid |
|---|---|---|---|---|
| **Gemini CLI** | TypeScript monorepo, React-Ink TUI over a separate core library | `/rewind` to any message, restoring conversation, code, or both; shadow-git commits make reverts inspectable; `/restore` rebuilds code | Selective rewind, extensions bundling MCP/commands/themes/hooks, headless JSON, trusted-folder sandboxing | Checkpointing ships disabled by default; conversation-only rewind can leave code and transcript disagreeing. Also: the CLI was replaced by Antigravity CLI for some users — a terminal surface can be withdrawn. |
| **Aider** | Python, one process, no server | Tree-sitter repo map sends only relevant definitions; every change auto-committed with a generated message; `/undo` reverses it; `--watch-files`; architect mode splits reasoning and editing across two models | Repo-map context selection; git-native undo; multiple edit formats; watch-files IDE bridge; auto-lint/test loop | No approval gate before writes; 100+ flags. The pre-governance generation. |
| **Cline** | One TS agent core shared by CLI (OpenTUI), VS Code, JetBrains, desktop, SDK | Shadow-git checkpoints with three restores (files/task/both), browsable per task; Plan vs Act modes; `--zen` background hub; cron and chat triggers | Checkpoint matrix, Plan/Act separation, background daemon, scheduled tasks, team subagents, MCP marketplace | Four clients + SDK + marketplace create config drift; auto-approve toggles can reproduce no-gate Aider. |
| **Continue** | TypeScript, Ink `cn` CLI plus IDE extensions | Everything declared in `config.yaml`: models/roles, rules, prompts, MCP, context providers, data destinations; same config in terminal and IDE; model roles for chat/edit/apply/autocomplete | Declarative portable config; named model roles; explicit context providers (`@docs`, `@files`); team config hub | Repo archived/read-only; a good config model with no maintainer is a dependency trap. Copy the idea, not the dependency. |
| **Cursor CLI** | Closed `agent` binary sharing Cursor's backend; Agent/Plan/Ask + cloud path | Permissions as typed tokens (`Shell()`, `Read()`, `Write()`, `WebFetch()`, `Mcp()`); allow/deny composition; `approvalMode` presets; sandbox + network toggle; `/rewind`; `agent ls/resume`; `&` cloud handoff | Typed permission DSL; three-mode split; session list/resume; cloud handoff; OS sandbox | Unrestricted mode is one flag away; binary sits inside the governance path with no inspectable policy. |
| **Goose** | Rust; interface/agent/extensions; desktop, CLI, API share the agent; extensions are MCP servers | Recipes as shareable YAML fixing prompt, extensions and parameters; sub-recipes and deeplinks; per-recipe tool scoping; fork/export; `goose acp` for editors; cron | Recipes; scheduling; session fork/export; ACP client/server; extension allowlists | 70+ extensions make install-time trust the security boundary; an allowlist is not runtime per-call policy. |
| **Crush** | Go + Bubble Tea v2; SQLite sessions; `crush serve` shared workspace | Genuinely fast keyboard-first TUI; LSP diagnostics feed the model; MCP stdio/HTTP/SSE + OAuth; skills, hooks, themes, notifications; sessions are rows, not scrollback; approvals become a shared inbox in serve mode | TUI craft; LSP context; shared server; durable SQLite sessions; MCP OAuth; desktop notifications | `crushrc` executes arbitrary Bash at startup — configuration that executes is a supply-chain hole. `--yolo` skips prompts. |
| **Amp** | Closed; Bun/TS CLI plus web/mobile; threads are server-side objects with URLs; Orbs are cloud machines | Shareable/unlisted/workspace-visible thread links; teammates attach to the same thread; "the Dial" (low/medium/high/ultra) fixes model+prompt+tools per thread; Task/Read Thread subagents; TS plugin API; orb-minute billing | Durable thread URLs; multiplayer/cross-client attach; cloud execution; plugin API; effort bundles | The Dial hides which model runs and what a thread costs until the bill; credits + orb-minutes + BYOK stack into unforecastable pricing. |
| **Warp CLI** | Standalone CLI over the same agent harness as the desktop app; native PTY multiplexer | Agent and human share one terminal, so the agent can drive REPLs, pagers and password prompts; `/handoff` snapshots uncommitted and untracked files to a cloud agent; `--resume` reattaches; tab bar per child agent; permission profiles, skills, MCP, statusline | PTY multiplexing; cloud handoff with working-tree snapshot; resume; child-agent orchestration; permission profiles | Credits meter every action with no pre-flight estimate; letting an agent drive a full-screen TUI can wedge the session. |
| **GitHub Copilot CLI** | Closed; npm umbrella package with platform binaries; GitHub-native | Plan mode (Shift+Tab) with ask/execute/autopilot beneath; LLM-assisted permission triage; rejection with inline feedback; `/sandbox enable`; `--cloud`; `--allow-tool` / `--deny-tool='shell(rm)'`; `/resume`; `/every`; custom agents, hooks, skills, memory | Plan mode; assisted triage; compaction + context meter; custom agents/hooks/scheduling; default GitHub MCP/ACP | Premium-request metering is opaque; autopilot + broad allow rules is a foot-gun. |

### 3.5 Hosted and IDE agents

The non-terminal cohort is not irrelevant to a terminal product; it shows where
the review surface is going.

- **Devin** sells an environment and a handoff, not a conversation: a cloud VM
  with shell/editor/browser, long-running sessions, playbooks, Slack/Linear/Jira
  triggers, output as draft PRs. Lesson: **sell the environment and the
  handoff; review work as a PR, not a transcript.**
- **Cursor (GUI)** adds Projects to coordinate parallel agents and review diffs
  in one place. Its checkpoints restore files but not messages, so the
  transcript can describe edits that no longer exist. Lesson: **a checkpoint
  that does not restore the conversation is half a checkpoint.**
- **Windsurf** has named checkpoints that cannot actually be reverted. Lesson:
  **naming a restore point is not making it reversible.** It runs simultaneous
  cascades in separate worktrees; worktrees are the right primitive for
  parallel agents, but the merge story is missing.
- **Replit Agent** puts an editable plan before code, checkpoints, background
  tasks, Design Canvas and one-click publish in the same loop. Lesson: **the
  plan should be an editable artifact, and effort should be a visible tier.**
- **Lovable** makes the plan a contract that must be approved before Build;
  connectors require per-connection approval. Lesson: **approval belongs at the
  connector boundary, where data leaves.**
- **Bolt.new** treats the live preview as the source of truth, translates
  visual edits back into source, and versions every edit. Lesson: **let users
  manipulate the artifact directly and translate that into code.**
- **v0** has Ask/Auto/Full modes, a sandbox, browser screenshots, Design mode
  with diffable versions, MCP, previews and PRs. Lesson: **one user-facing
  autonomy dial beats a page of toggles.**

**The hosted lesson in one sentence:** the winning surface is a governed
environment with a plan, a preview, a checkpoint and a review handoff — not a
chat window that happens to write files.

---

## 4. Architecture comparison

| Dimension | Claude Code | Codex CLI | OpenCode | Tamias |
|---|---|---|---|---|
| **Process model** | Single CLI, internal session | Core daemon + TUI/exec/IDE clients over JSON-RPC | One local server + thin clients (TUI, mini, run, web, ACP) | Single process |
| **State model** | JSONL transcript + checkpoints | Append-only JSONL + typed event stream | Event-sourced log + projections, strict replay | Module globals + in-memory history |
| **Turn loop** | Model → tool gate → tool → repeat | Typed events; pending steers drained at tool boundaries | Session runner; durable inbox | Sequential loop; no steering |
| **Tool execution** | Parallel independent calls; permission gate per call | Typed tool calls; approval objects | Tool registry; ordered permission rules | 18 tools, strictly serial |
| **Permission model** | Deny > ask > mode > sandbox > classifier > hooks | Sandbox axis + approval axis + execpolicy | Ordered rules, last match, any-deny | TOML allow/ask/deny + path/domain fence |
| **Sandbox** | Opt-in Seatbelt/bwrap, credential masking | Seatbelt/bwrap/seccomp/MXC, network proxy | None | None; substring shell rules |
| **Persistence** | JSONL, resume/fork/rewind | JSONL, resume/fork/apply | Event log, resume/fork/undo/redo | None |
| **Extension** | MCP, hooks, skills, plugins, subagents | MCP, skills, hooks, subagents, plugins | MCP, plugins, agents, commands, skills | None |
| **Headless** | `-p` JSON/stream-JSON, SDK | `exec --json`, JSONL schema | `run --format json`, `api`, ACP | Prose only |
| **Model routing** | Aliases, effort, fast mode, provider auth | Providers, profiles, reasoning effort | 230 providers, variants, small-model tasks | Catalog, tiers, rotation, escalation |
| **Cost** | List-price estimate; plan bars | Rate-limit card; thread credits | Provider costs; stats | Provider-billed + unpriced; hypothetical premium label |
| **Scale** | 827 prompt fragments | 164 crates, 2.17M lines | 35 packages, 50 migrations | 4.2k-line agent + 7k-line TUI |

**What this table says.** Tamias's architecture is closest to Aider (one
process, one model, no server), but its product ambition is closer to Codex
(governed, auditable, multi-surface). That mismatch is the core design debt.
You do not need 164 crates to fix it. You need one durable session store, one
event vocabulary and one transport boundary — three modules, not a rewrite.

---

## 5. Tamias scorecard (judgment)

Scores are 0–5, where 5 is best-in-class in this survey. They are a product
judgment, not a benchmark.

| Dimension | Tamias | Best in class | Why |
|---|---:|---|---|
| Governance / policy | **5.0** | Tamias | Project-bound, signed in managed mode; domain + tool + path + shell + model; deny is terminal; fail-closed ask. |
| Cost honesty | **5.0** | Tamias | Provider-billed, `None` for missing, unpriced steps, hypothetical premium label. |
| Model routing | **4.0** | OpenCode | Catalog, tiers, rotation, escalation, free/paid gate; missing variants/failover. |
| Testing | **4.0** | Codex | 301 tests, boundary probes, demo gate; missing TUI golden frames and live e2e. |
| Permissions UX | **2.5** | Codex / Cursor | Policy is strong, but interactive persistence, prefix/host rules and consequence-bearing options are missing. |
| Context / compaction | **3.0** | Codex / OpenCode | Compaction exists; no meter, no structured headings, no cache-aware budget. |
| TUI craft | **2.5** | Crush / OpenCode | Clean but sparse; hidden nav mode, no palette, no tabs, no diff. |
| Plan / act | **2.0** | Cline / Copilot | A plan tool, not a mode; policy used to deny it. |
| Streaming / cancel | **0.5** | all | Whole reply at end; Ctrl+C quits. |
| Sessions / resume | **0.0** | OpenCode | Nothing survives the process. |
| Undo / checkpoints / diff | **0.5** | Cline / Gemini | First-match string replace, no preview, no rollback. |
| MCP / extension | **0.0** | Codex / Goose | No client, no plugins, no hooks, no skills. |
| Project rules | **0.0** | Codex / Claude | `AGENTS.md` is not read. |
| Headless / CI | **1.5** | Codex | Prose only; exit code conflates refusal, error, cap and ceiling. |
| Sandbox | **1.0** | Codex | No OS containment; shell rules are substring heuristics. |
| Packaging / onboarding | **2.5** | Claude Code | Installable wheel with bundled catalog and policy; no first-run flow or update channel. |

**Aggregate:** governance 10/10, product surface ~3/10. That is the whole
problem in one line.

---

## 6. Keep / cut / add

### 6.1 Keep — do not trade these away

| Keep | Why it is a moat | Evidence |
|---|---|---|
| **Policy file as the product boundary** | Deterministic, offline, evaluated before any model call; tool/path/shell/domain/model in one reviewable TOML. Competitors express this as modes or per-tool prompts, not a deployment artifact. | `agent.py:2335-2455`, `docs/BOUNDED-AGENT.md` |
| **Deny-is-terminal + fail-closed ask** | A refusal ends the turn instead of becoming model feedback to route around. No human → deny. This is the right posture for supervised work. | `agent.py:1079-1083,2397,2522,3830-3838` |
| **Honest cost ledger** | Missing provider cost is `None`, not `$0`; unpriced steps are counted; UI can say "unknown". Compaction is billed into the same tally. | `agent.py:2947-2965,3317-3360`; `tui/credits.py` |
| **Investigation-before-build gate** | No competitor blocks a write on "you have not investigated". The implementation is weak (keyword scan), but the *contract* is a real differentiator. | `agent.py:1877-1885` |
| **Boundary refusal vocabulary** | `refused` is a first-class outcome in the loop, CLI and task board; a blocked task never reads 100%. | `agent.py:3838,3904-3913`; `tui/tasks.py` |
| **Model catalog + free/paid gate** | Catalog generated from the provider, 54 tool-capable models, real prices/context, no paid row promised unless enabled. | `models/catalog.json`, `model_catalog.py`, `providers.py` |
| **Offline brief + symbol index + bench harness** | The only honest path to a "cheaper per success" claim: a pre-registered gate, not a result. | `brief.py`, `context_index.py`, `bench.py` |
| **Small, auditable Python core** | A reviewer can read the loop and the policy engine in an afternoon. That is a feature for a governance product. | `agent.py` |

### 6.2 Cut — remove or demote

| Cut / demote | Why | What to do instead |
|---|---|---|
| **"Savings" language and the `spent × 0.5` estimate** | It was fabricated. A free model does not retroactively save half of past spend. This is exactly the honesty failure the project says it will not make. | Use "premium-equivalent (hypothetical retail)" and "retail delta"; show per-model actual spend. **Done this round.** |
| **Fake in-flight progress** | +9% per tool call capped at 95%, and any reply = 100%, is theatre. | Show step/tool counts while active; 100% only after human confirmation. **Done this round.** |
| **Demo-only tools in the default tool surface** | `boundary_accuracy`, `model_performance_comparison`, `reasoning_chain` are demo instruments, not agent capabilities. They add prompt surface and confusion. | Move them behind a `demo` tool profile; keep the default surface small. |
| **Keyword-scan "investigation" as the method** | The gate is good; the evidence is thin. A grep with headers will not survive a faculty or customer review. | Keep the gate, replace the method with AST/symbol/index evidence and a structured record (files, symbols, hypotheses, evidence IDs). |
| **`run_shell` substring deny list as security** | `"rm "` misses `rm\t`, `/bin/rm` and interpreter payloads; `shell=True` is not a boundary. | Demote to a convenience rule; add a real sandbox/container in P2 and say plainly when there is none. |
| **Hidden single-letter nav mode** | Discoverability is near zero; `t`, `c`, `m`, `h` only work when the composer is unfocused. | A command palette (`Ctrl+P`), visible footer hints, and a `?` help overlay. |
| **Credits framing** | "Credits" implies prepaid units Tamias does not sell; it invites the fake-savings narrative. | Call it "Cost" and "Session ledger". |
| **25-step hard stop that erases the turn** | Hitting a limit deletes the turn's history, so the work is lost. | Pause at the cap, keep history, ask to continue or raise the cap. |
| **Text-only headless with one exit code** | Automation cannot distinguish refusal, error, cap and ceiling. | `--output-format json` with typed terminal events and distinct exit codes. |

### 6.3 Add — the prioritized list

**P0 — truth and safety (this round, done):** see §8.

**P1 — table stakes, "credible agent" (2–3 weeks):**

| Add | Smallest useful implementation | Acceptance |
|---|---|---|
| **Streaming + cancellation** | `stream=True` in the OpenAI client; emit `message_delta`; `Esc`/`Ctrl+C` sets a cancel token checked between chunks and before each tool. | First token < 2s on a live model; cancel stops within 1s; partial text is preserved. |
| **Session store + resume** | One SQLite file (`~/.tamias/sessions.db`) with `sessions`, `messages`, `events`; `--continue`, `--resume`, `tamias sessions`, `--fork`. | Close and reopen the TUI; transcript and model restore; fork creates a new id. |
| **Checkpoints + diff + undo** | Snapshot touched files before each write into a content-addressed store; `git diff`-style preview in the ask modal; `/rewind` with files/chat/both. | Every edit is previewable; undo restores bytes; a checkpoint survives restart. |
| **Plan/act mode** | `--plan` + Shift+Tab; read-only tool subset; plan file is the only writable artifact; `Ctrl+G` opens it. | Plan mode cannot write outside the plan; switching to act requires confirmation. |
| **`AGENTS.md`** | Load root → cwd, `AGENTS.override.md` wins, 32 KiB cap; inject after the system prompt, not as configuration. | A repo rule changes behavior without editing `agent.py`. |
| **MCP client** | stdio + HTTP, `initialize`/`tools/list`/`tools/call`, per-tool approval, schema cache, `/mcp` status. | One real server (e.g. filesystem or GitHub) exposes a tool the model can call; denied tools never reach the model. |
| **Headless JSON** | `--output-format json|stream-json`; events `session.started`, `turn.started`, `tool.*`, `turn.completed{usage}`, `turn.failed`; distinct exit codes. | A shell script can parse a run and tell refusal from error from cap. |
| **429 retry + failover** | Honor `retry-after`; exponential backoff with jitter; after N failures, try the next catalog model in the same tier. | A 429 does not end the turn; the switch is visible in the transcript. |
| **Preserve history at limits** | Do not `del history[checkpoint:]`; append a `limit` event and keep the work. | Hitting the step cap leaves the transcript intact and offers continue. |
| **Tool results in the TUI** | Render the first N lines (expandable); keep a raw view. | A `read_file` card shows content, not just a glyph. |
| **Config file** | `tamias.toml` + `--config`; precedence packaged < user < project < flags; `/debug-config` prints the winner. | No behavior requires an env var; every setting has a provenance. |

**P2 — governed product (3–4 weeks):**

| Add | Why | Acceptance |
|---|---|---|
| **Policy DSL + persistence** | Move from TOML lists to typed rules (tool, resource, effect), last-match or deny-wins, with tests. Persist "always allow" per project/prefix/host, never overriding deny. | A user can approve `pytest` for the project once; a deny rule still wins. |
| **Approval data model** | `{id, kind, subject, options:[{id,label,scope,persist}], default}`; UI renders exactly those; batch reject. | No hard-coded Yes/No strings in the UI; approvals are auditable. |
| **Context meter + structured compaction** | Token estimate per consumer; `/context`; compaction headings `Objective/Requirements/Decisions/Work State/Next Move/Relevant Files/Important Context`; preserve user messages and constraints verbatim. | The meter matches provider usage within 10%; a compaction keeps the last 3 user messages verbatim. |
| **Hooks + skills + custom commands** | `PreToolUse`/`PostToolUse`/`SessionStart`/`UserPromptSubmit`; `SKILL.md` with YAML frontmatter; markdown commands. | A repo can add a formatter hook and a `/deploy` command without forking the agent. |
| **Sandbox (container-first)** | Ship a devcontainer/OCI profile with network off by default; optional bwrap on Linux. Do not claim native Seatbelt parity. | A shell command cannot read `~/.ssh` or reach the network unless the profile allows it. |
| **Audit join** | One event id links the tool decision, the model call and the billed usage; export JSONL. | Given a file change, you can find the model call, policy decision and cost. |
| **Cost-per-success** | Wire `bench.py` to the session ledger; publish a result only with n, model, task set and gate. | A claim has a reproducibility command and an n. |

**P3 — differentiators (4–6 weeks):**

| Add | Why | Acceptance |
|---|---|---|
| **Subagents** | Isolated context, parallel investigation; Claude/Codex treat it as baseline. | A subagent gets a scoped toolset and returns a summary, not a transcript. |
| **Shared server + tabs** | One process owns sessions; TUI/web/CI attach; tabs with attention. | Two clients see the same session; a permission request raises attention. |
| **LSP diagnostics** | Real compiler context beats grep; Crush proves the value. | After an edit, diagnostics appear in the next model step. |
| **PTY multiplexing** | Warp's lesson: agents need to drive interactive programs. | The agent can run a REPL and page a pager without wedging. |
| **Sanitized export/share** | Review and handoff; OpenCode's `--sanitize` replaces text/paths/tool output with redaction tokens. | Export a session with no secrets or absolute paths. |
| **ACP** | Editor integration without building an IDE. | Zed/Neovim can drive a Tamias session. |

**Do not build (now):** a daemon before there is a second client; 100+ feature
flags; a plugin marketplace; a Guardian-style model approving model calls; a
custom prompt language; a web app; a VS Code extension. Each is a distraction
from the governance wedge.

---

## 7. The minute details that separate a demo from a product

These are the behaviors that came up repeatedly across the cohort. They are
cheap individually and compound into "this feels real".

### Input and interruption

1. **Enter queues while busy; Ctrl+Enter sends now; ↑ takes the queued message
   back.** (Claude Code, Codex, OpenCode.) Tamias queues turns but cannot steer
   or take back.
2. **Esc interrupts the turn and keeps the queue**, not the app.
3. **Paste-burst detection** so a multiline paste is one input, not 40.
4. **Image paste** with per-model modality filtering.
5. **`!command`** runs a local shell command without the model (Codex).

### Approvals and safety

6. **Consequence-bearing labels**, not Yes/No: "Yes, just this once", "Yes,
   and don't ask again for commands that start with `pytest`", "No, and block
   this host in the future".
7. **Approval data is structured** (`available_decisions`), so the UI cannot
   invent an option the core will not honor.
8. **Persist approvals** at project/prefix/host scope; a saved allow never
   overrides a hard deny.
9. **Reject rejects every pending request** in the session (OpenCode), so a
   user can stop a batch.
10. **Read-before-edit**; `old_string` must be unique; `replace_all` is
    explicit; failure tells the model what to do next.
11. **Protected paths** enforced before the write: `.git` (including `gitdir:`
    targets), `.agents`, `.codex`, `.aws`, `.env`, the policy file itself.
12. **Trusted-folder gate** at load time: project config/hooks/exec policies
    from an untrusted folder stay disabled until confirmed.
13. **Say when there is no sandbox.** A permission prompt is not containment.
14. **Credential masking** at the network boundary; the model never sees the
    secret.

### Sessions, undo and review

15. **Append-only session log** with a `Compacted` record; resume is replay,
    fork is a prefix copy.
16. **Checkpoint per turn-starting prompt**, not per tool call; 100 is enough.
17. **Four restores**: files + chat, chat only, files only, summarize from
    here.
18. **Diff scopes**: branch, committed, working, **last turn**. "What did this
    turn change?" is the reviewer's real question.
19. **Per-file reviewed** state in the diff viewer.
20. **A checkpoint that cannot restore is a lie**; do not ship named
    checkpoints without a working restore.
21. **Sanitized export** with redaction tokens for text, paths and tool output.

### Plan and context

22. **Plan mode is read-only**; the plan file is the only writable artifact.
23. **The plan is editable in `$EDITOR`** and survives approval.
24. **A plan is a checklist cell**, not a blob of prose: `{step, status:
    pending|in_progress|completed}`.
25. **Compaction has fixed headings** and preserves user messages and security
    constraints verbatim.
26. **A context meter shows consumers**, not just a total: system, rules,
    tools, files, history.
27. **Deferred MCP schemas**: load tool schemas on demand, not all at startup.
28. **Model-specific prompt overlays** and a small-model title agent.

### Model and cost

29. **The picker shows tier, context, price and free/paid**, and never offers
    a row the run cannot use.
30. **A switch is visible** in the transcript with old/new tier and reason.
31. **Cost is provider-billed**; missing cost is "unknown", not zero.
32. **Hypothetical comparisons are labeled hypothetical** and are never called
    "saved".
33. **Per-model spend is a partition of the turn**, not a second total.
34. **Rate-limit card** with reset time and stale-data detection.
35. **Model failover** after retries, with the switch announced.

### TUI craft

36. **A command palette** makes 30–50 actions discoverable; hidden single-letter
    keys do not.
37. **Tabs with attention** (unread/error/permission) and a closed-tab stack.
38. **Tail-first transcript**: mount the newest rows, load older rows on demand.
39. **Typed history cells** with `compact()/display()/raw()`; `/raw` falls out.
40. **Theme from terminal colors** plus explicit themes; no hard-coded palette
    that fights the user's terminal.
41. **Notifications coalesce by priority**, are suppressed when focused, and
    self-disable after one failure.

### Headless and extension

42. **Stable JSONL event schema** for CI: `thread.started`, `turn.started`,
    `item.*`, `turn.completed{usage}`, `turn.failed`.
43. **Distinct exit codes** for refused, error, cap and ceiling.
44. **`exec --json` plus `--output-schema`** for structured results.
45. **MCP over stdio and HTTP**, with OAuth and per-tool approval.
46. **Recipes/runbooks** (Goose) or **skills** (Claude/Codex) as versioned,
    reviewable units of behavior.
47. **ACP** for editor integration.
48. **`/doctor`** for environment/auth/config diagnosis.

---

## 8. What changed in this round

The Tamias audit found defects that made the demo less honest than its
documentation. These are fixed and verified; the test count is now **301
passed**, and the offline gate is **13 passed, 0 failed, 1 skipped**.

| # | Defect | Before | Fix |
|---|---|---|---|
| 1 | Investigation tools were an unfenced read primitive | `investigate_target("/etc/hostname")` returned findings | `resolve_in_company_workspace` now falls back to `resolve_in_workspace` when no company is bound |
| 2 | `deny_read` failed open for absolute paths | Relative HR path denied; absolute form allowed | `_glob_any` normalizes literal, absolute and workspace-relative forms |
| 3 | Investigation tools skipped path rules | Not in `PATH_ARG`/`READ_TOOLS` | Added all four; followed imports in `trace_feature` now re-check workspace, secrets and policy |
| 4 | Shipped policy denied `update_plan` | Prompt mandated a plan; policy denied it; denial ended the turn | Added `update_plan` and `create_directory` to allow/ask |
| 5 | Headless `--task` ran with no policy | Writes ungated | Deployment policy now applies to every non-`--unbounded` run; bench/tests opt out explicitly |
| 6 | Explicit `--policy` did not bind its company | Company fence inert | `bind_policy_company` sets `COMPANY_ID`; a contradictory `--company-id` is an error |
| 7 | Fabricated "savings" | Manual switch invented `spent × 0.5`; header said "saved" | Removed the estimate; renamed to premium-equivalent (hypothetical retail); removed "saved" from cards/dashboard |
| 8 | Per-model spend table always empty | `turn_end` omitted `model`/`tier`; bridge dropped them | Central `_turn_end_fields`; per-model `account_usage`; bridge + ledger partition |
| 9 | Fake task progress | +9% per tool, 95% cap, any reply = 100% | Active shows step/tool counts; reply = "ready to review"; only human confirmation = 100% |
| 10 | Audit copied full file bodies | Write content duplicated into JSONL | Large free-text bodies replaced by length + SHA-256 prefix |
| 11 | Policy state leaked across `main()` calls | Tests saw a stale policy/company | `main` wrapper restores policy, company and protected paths on every exit |
| 12 | The package could not be installed | Invalid build backend, dangling `tamias.cli:main`, `Queue` annotation that only works on 3.14 | Valid backend; `tamias-agent = agent:main`; bundled catalog/policy; `queue.Queue`; `--version`; wheel built and entry point verified (a fully clean dependency install hit a PyPI timeout, not a build error) |

**What is not fixed yet** (the P1/P2 list above): streaming, cancellation,
sessions/resume, checkpoints/diff/undo, plan mode, `AGENTS.md`, MCP, headless
JSON, 429 retry/failover, history preservation at limits, tool results in the
TUI, config file, sandbox.

**Verification honesty:** the offline gate was re-run after these changes
(13 passed, 0 failed, 1 skipped). The live gate was attempted twice earlier and
both attempts hit free-tier 429s, so it reported **0/2, not claimed as proven**.
On 28 October 2026 it was re-run and **passed twice consecutively** (14 passed,
0 failed, 0 skipped): a real free model called a tool, and rotation moved the
turn onto a second model with a visible `lightning → ultra` switch card at
`$0.0000`. The 429 risk is still real; never present the mock run as live.

---

## 9. Roadmap and acceptance

### Phase 0 — stop the lies (done)

- Fence leaks closed; policy binds company; update_plan allowed.
- Cost language and task progress made honest; audit redacted.
- 301 tests; offline gate 13/13.

### Phase 1 — credible agent (2–3 weeks)

Order matters: streaming/cancel first (perceived quality), then sessions
(continuity), then checkpoints/diff (trust), then plan mode + `AGENTS.md`
(control), then MCP (extension), then JSON/retry/config (packaging is already
done).

**Exit criteria:**

- A live turn streams and can be cancelled without killing the app.
- Closing the TUI and running `--continue` restores the transcript and model.
- Every write shows a diff; `/rewind` restores bytes; a checkpoint survives a
  restart.
- Plan mode cannot write outside the plan file.
- `AGENTS.md` changes behavior in a fresh repo.
- One MCP server works end-to-end with per-tool approval.
- `--output-format json` is parseable and exit codes are distinct.
- A 429 is retried and, if needed, fails over visibly.
- `pip install .` in a clean venv gives a working `tamias-agent`. **Done this
  round.**

### Phase 2 — governed product (3–4 weeks)

- Policy DSL with tests; persisted approvals that never override deny.
- Approval data model; batch reject; prefix/host scopes.
- Context meter; structured compaction; skills/hooks.
- Container-first sandbox with network off by default.
- Audit join: decision + model call + billed usage.
- Cost-per-success with a reproducible harness.

**Exit criteria:**

- A user can approve `pytest` once for a project and see the rule.
- A deny rule still wins over a saved allow.
- `/context` matches provider usage within 10%.
- A container run cannot read `~/.ssh` or reach the network unless allowed.
- Given a file, `tamias audit` prints the decision, model call and cost.

### Phase 3 — differentiated (4–6 weeks)

- Subagents with scoped toolsets.
- Shared server + tabs/attention.
- LSP diagnostics.
- PTY multiplexing.
- Sanitized export/share.
- ACP.

**Exit criteria:** two clients share one session; a subagent cannot exceed its
scoped toolset; a sanitized export contains no secrets or absolute paths.

---

## 10. Decisions needed

These are the forks where the evidence does not make the choice for you.

1. **Product identity.** Is Tamias a *governed local agent* that companies
   install, or a *companion to the proxy* that demonstrates metering? The
   answer changes packaging, onboarding and roadmap.
   **Recommendation:** governed local agent; the proxy is the backend and the
   source of budgets.

2. **Sandbox strategy.** Build native bwrap/Seatbelt parity, or require a
   container/VM for untrusted work and say so?
   **Recommendation:** container-first. Native sandbox is a multi-quarter
   cross-platform project; a container profile is honest and shippable.
   Never call the substring shell rules a sandbox.

3. **Demo-only tools.** Keep `boundary_accuracy`,
   `model_performance_comparison` and `reasoning_chain` in the default tool
   surface?
   **Recommendation:** move them to a `demo` profile. The default agent should
   have the smallest tool surface that does the job.

4. **Packaging.** Publish a standalone `tamias-agent` package, or keep the demo
   as a checkout-only dependency?
   **Recommendation:** publish it. The wheel now builds, bundles
   `models/catalog.json` and the deployment policy, and exposes a real
   `tamias-agent` entry point; decide whether it belongs on PyPI or an internal
   index.

5. **UI ambition.** Polish Textual (palette, streaming, diffs, tabs) or rewrite
   on a web/React stack?
   **Recommendation:** keep Textual. The TUI is not the moat; the governance
   layer is. A rewrite would spend the next quarter on pixels instead of table
   stakes.

---

## 11. Evidence map

| Topic | File |
|---|---|
| Claude Code architecture, tools, UX, prompt patterns | `docs/research/01-claude-code.md` |
| Codex CLI runtime, TUI, sandbox, patterns | `docs/research/02-codex-cli.md` |
| OpenCode server, event log, TUI, permissions | `docs/research/03-opencode.md` |
| Gemini, Aider, Cline, Continue, Cursor, Goose, Crush, Amp, Warp, Copilot, hosted | `docs/research/04-wider-field.md` |
| Tamias capability inventory, gaps, rough edges | `docs/research/05-tamias-inventory.md` |
| Current policy and boundary behavior | `docs/BOUNDED-AGENT.md`, `policies/todoinc-todo.toml` |
| Current frontend contract | `docs/FRONTEND_REFERENCE.md` |
| Demo rehearsal | `demo/PRESENT.md`, `demo/check_all.sh` |

### What remains unverified

- No live competitor benchmark; no cost-per-success comparison against another
  agent.
- No decompilation of Claude Code's bundle; its loop is reconstructed from
  prompts and docs (marked inference where appropriate).
- No run of Cursor, Amp, Warp or Copilot (closed products); their claims are
  from docs.
- The live Tamias gate was rate-limited on the free tier in earlier attempts
  (0/2); it was re-run on 28 October 2026 and passed twice consecutively, with
  a real tool call and a visible model switch. The receipt and boundary card
  were verified offline; the live gate does not drive the TUI.
- A fully clean `pip install .` (downloading dependencies) was blocked by a
  PyPI timeout in this environment. The wheel itself built and installed, and
  the entry point, bundled catalog and bundled policy were verified.

---

## 12. The one-page answer

**Keep:** policy file, deny-is-terminal, fail-closed ask, honest cost ledger,
investigation gate, refusal vocabulary, model catalog, offline brief/index,
bench harness, small auditable core.

**Cut:** "savings" language, fake progress, demo tools in the default surface,
keyword-scan investigation as the method, substring shell rules as security,
hidden nav mode, "credits" framing, history-erasing limits, text-only headless.

**Add, in order:** streaming + cancel → sessions/resume → checkpoints/diff/undo
→ plan mode → `AGENTS.md` → MCP → headless JSON → retry/failover → config →
policy DSL + approvals → context meter + compaction → skills/hooks →
container sandbox → audit join → cost-per-success → subagents → server/tabs →
LSP/PTY/ACP.

**The sentence to remember:** *Governance is the moat; the table stakes are the
door. Build the door first, or no one will reach the moat.*
