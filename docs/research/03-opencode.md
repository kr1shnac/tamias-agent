# OpenCode v2 — reverse-engineering report

**Binary:** `opencode v2.0.32` (installed CLI)
**Source:** `github.com/sst/opencode` @ `843a6c5` (2026-10-16, “release: v2.0.32”), checkout at `/tmp/opencode/opencode-2032`
**Docs:** `opencode.ai/v2/docs/*` (V2). `opencode.ai/docs/*` is V1 and was not used.
**Method:** CLI help and source only; no model task was run. Citations are from the v2.0.32 tree.

---

## 1. Scale

| Metric | Value | Source |
|---|---|---|
| Packages | 35 | `packages/` |
| TS/TSX files under `src` | 3,657 | `find` |
| Test files | 244 | `find` |
| `core/src` | 426 files, 68,259 lines | `find`/`wc` |
| `tui/src` | 284 files, 62,946 lines | same |
| `ai/src` | 218 files, 31,715 lines | same |
| `cli/src` | 116 files, 12,968 lines | same |
| `server/src` | 53 files, 4,139 lines | same |
| OpenAPI paths | 119 | `packages/protocol/openapi.json` |
| TUI actions / themes | 241 / 33 + `system` | `packages/tui/src/config/keybind.ts`, `theme/assets` |

This is a product, not a chat wrapper: it ships a server, provider layer, plugin host, SDK, and web/desktop surfaces, with most code spent on session durability and client coordination rather than prompting.

---

## 2. Architecture

### 2.1 One server, many clients

The CLI discovers or starts **one shared background server per user**. Discovery uses a registration file in the state directory containing URL, PID, version, and a private password, mode `0600` (`packages/client/src/effect/service.ts:15-20`). All local clients connect to it; the server owns sessions, configuration, permissions, and tool execution. `--standalone` starts a private child, `--server` attaches to a URL, and `opencode service set disabled true` disables the shared model.

Version skew is handled explicitly: discovery probes health and refuses a mismatched version; `ensure` can replace it and spawn “contenders” until a compatible server appears (`service.ts:22-105`). `opencode pair` issues one-time links with a **5-minute TTL** (`packages/server/src/pairing.ts:7`); session tokens last 30 days and are HMAC-derived from the server password (`packages/server/src/auth.ts:15,42`). This is a real local-service design.

Clients: TUI, `mini`, `run`, ACP, `api`, web/desktop; `serve` exposes the v2 API and web server.

### 2.2 Event-sourced sessions

SQLite runs in WAL mode with `synchronous=NORMAL`, a 5-second busy timeout, and a 64 MB cache (`packages/core/src/database/database.ts:38-46`). The DB is forced to `0600`; there are **50** versioned migrations.

Durable events live in `event` with a per-aggregate `event_sequence`; a projector folds them into `session_v2`, `session_message`, `session_pending`, `session_inbox`, and instruction tables (`packages/core/src/session/sql.ts:22,79,100,125,147`; `packages/core/src/event/sql.ts:4`). Replay is strict: owner mismatch or sequence divergence is a defect, not a silent overwrite (`packages/core/src/bus.ts:320-370`). Durable and ephemeral events share the same typed bus.

This buys replay, audit, multiple projections, and cheap forks. A fork records a boundary (`before`/`through` a message) and copies only **settled** history; terminal events for running assistant, shell, or compaction messages stay on the parent (`packages/core/src/session/projector.ts:126-168,202`). Undo/revert uses filesystem snapshots plus a revert record (`packages/core/src/session/revert.ts:31-67`).

### 2.3 HTTP + SSE with backpressure

Clients use HTTP and subscribe to `/api/event` over SSE. Each subscriber gets a **4,096-frame dropping queue**; when full, the subscriber is removed and failed rather than blocking the bus (`packages/server/src/event-feed.ts:8,74-80`). A hung TUI loses its stream, not the session.

The cost is a daemon, migrations, version negotiation, and 119 API paths; the benefit is that every client sees the same session and event log.

---

## 3. TUI / UX

### 3.1 Composition

The full-screen TUI is **OpenTUI + SolidJS**, not a Go/Bubble Tea stack (`packages/tui/package.json:61-70`). It has 241 bindable actions, a `ctrl+x` leader, a `ctrl+p` palette, and a which-key panel with paging and pending-preview modes (`packages/tui/src/config/keybind.ts:41,45-80,290-300`). Bindings can be strings, arrays, or objects with `preventDefault`/`fallthrough`; `"none"` or `false` unbinds.

