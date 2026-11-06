# OpenAI Codex CLI — reverse-engineering report

**Binary:** `codex-cli 0.162.1` (`codex --version`, `/home/krish/.nvm/.../bin/codex`)
**Source:** `github.com/openai/codex` @ `2cab11ca40aad193382348a7bda46da2fc47596a` (2026-10-27, "Pin the Rust toolchain to 1.95.0 (#57373)"), shallow clone at `/tmp/opencode/codex-src`
**Docs:** `learn.chatgpt.com/docs/agent-approvals-security` (the repo's `docs/*.md` are now 3-line stubs pointing at the website)
**Method:** help output only; no model task was run.

---

## 1. Scale, and why it matters

| Metric | Value | Source |
|---|---|---|
| Rust workspace members | 164 | `codex-rs/Cargo.toml` `members` |
| `.rs` files under `codex-rs/` | 5,556 (~2.17M lines incl. tests) | `find`/`wc` |
| `tui/src` | 1,155 files, ~469k lines | same |
| `core/src` | 599 files, ~261k lines | same |
| Feature flags | 167 (`stable`/`experimental`/`under development`/`removed`) | `codex features list` |
| Slash commands | 65 variants | `tui/src/slash_command.rs:12-89` |

This is not a "CLI that calls an API" — it is a **local agent runtime**: daemon, JSON-RPC protocol, four front-ends (TUI, `exec`, desktop, IDE), MCP host, plugin host, policy engine and OS sandbox. Copy the *shapes*, not the mass.

---

## 2. Architecture

### 2.1 Process model: core is a server, the TUI is a client

`codex --help` exposes `app-server`, `app-server daemon`, `remote-control`, `--remote <ws://|unix://>`, `agents`, `queue`, `--no-daemon`. The TUI talks JSON-RPC to a **shared local app-server daemon** when one is running (`daemon_auto_start` is a `stable` feature set to true in `codex features list`), and falls back to an in-process runtime:

```rust
// codex-rs/tui/src/lib.rs:328
enum AppServerTarget { Embedded, LocalDaemon { endpoint, allow_embedded_fallback }, Remote { endpoint } }
```

Consequences visible in the binary: `codex agents` browses *all* sessions on the daemon, `codex queue --thread <id> --message <text>` injects a message into a **running** session from another terminal, and `--remote ws://host:port` runs the TUI against a server on another machine.

The wire protocol is JSON-RPC with generated TS bindings and JSON Schema (`codex app-server generate-ts|generate-json-schema`), method namespaces `thread/*`, `turn/*`, `initialize` (`codex-rs/app-server/README.md`).

### 2.2 Turn loop

`codex-rs/core/src/session/turn.rs:174 run_turn` → `loop { … }` (line 473):

1. Drain **pending input** (messages typed while the model was running) into history.
2. Run `UserPromptSubmit` hooks; persist recorded inputs to the rollout.
3. Capture a `StepContext` (settings, model info, environment, MCP servers required by *this* input).
4. `run_sampling_request` → stream from provider, execute tool calls, collect follow-ups.
5. If `needs_follow_up`, loop; else finish the turn and maybe compact.

The prompt is `sess.clone_history().await.for_prompt(&input_modalities)` — history is filtered per model at request time (images dropped for text-only models) rather than at write time.

### 2.3 Tool execution

A `ToolRouter` (`core/src/tools/router.rs:85`) plus a `ToolRegistry` of `RegisteredTool { spec, handler, exposure }`. Specs are assembled per turn by `core/src/tools/spec_plan.rs`, conditionally adding handlers from model capabilities, feature flags, environment and MCP state. Handlers live in `core/src/tools/handlers/`: `exec_command`, `write_stdin`, `apply_patch`, `update_plan`, `view_image`, `request_user_input`, `tool_search`, `list/read_mcp_resource`, `multi_agents*`, code-mode (`exec`/`wait`). `apply_patch` is its own tolerant patch format with a streaming parser (`codex-rs/apply-patch`), not JSON-escaped diffs. Tool **namespaces** are first-class (`multi_agent_v1`, `image_gen`), and `tool_search` keeps large MCP catalogs out of the prompt.

### 2.4 Config layering

`codex-rs/config/src/config_layer_source.rs:6-51` defines an explicit precedence ladder, and every value carries provenance (surfaced by `/debug-config`):

| Precedence | Layer |
|---|---|
| -10 / 0 / 10 / 15 | packaged defaults, MDM, system, enterprise cloud bundle |
| 20 / 21 | user `~/.codex/config.toml`, then profile `<name>.config.toml` |
| 25 | project `.codex/` |
| 30 | session flags (`-c k=v`, `--enable`) |
| 40 / 50 | legacy managed |

Profiles are *files*, not tables — diffable and shareable; `--strict-config` errors on unknown keys.

### 2.5 Persistence

Sessions are append-only JSONL rollouts named `rollout-<ts>-<uuid>.jsonl` under `~/.codex/sessions/YYYY/MM/DD/` (verified on disk), each line a `RolloutItem`: `SessionMeta`, `ResponseItem`, `Compacted`, `TurnContext`, `TokenUsageRecord`, `WorldState`, `EventMsg` (`codex-rs/history/src/lib.rs:215`). A `Recorder` writes asynchronously via mpsc (`rollout/src/recorder.rs`). Alongside: `state_5.sqlite`, `thread_history_1.sqlite`, `logs_2.sqlite`, `memories_1.sqlite`, `history.jsonl`, `shell_snapshots/`, `rules/`, `skills/`, `plugins/`. Resume is *replay*, not snapshot — which is why `fork`, `archive`, `delete` and `migrate-rollouts` are cheap.

### 2.6 Providers

`codex-rs/model-provider-info/src/lib.rs:734` ships six: `openai`, `amazon-bedrock`, `amazon-bedrock-runtime`, `gcp`, `ollama`, `lmstudio`, plus user `[model_providers.*]`. **`wire_api = "chat"` was removed** (`CHAT_WIRE_API_REMOVED_ERROR`, line 108) — custom providers must speak the Responses API.

### 2.7 MCP

`codex-rs/codex-mcp` is a full MCP *host*: stdio and streamable-HTTP transports, OAuth login (`codex mcp login`), `bearer_token_env_var`, `env_http_headers`, per-server `required`, `enabled`, `startup_readiness` (live vs cached catalog), `supports_parallel_tool_calls`. Tools are namespaced `mcp__<server>__<tool>` (seen in tests, e.g. `mcp__calendar__send`). Elicitation is a first-class TUI modal with its own approval category.

---

## 3. TUI / UX

### 3.1 Composition

There is no fixed grid. The chat view is a variable-height *inline* surface composed as a flex column: active transcript cells → pending-input preview → rate-limit hint → composer → footer (`tui/src/chatwidget/rendering.rs:129-230`). `App::render_chat_widget_frame` asks the widget for `desired_height(width)` and draws into that slot (`app.rs:1253`); `--no-alt-screen` keeps scrollback and `/tui` picks the mode for next launch. Cell layout is cached per `(cell_identity, revision, width, render_mode, syntax_theme_revision)` — a practical fix for reflow cost.

The event loop is one `tokio::select!` over `AppEvent`s, terminal input and timers (`app/startup.rs:1427`); widgets never touch `App`, they emit `AppEvent`s (`app_event.rs`). Redraws are coalesced by a `FrameRequester` capped at **120 fps** (`tui/frame_rate_limiter.rs`).

### 3.2 Composer

`bottom_pane/textarea.rs` is 4,725 lines: wrapping, paste-burst detection, image paste, history search, vim mode. `!cmd` runs a local shell command without the model (`Op::RunUserShellCommand`, `chatwidget/input_submission.rs:170`). `@` opens file search; `/` opens the command popup. Drafts survive Ctrl+C; Esc restores interrupted input.

### 3.3 Transcript vocabulary

Typed history cells, one per semantic object: `exec`, `patches`, `plans`, `approvals`, `mcp`, `mcp_result`, `search`, `hook_cell`, `notices`, `session`, `activity_group`. Each supports `compact`, `display` and `raw` modes — so `/raw` is a re-render, not a re-fetch. Diffs use `diff_render::create_diff_summary_with_links` (clickable paths via OSC 8). Distinctive: **in-terminal Mermaid** (`codex-rs/mermaid`), a bounded subset (flowcharts, sequence, state, class, ER; ≤16 nodes/24 edges), plus Markdown tables/math/lists as Unicode, all default-on (`config/src/tui_rendering.rs`).

### 3.4 Status surfaces

- **Busy row** above the composer: animated header, elapsed clock, wrapped detail (≤3 lines), interrupt hint, hook activity, background-terminal summary (`status_indicator_widget.rs`).
- **Configurable status line** with ~29 items including `context-remaining`, `five-hour-limit`, `weekly-limit`, `thread-credits`, `estimated-thread-cost`, `pull-request-number`, `branch-changes` (`bottom_pane/status_line_setup.rs:167-216`).
- **Rate-limit card** with a 20-segment `█/░` bar, local-time reset labels and stale-data detection (`status/rate_limits.rs`).

### 3.5 Slash commands (65)

Grouped by intent, not alphabet (`slash_command.rs:13` — "DO NOT ALPHA-SORT! Enum order is presentation order"):

| Group | Commands |
|---|---|
| Session | `/new` `/resume` `/fork` `/rename` `/archive` `/delete` `/clear` `/compact` `/recap` `/export` `/copy` `/raw` |
| Model | `/model` `/presets` `/fast` `/reasoning` `/daybreak` |
| Safety | `/permissions` `/approve` `/setup-default-sandbox` |
| Context | `/init` `/mention` `/diff` `/status` `/usage` `/cd` `/pwd` `/skills` `/mcp` `/apps` `/plugins` `/hooks` `/memories` |
| UI | `/theme` `/statusline` `/title` `/keymap` `/vim` `/tui` `/pets` `/experimental` `/warnings` |
| Ops | `/ps` `/stop` `/daemon` `/feedback` `/rollout` `/logout` `/quit` |

`/import` ("import setup, this project, and recent chats from Claude Code") is a competitive land-grab; `/pets` renders an ambient terminal pet.

### 3.6 Keys, approvals, plan, queue

Keymap is **action-based with contexts** (`global`, `composer`, `vim_normal`, `pager`, `list`, `agents`, `approval`), supports two-stroke chords, and an empty list explicitly unbinds (`keymap/bindings.rs:400-457`, `config/src/tui_keymap.rs`).

The approval modal is **data-driven**: the server sends `available_decisions: Vec<ReviewDecision>` and the overlay renders exactly those (`protocol/src/approvals.rs:340-420`, `bottom_pane/approval_overlay.rs:850-900`). Labels are consequence-bearing: "Yes, just this once", "Yes, and don't ask again for commands that start with `cargo test`", "Yes, and allow this host in the future", "No, and block this host in the future".

Plan display is an `update_plan` tool with `{step, status: pending|in_progress|completed}` (`protocol/src/plan_tool.rs`) rendered as a styled checklist cell; plan *mode* is separate (proposed-plan streaming cell, `history_cell/plans.rs`).

Queueing: messages typed mid-turn become **pending steers** — delivered at the next tool/result boundary — or immediate on interrupt (`chatwidget/input_queue.rs`, `pending_input_preview.rs`). This is the best UX idea in the product.

Images: `-i/--image` at launch, clipboard paste mid-session, per-model modality filtering, image token budget. Notifications are coalesced by priority, suppressed when the terminal is focused, and self-disable after one failure (`chatwidget/notifications.rs`, `tui.rs:1028`). Onboarding: welcome → login (ChatGPT OAuth / API key / access token) → **folder trust** modal noting that config, hooks and exec policies from untrusted folders stay disabled (`onboarding/trust_directory.rs:63-72`).

### 3.7 Non-interactive surfaces

`codex exec` emits JSONL: `thread.started`, `turn.started`, `item.started|updated|completed`, `turn.completed` (token usage incl. `cached_input_tokens`, `reasoning_output_tokens`), `turn.failed`, `error` (`exec/src/exec_events.rs`). Plus `--output-schema`, `-o` last-message file, `--ephemeral`, `--skip-git-repo-check`, `--ignore-user-config`, `--ignore-rules`, `--json`. `codex apply <TASK_ID>` shells out to `git apply` for the last recorded diff (`git-utils/src/apply.rs`) with a `--check` preflight.

---

## 4. Safety model

Two orthogonal axes (`protocol/src/protocol.rs:1137`, `:1216`):

**Sandbox:** `read-only` | `workspace-write` | `danger-full-access` (+ internal `external-sandbox`). `workspace-write` carries `writable_roots`, `network_access`, `exclude_tmpdir_env_var`, `exclude_slash_tmp`.

**Approval:** `on-request` (default) | `never` | `granular{sandbox_approval, rules, skill_approval, request_permissions, mcp_elicitations}` | internal `untrusted`. The public `untrusted` policy is **retired** per docs — you now express it as `[projects."/path"] trust_level = "untrusted"`.

| Intent | Invocation |
|---|---|
| Auto | `--sandbox workspace-write -a on-request` |
| Read-only browse | `--sandbox read-only -a on-request` |
| CI | `--sandbox read-only -a never` |
| Auto-review | `-c approvals_reviewer=auto_review` |
| YOLO | `--dangerously-bypass-approvals-and-sandbox` |

Enforcement is per-OS: **macOS** Seatbelt via `sandbox-exec -p` with composable SBPL files (`sandboxing/src/seatbelt_*.sbpl`); **Linux** bundled `bwrap` + `seccomp` + `no_new_privs` (digest-verified binary, exit code 8 on mismatch) with a legacy Landlock path (`linux-sandbox/src/lib.rs`); **Windows** MXC.

**Protected paths inside writable roots** are recursive and explicit: `.git` (including `gitdir:` pointer targets), `.agents`, `.codex`, `.aws` (`protocol/src/permissions.rs:38-52`, docs). The cheapest high-value control in the design.

**Network:** off by default; when on, optional `network_proxy` with allowlist-first rules (`*.example.com` ≠ apex, `**.example.com` = apex+subdomains, `deny` always wins), `allow_local_binding=false`, and a DNS-rebinding check that **fails closed**. Credentials can be injected at the proxy so the model never sees them (`core/tests/suite/scenarios_credential_masking.rs`).

**Execpolicy:** Starlark `prefix_rule(pattern, decision="allow"|"prompt"|"forbidden", justification, match, not_match)` plus `host_executable(name, paths)` to pin which binary a basename may resolve to. `match`/`not_match` are **load-time unit tests** (`codex-rs/execpolicy/README.md`). Commands split at pipes/`&&`/`;`/`$( )` and each segment is evaluated; redirections, substitutions, env assignments and globs are *not* matched, by design.

**Escalation** is prompt-engineering, not API: the model must set `sandbox_permissions="require_escalated"` + a `justification` question + optional `prefix_rule` (`prompts/templates/permissions/approval_policy/on_request.md`), which also bans broad prefixes (`["python3"]`), prefixes for `rm`, and heredoc prefixes.

**Guardian / auto-review** routes approvals to a reviewer model with `low|medium|high|critical` risk; critical denied, high requires authorization, and it **fails closed** on prompt/parse errors (`protocol/src/approvals.rs:88-130`, `core/src/guardian/`).

**Secrets:** keyring store plus `redact_secrets`. But `shell_environment_policy.ignore_default_excludes` defaults to **true** — the `*KEY*|*SECRET*|*TOKEN*` filter is off unless configured (`config/src/shell_environment_policy.rs:136`). Inference: sandboxed commands inherit the full parent environment by default.

**Project trust** gates project config, hooks and exec policies at load time, before any model call.

---

## 5. Feature inventory

| Feature | State | Evidence |
|---|---|---|
| `AGENTS.md` chain root→cwd, `AGENTS.override.md` wins, 32 KiB cap, `project_doc_fallback_filenames` | stable | `core/src/agents_md.rs`, `config_toml.rs:77` |
| Skills: `SKILL.md` + YAML frontmatter, explicit `$skill` and implicit invocation, dependency checks | stable | `codex-rs/skills/`, `features`: `skill_search` |
| Hooks: 14 events incl. `PreToolUse`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`, `PreCompact`, `SubagentStart/Stop`, `Stop`, `Interrupt` — Claude-Code-compatible names | stable | `hooks/src/lib.rs:HOOK_EVENT_NAMES` |
| MCP host (stdio/HTTP, OAuth, elicitation, per-tool approval) | stable | `codex-rs/codex-mcp`, `codex mcp --help` |
| Sub-agents: `spawn_agent`, `send_input`, `wait_agent`, `close_agent`; v2 adds `followup_task`, `interrupt_agent`, `list_agents`; depth limit; per-agent model override | stable, v2 off | `core/src/tools/handlers/multi_agents_spec.rs` |
| Compaction: local summarization, remote variants, pre/post-turn thresholds, image budget | stable | `core/src/compact.rs`, `prompts/templates/compact/*.md` |
| Goals (`/goal` persistent objective), Memories, Recap, plugins/marketplace | stable/experimental | `features list`, `slash_command.rs` |
| OTel telemetry (prompts redacted by default), self-update, Cloud tasks | opt-in / stable / experimental | docs §Monitoring, `codex --help` |

Compaction prompt in full (`prompts/templates/compact/prompt.md`) is four bullets: progress/decisions, constraints and preferences, next steps, critical data — injected behind a fixed "another language model started to solve this problem…" prefix.

---

## 6. Better than a typical homegrown agent

1. **Isolation is real** — OS sandbox, not a permission prompt pretending to be one, and testable in isolation (`codex sandbox linux <cmd>`).
2. **Approvals are structured data** with consequence-bearing options, session/prefix/host persistence and a transcript audit trail.
3. **Policy is code** — Starlark `prefix_rule` with self-testing `match`/`not_match`.
4. **The turn loop separates `pending_input` from turn input**, so steering and queueing fall out instead of being bolted on.
5. **Everything is a typed event**; one `EventMsg` stream drives TUI, JSONL, app-server, IDE, desktop.
6. **Resume/fork are free** because history is append-only JSONL with explicit compaction checkpoints.
7. **Prompt fragments per policy** (`permissions/approval_policy/*.md`, `sandbox_mode/*.md`) — small reviewable files, no prompt spaghetti.

## 7. Weak / controversial

- **Enormous.** 164 crates, 2.17M lines; compile-time and maintenance cost visible in toolchain pinning and parallel Bazel files.
- **Responses-API lock-in**: `wire_api="chat"` removed, so custom providers need a shim.
- **Feature-flag sprawl**: 167 flags; `removed` ones still listed; `/experimental` holds `pets`, `daybreak`, `code_mode`.
- **Default env passthrough** — `*KEY*/*TOKEN*/*SECRET*` filtering is off unless configured, so credentials reach sandboxed commands.
- **Prompt text left the repo**: base instructions come from server-delivered `ModelInfo.instructions_template` (`prompts/src/model_instructions.rs`); behavior is not fully auditable from source.
- **Guardian adds model calls to approve model calls** — probabilistic, not enforcement.
- Session JSONL grows unbounded; compaction fixes context, not disk.

---

## 8. Patterns Tamias can copy at small scale

1. **Event bus, not callbacks.** One `AppEvent` enum + one `asyncio.Queue` + one loop; widgets emit intents, the loop owns state. Kills most TUI race bugs for ~100 lines.
2. **Variable-height inline viewport.** Ask each cell for `desired_height(width)`, render into that slot, keep scrollback; cache layout per `(cell_id, revision, width)`.
3. **Typed history cells** — `ExecCell`, `PatchCell`, `PlanCell`, `ApprovalCell`, `NoticeCell` — each with `compact()/display()/raw()`; `/raw` becomes free.
4. **Server/core split over a local socket.** Even single-process: `tamias serve` + client buys `queue`, `agents`, `--remote`, multi-window for the cost of a small JSONL protocol.
5. **Approval as a data structure** `{id, kind, subject, options:[{id,label,scope,persist}], default}`; core proposes, UI renders, approvals persist to a prefix/host rules file.
6. **Pending-steer queue**: drain at tool boundaries, interrupt sends immediately, preview row above the composer.
7. **Protected-path list** (`.git`, `.codex`, `.agents`, `.aws` + symlink targets) enforced *before* the write, recursively — ten lines, kills a class of self-modification attacks.
8. **Escalation contract in the tool schema** (`sandbox_permissions`, `justification`, `prefix_rule`) plus a banned-prefix list, so the UI has something concrete to show.
9. **Policy file with tests** (prefixes + `match`/`not_match`, validated at load). YAML/TOML suffices; no Starlark needed.
10. **Layered config with provenance** (`packaged < user < profile < project < flags`) and a `/debug-config` command that prints the winner.
11. **Compaction as a 4-bullet versioned template file** behind a fixed preamble.
12. **Append-only JSONL sessions** at `sessions/YYYY/MM/DD/<uuid>.jsonl` with a `Compacted` record — resume = replay, fork = copy prefix.
13. **Status line as user-selected typed items**, each with a one-line description.
14. **Feature registry with stages** (`stable|experimental|dev|removed`) + `tamias features list` + `--enable/--disable`.
15. **`exec --json` with a tiny stable schema**: `thread.started`, `turn.started`, `item.*`, `turn.completed{usage}` — the enabler for CI and third-party UIs.

Not worth copying at small scale: daemon + remote control, MCP OAuth/elicitation, plugins/marketplace, Guardian, code-mode, sub-agents, Mermaid, pets.

---

## 9. Copy / avoid for Tamias

**Copy (in this order):** typed event bus + inline variable-height viewport → typed history cells with compact/display/raw → protected-path enforcement and a real sandbox boundary → data-driven approval options with prefix/host persistence → pending-steer queue → layered config with provenance → append-only JSONL sessions with compaction checkpoints → `exec --json` schema → policy file with self-tests → per-policy prompt fragments → configurable status line → feature registry with stages.

**Avoid:** the 164-crate decomposition; a daemon before there is a second client; 167 feature flags; model-proposed escalations without a banned-prefix list; a server-only system prompt; product surface area ahead of loop quality; Guardian-style model calls as a substitute for enforcement; default env passthrough of `*KEY*/*TOKEN*/*SECRET*`.

**The one-sentence lesson:** Codex's advantage is not the model — it is that *every* state transition is a typed event, *every* permission is a structured object, and *every* destructive action passes through a list of paths it may not touch.