The best UX is **session tabs plus attention**. Ten tabs are directly selectable, nine quick slots exist, and a closed-tab stack retains 25 entries (`keybind.ts:113-161`; `packages/tui/src/context/session-tabs-model.ts:62,70,119`). Tabs carry unread/error state, pulse animations, and an attention flag for permission or question requests; the session list sorts attention first (`packages/tui/src/component/session-tabs.tsx:103-125`; `dialog-open.tsx:159-207`). Notifications and per-event sounds are configurable.

The transcript is **tail-first**: only the newest rows mount initially, older rows mount near the top on demand, and inactive tabs stay cheap (`packages/tui/src/routes/session/index.tsx:413-420`). A practical fix for long-session slowdown.

### 3.2 Session surface

The session route supports message navigation, a timeline (`<leader>g`), fork from a message, undo (`<leader>u`), redo (`<leader>r`), compaction (`<leader>c`), and Markdown/JSON transcript export (`keybind.ts:121-134,193-194`; `routes/session/index.tsx:1209-1235`). Footers show agent, model, duration, and tokens per second. `/btw` answers a side question without derailing the main turn.

### 3.3 Diff and terminal

The diff viewer has **branch**, **committed**, **working**, and **last turn** scopes; split or unified layout; file tree or flat list; wrap; hunk navigation; and per-file “reviewed” (`packages/tui/src/feature-plugins/system/diff-viewer.tsx:81-84,688-690`). “Last turn” diffs from the previous idle marker to the next using snapshots, so steered prompts in the same busy period belong to the same turn (`packages/core/src/session/diff.ts:25-36`). This is the best product idea in the TUI after tabs.

There is an embedded terminal pane (`<leader>t`), terminal tabs, external-editor handoff (`<leader>e`), and editor-context discovery. Themes are JSON; 33 ship, plus `system` derived from terminal colors.

### 3.4 Mini

`opencode mini` is a separate client, not a mode. It uses a **split-footer** layout: immutable append-only scrollback for the transcript, and a repaintable footer for prompt, status, permissions, and forms (`packages/tui/src/mini/types.ts:1-14`; `mini/footer.ts:3-8`). It is the right shape for SSH and tmux, and shares the server and event model.

### 3.5 Assessment

The TUI is the moat: tabs for parallel work, attention as state, a palette for discoverability, and a diff view that models how reviewers think. The risk is maximalism; 241 actions are hard to learn and keep coherent.

---

## 4. Configuration and agents

### 4.1 Two planes

`opencode.json(c)` controls the server/project: model, agents, permissions, providers, MCP, plugins, skills, instructions, references, worktrees, formatters, LSP entries. `~/.config/opencode/cli.json` controls terminal clients only: theme, keybinds, tabs, diffs, attention, mini, editor, debug. No project-local CLI file; inline JSON via `OPENCODE_CLI_CONFIG_CONTENT`; writes atomic at `0600` (`packages/cli/src/config/config.ts:31-49`; `opencode.ai/v2/docs/cli/config`).

The split is right: agent behavior belongs with the repo; personal themes do not.

### 4.2 Precedence is surprising

Merge order is global user file → direct `opencode.json(c)` from farthest ancestor to current → `.opencode/opencode.json(c)` in the same order → system. Managed macOS preferences and Console policies outrank everything. Every `.opencode` file overrides every direct file, regardless of depth (`opencode.ai/v2/docs/config`; `packages/core/src/config/discovery.ts:61-140`).

Discovery walks **above the repository root to the filesystem root**, so a config in `/home/user` or `/` can affect a project. “System outranks project” is also the opposite of the usual “most local wins” instinct. Defensible for fleets; easy to misconfigure on a laptop. Substitution supports `{env:NAME}` and `{file:path}`; missing values become empty strings.

### 4.3 Agents and extensions

Built-ins are `build`, `plan`, `general`, `explore`; `compaction`, `title`, `summary` are hidden (`packages/core/src/plugin/agent.ts:80-145`). Agents have mode (`primary`, `subagent`, `all`), optional model, step limit, prompt, and permissions. Plan mode denies edits except under `~/.opencode/plan` (`packages/core/src/plugin/plan.ts:31-40`).

Extensions cover Markdown agents, commands, skills, MCP, server/TUI plugins, instructions, references, worktrees, and formatters. The plugin API is the one intentional breaking change from V1 alongside the server API (`packages/core/src/plugin/skill/opencode.md:144`).

---

## 5. Permissions and safety

### 5.1 The rule engine

Rules are ordered `{action, resource, effect}`. The **last match wins**; `*` crosses `/`, `?` matches one character, Windows matching is case-insensitive (`opencode.ai/v2/docs/permissions`; `packages/core/src/permission.ts:88-97`). For multi-resource operations, any `deny` denies, else any `ask` asks, else allow (`permission.ts:166-178`). No match falls back to `ask`.

Actions cover `read`, `edit` (also `write`/`patch`), `glob`, `grep`, `shell`, `subagent`, `skill`, `question`, `webfetch`, `websearch`, `external_directory`, MCP tools, and `execute` for Code Mode. `external_directory` is checked before reads/edits outside the location/worktree.

Approvals are data: once, always (save the tool’s proposed patterns for the project), or reject. Reject rejects **every pending permission request in the session**; feedback can be attached (`opencode.ai/v2/docs/permissions`; `permission.ts:289`). Saved approvals are project-scoped `allow` rules and never override `deny`. Policies hard-deny after rules and saved approvals, so an organization can block a command a repo allows.

### 5.2 Defaults are allow-all

Every agent, including custom ones, starts with:

```json
[
  { "action": "*", "resource": "*", "effect": "allow" },
  { "action": "read", "resource": "*.env", "effect": "ask" },
  { "action": "read", "resource": "*.env.*", "effect": "ask" },
  { "action": "read", "resource": "*.env.example", "effect": "allow" }
]
```

(`packages/schema/src/agent.ts:46-52`; `opencode.ai/v2/docs/permissions#defaults`)

Shell, edits, web access, subagents, and **external directories** are allowed without a prompt unless a rule is added. The only default protection is a filename heuristic: `.env.local` asks; a key in `config/secrets.json` does not.

### 5.3 No local sandbox

The docs say `shell` runs with “the host user’s filesystem, process, and network authority,” and directory inference is best effort. The Kimi system prompt states: “The operating environment is not in a sandbox. Any actions you do will immediately affect the user’s system” (`packages/core/src/plugin/system-prompt/kimi.txt:62`). There is no Seatbelt, bubblewrap, Landlock, or container boundary around local tool execution.

The shell scanner is tree-sitter by default, with an optional portable scanner; a command it cannot analyze produces a scanner error, not a denial (`opencode.ai/v2/docs/permissions#scanner`). `--auto` approves everything not explicitly denied; hidden `--yolo`/`--dangerously-skip-permissions` flags exist (`packages/cli/src/commands/commands.ts:39-46`).

### 5.4 Good, and not good

Good: the rule model is small and testable; approvals are structured; “allow always” is scoped and reviewable; plan mode is a real capability boundary; hard-deny policies survive a compromised project config; rejection is batch-safe.

Not good: **this is a UX layer, not a security boundary.** It depends on the model calling the right tool, the scanner recognizing the command, and the user reading the prompt. A shell command can still read `~/.ssh`, exfiltrate over the network, or delete the repo.

Two residue items show drift. Sharing was removed in V2 (`CHANGELOG.md:20`), but `session_v2.share_url` remains. LSP has config schema, TUI action labels, and OpenAPI remnants, but the runtime is absent — the code says “after LSP runtime exists” (`packages/core/src/file-mutation.ts:131`; `tool/plugin/write.ts:44`). **Inference:** LSP was deferred, not shipped; the schema is compatibility surface.

---

## 6. Models and providers

OpenCode bundles a **5.4 MiB models.dev snapshot** (5,687,565 bytes) with **230 providers and 8,894 models**, then refreshes from `https://models.opencode.ai` (`packages/core/src/models-dev.ts:280-285,362-434`). The cold-start catalog is offline-safe.

There are 32 registered provider plugins (`packages/core/src/plugin/provider.ts`), plus local discovery for Ollama, LM Studio, and vLLM. Model references use `provider/model#variant`; variants carry reasoning effort, budget tokens, or provider toggles. Provider/model settings can override transport, headers, body, and compaction mode.

Two smaller decisions are worth copying:

- **Model-specific prompts.** Kimi, GPT, Claude, Trinity, and Meta Muse get targeted prompt overlays (`packages/core/src/plugin/optimize.ts:19-40`).
- **Small-model titles.** The title agent prefers `gpt-luna`, `gemini-flash-lite`, `gemini-flash`, or `claude-haiku` from the same provider, with 8,000-character context, 2,000-character first message, and 100-character title (`packages/core/src/session/title.ts:22-24`; `session/context.ts:95-118`). Cheap and bounded.

Retries: 2s → 4s → 8s, then 10s per gap, 10 retries (about 84s nominal, 67–101s with jitter); `retry-after` honored up to 15 minutes; timeouts get at most 3 retries (`packages/core/src/session/runner/retry.ts:31-60`). The loop retries the same request. **Inference:** I found no cross-provider/model failover; a dead provider ends the step after the retry budget.

---

## 7. Sessions and product features

The inbox is the best “small” idea. A prompt submitted while the agent is busy has a delivery mode: **steer** (next step boundary) or **queue** (when idle). The inbox is durable and ordered; promotion is explicit: `promote("steer")` takes only steers, `promote("input")` takes one queued item at idle (`packages/core/src/session/inbox.ts:33-40`). A unique index allows one pending compaction per session (`session/sql.ts:115-122`). This enables mid-turn steering without a second ad-hoc queue.

Compaction is structured. The summary template is `Objective`, `Requirements`, `Decisions`, `Work State` (`Completed`/`Active`/`Blocked`), `Next Move`, `Relevant Files` (max 15), `Important Context` (`packages/core/src/session/compaction.ts:104-135`). It triggers at a context ceiling (default keep 15,000 tokens, 10% free buffer), on overflow, or manually; native provider compaction is supported per provider/model (`compaction.ts:197,213-233`). A malformed summary gets one reminder, then fails.

Export/import is JSON with optional `--sanitize`, replacing text, paths, shell output, skills, and tool content with `[redacted:kind:id]` (`packages/core/src/session/transfer.ts:57-62,180-277`). The TUI exports Markdown or JSON transcripts. `stats --json` reports sessions, models, tool reliability, cost, and tokens.

`opencode run --format json` streams typed records (`text`, `reasoning`, `step_start`, `step_finish`, `tool_use`, `error`) over stdout (`packages/cli/src/run/noninteractive.ts:101-134`). ACP and `opencode api` cover editor and HTTP clients.

---

## 8. Strengths and weaknesses

| Strong | Weak |
|---|---|
| Shared server with discovery and version gating | Daemon, migrations, 119 API paths |
| Event-sourced state with strict replay | Hard to evolve; 50 migrations |
| Durable steer/queue inbox | Two delivery modes need UI explanation |
| Tabs, attention, real diff review | 241 actions; maximalist |
| Two-plane config with managed policy | Surprising precedence; config above repo |
| Structured approvals, hard-deny policies | Allow-all defaults, no local sandbox |

The contradiction: permissions are presented as safety, but defaults are allow-all and the shell is unsandboxed. The feature is an audit trail and policy hook, not containment.

---

## 9. Copy / avoid for Tamias

**Copy, in this order:**

1. **Shared local server with thin clients.** One process owning sessions buys tabs, `run`, and a future web client. Registration file at `0600`, health probe, version refusal; skip “contenders” until needed.
2. **Event log plus projections, not a mutable transcript.** `events(aggregate_id, seq, type, data)` → `sessions`, `messages`, `inbox`. Strict replay; boundary-based forks. Highest-leverage architectural copy.
3. **Durable inbox with steer vs queue.** One table, one promotion rule, one compaction slot. Removes TUI races.
4. **Tabs + attention as first-class state.** Unread, permission, question, error; attention first; closed-tab stack. Five tabs and three slots deliver most value.
5. **Palette and which-key.** 241 actions are too many; a palette makes 30–50 discoverable.
6. **Diff viewer with “last turn.”** Branch/committed/working is table stakes; “what this turn changed” is the real question. Add per-file reviewed.
7. **Two configuration planes.** Agent/project config in the repo; terminal preferences in one global file.
8. **Ordered rules with last-match, batch deny, project-scoped saved approvals.** Keep the data model; change the defaults.
9. **Plan mode as an agent overlay with one writable directory.** Cheap, explainable, useful.
10. **Structured compaction with a fixed heading set.** Copy the headings, not the 900-line implementation; fail loudly.
11. **Bundled model catalog with background refresh.** A curated snapshot beats a cold network call.
12. **`run --format json` and sanitized export.** The surfaces that make the agent usable outside the TUI.

**Avoid:**

- **Allow-all defaults.** Start from deny/ask for shell, edit, and external dirs; show the base policy.
- **“Permissions” without a sandbox.** If Tamias runs shell, add an OS boundary or say plainly there is none.
- **The 35-package, Effect-TS-scale decomposition.** A Python agent needs a few modules and one SQLite file.
- **119 endpoints before a second client.** Ship session/message/event/permission first.
- **Config discovery above the repo root.** Stop at the repo or require an explicit flag.
- **Two delivery modes without UI affordances.** Show mode in the composer and preview delivery.
- **Schema/feature residue.** Don’t keep `share_url`, LSP labels, or deprecated flags without a real client.
- **No fallback or cost ceiling.** Retrying a dead provider for 84s is predictable but wasteful.

**The one-sentence lesson:** OpenCode’s real invention is treating a coding session as a durable, replayable event log behind one shared server — but its permission system is a UX layer, not a security boundary, and that is the line Tamias must not copy.
