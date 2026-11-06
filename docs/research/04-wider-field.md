# 04 — The wider field

**A terminal-first survey of coding agents, with hosted products as context.** 27 October 2026.

Tamias sells governance: a signed, project-bound policy, gateway metering, and an agent that cannot quietly exceed either. This note asks what ten terminal agents — and, briefly, seven hosted ones — assume about architecture and UX, and which capabilities are now table stakes. `[inference]` marks judgement. Sources are primary docs, read in October 2026; there were no hands-on trials and pricing was not audited. Baseline: Tamias has policy, spend and bench; it lacks MCP, checkpoints, resume, subagents, hooks, sandbox and plugins.

## Terminal and CLI agents

### 1. Gemini CLI — selective rewind, shipped off

**Architecture.** TypeScript monorepo: a React-Ink terminal UI over a separate `packages/core` agent library, with a local server sharing that core. Extensions, not plugins, are the unit of distribution.

**Standout UX.** `/rewind` picks any earlier message and reverts the conversation, the code, or both; checkpoints are shadow-git commits, so a revert is inspectable with git. `/restore` rebuilds code from the same store. The unit of undo is a message rather than a file, closer to an editor's undo stack than to a branch. Project context lives in `GEMINI.md`.

**What Tamias lacks.** Selective rewind; extensions bundling MCP servers, slash commands, themes, hooks, subagents and skills; lifecycle hooks; headless JSON output; trusted-folder sandboxing.

**Avoid.** Checkpointing ships disabled by default, and a conversation-only rewind leaves code and transcript disagreeing `[inference]`. The larger warning is the README: the CLI is replaced by Antigravity CLI for unpaid and Google One users (18 June 2026). A terminal surface can be withdrawn.

**Evidence.** [repo](https://github.com/google-gemini/gemini-cli) · [rewind](https://geminicli.com/docs/cli/rewind/) · [checkpointing](https://geminicli.com/docs/cli/checkpointing) · [extensions](https://geminicli.com/docs/extensions/)

### 2. Aider — the repo map and the auto-commit

**Architecture.** Python, one process, no server. A tree-sitter repo map ranks definitions by graph relevance and sends only the relevant slice; several edit formats trade reliability against token cost.

**Standout UX.** Every change is committed automatically with a generated message, and `/undo` reverses the last one. `--watch-files` lets the agent see editor buffers, and architect mode splits reasoning and editing across two models. `/add` and `/read` make context curation manual, which keeps token spend predictable. Because edits land as commits, `git log` becomes a crude audit trail — it records what changed, never what was refused.

**What Tamias lacks.** Repo-map context selection; auto-commit with `/undo`; multiple edit formats; the watch-files IDE bridge; architect two-model mode; auto-lint and auto-test loops.

**Avoid.** There is no approval gate before a write, and the configuration surface runs past a hundred flags. Aider is the clearest product of the pre-governance generation: fast, scriptable and indifferent to who approved what.

**Evidence.** [git and undo](https://aider.chat/docs/git.html) · [repo map](https://aider.chat/docs/repomap.html) · [edit formats](https://aider.chat/docs/more/edit-formats.html)

### 3. Cline — checkpoints with three restores

**Architecture.** One TypeScript agent core shared by the CLI (on OpenTUI), VS Code, JetBrains, a desktop app and an SDK. The CLI is a thin client over the same state, not a wrapper around the webview.

**Standout UX.** Shadow-git checkpoints offer three distinct restores: files only, task only, or both, and checkpoints are browsable per task rather than a single last-step undo. Plan and Act are separate modes, so investigation cannot silently become a write. A hub daemon (`--zen`) runs tasks in the background, and cron schedules and chat connectors let work start without a terminal.

**What Tamias lacks.** Checkpoints and their restore matrix; Plan/Act separation; a background daemon; scheduled and chat-triggered tasks; team subagents; an MCP marketplace.

**Avoid.** Four clients, an SDK and a marketplace create configuration drift, and the auto-approve toggles can quietly reproduce Aider's no-gate posture `[inference]`.

**Evidence.** [repo](https://github.com/cline/cline) · [CLI](https://github.com/cline/cline/blob/main/apps/cli/README.md) · [checkpoints](https://docs.cline.bot/features/checkpoints)

### 4. Continue — configuration is the product

**Architecture.** TypeScript; an Ink-based `cn` CLI plus VS Code and JetBrains extensions. Almost everything is declared in `config.yaml`: models and roles, rules, prompts, MCP servers, context providers and data destinations.

**Standout UX.** The same config produces the same agent in the terminal and the IDE. Context providers (`@docs`, `@files`) make retrieval explicit, and model roles assign different models to chat, edit, apply and autocomplete — a direct cost/quality dial. Rules live in the repo, so behaviour is reviewable. Config can also be pulled from a hub, letting an organisation publish one assistant definition.

**What Tamias lacks.** Declarative, portable configuration; named model roles; context providers; a shared hub for team assistants; autocomplete.

**Avoid.** The repository is archived and read-only, with 2.0.0 the final release. A good configuration model with no maintainer is a dependency trap: copy the idea, not the dependency.

**Evidence.** [repo](https://github.com/continuedev/continue) · [config reference](https://docs.continue.dev/reference)

### 5. Cursor CLI — permissions as a language

**Architecture.** A closed-source `agent` binary sharing Cursor's backend, with Agent, Plan and Ask modes and a cloud execution path.

**Standout UX.** Permissions are typed tokens — `Shell()`, `Read()`, `Write()`, `WebFetch()`, `Mcp()` — composed into allow and deny rules. `approvalMode` adds allowlist, auto-review and unrestricted presets, and a sandbox with a network toggle backs the rules. `/rewind` jumps to a previous message; `agent ls`, `resume` and `--continue` make sessions durable; `&` hands a task to a Cloud Agent. Plan can read and search without writing, and Ask stays conversational: the clearest three-mode split here.

**What Tamias lacks.** A typed permission DSL; session list and resume; cloud handoff; OS sandbox; plugins and marketplaces; LLM-assisted approval review.

**Avoid.** Unrestricted mode is one flag away, and the binary sits inside the governance path with no inspectable policy `[inference]`. The DSL is the most expressive permission surface here — and the one most worth copying.

**Evidence.** [overview](https://cursor.com/docs/cli/overview) · [permissions](https://cursor.com/docs/cli/reference/permissions) · [configuration](https://cursor.com/docs/cli/reference/configuration)

### 6. Goose — recipes and ACP

**Architecture.** Rust, split into interface, agent and extensions. Desktop, CLI and API share the agent, and extensions are MCP servers: the product is MCP-native rather than MCP-compatible.

**Standout UX.** Recipes are shareable YAML that fix a prompt, extensions and parameters; sub-recipes and deeplinks compose them, and a recipe is the closest thing here to a versioned runbook. Because extensions are scoped per recipe, the tool surface shrinks to the task — a useful precedent for policy. Sessions can be forked, edited and exported. `goose acp` exposes the agent over the Agent Client Protocol, so editors such as Zed can drive it, and cron schedules run recipes unattended.

**What Tamias lacks.** Recipes; scheduling; session fork and export; ACP client and server; an MCP extension catalog; extension allowlists.

**Avoid.** With seventy-plus extensions, install-time trust becomes the security boundary; an allowlist is not runtime per-call policy `[inference]`.

**Evidence.** [repo](https://github.com/block/goose) · [architecture](https://goose-docs.ai/docs/goose-architecture/) · [CLI](https://goose-docs.ai/docs/guides/goose-cli-commands)

### 7. Crush — TUI craft and LSP context

**Architecture.** Go on Bubble Tea v2, with SQLite-backed sessions. `crush serve` exposes a shared workspace — session list, history and a permission queue — to multiple clients at once.

**Standout UX.** The polish is the point: a genuinely fast, keyboard-first TUI. LSP diagnostics feed the model real compiler context. MCP over stdio, HTTP and SSE includes OAuth; there are skills, hooks, themes and desktop notifications. Sessions are rows, not scrollback, so `crush serve` can hand the same conversation to a second client. In `serve` mode, approvals become a shared inbox rather than a modal blocking one terminal. `crushrc` is executable Bash, and `--yolo` skips prompts.

**What Tamias lacks.** LSP context; a shared workspace server; a durable session store; MCP with OAuth; skills and hooks; desktop notifications.

**Avoid.** `crushrc` executes arbitrary Bash at startup. Configuration that executes is a supply-chain hole, however convenient `[inference]`.

**Evidence.** [repo](https://github.com/charmbracelet/crush) · [go.mod](https://raw.githubusercontent.com/charmbracelet/crush/main/go.mod)

### 8. Amp — threads as durable objects

**Architecture.** Closed source; a Bun/TypeScript CLI plus web and mobile. Every thread is a server-side object with a URL, and an Orb is a cloud machine attached to that thread.

**Standout UX.** Thread links can be shared, unlisted or workspace-visible; teammates can attach and continue the same thread from another client, so closing the laptop does not end the task. The Dial (low, medium, high, ultra) fixes a bundle of model, prompt and tools per thread, preventing mid-task model drift. Task and Read Thread subagents isolate work, and a TypeScript plugin API can register tools, modes and `amp.ai.decide` hooks. Orbs bill by the minute, so long runs have a visible meter.

**What Tamias lacks.** Durable thread URLs; multiplayer; cross-client attach; cloud Orbs; a plugin API; configurable effort bundles.

**Avoid.** The Dial hides which model is running and what a thread costs until the bill; credits, orb-minutes and BYOK stack into pricing that is hard to forecast `[inference]`.

**Evidence.** [docs](https://ampcode.com/docs) · [threads](https://ampcode.com/docs/threads) · [the Dial](https://ampcode.com/docs/the-dial) · [plugins](https://ampcode.com/docs/customize/plugins)

### 9. Warp Agent CLI — the PTY multiplexer

**Architecture.** A standalone CLI running the same Warp Agent harness as the desktop app, built around a native PTY multiplexer rather than a subprocess wrapper.

**Standout UX.** Agent and human share one terminal, so the agent can drive interactive programs — REPLs, pagers, prompts — while you watch; it can answer a password prompt or page through `git log`, tasks that break pipe-based tools. The transcript renders diffs, plans, task lists and thinking. `/handoff` snapshots uncommitted and untracked files to a cloud agent, which matters because most local work is untracked; `warp --resume` reattaches. A tab bar gives each child agent its own terminal rather than multiplexing every stream into one. Permission profiles, `AGENTS.md`/`WARP.md`, skills, MCP and a TOML statusline round it out.

**What Tamias lacks.** PTY multiplexing; cloud handoff with a working-tree snapshot; resume; child-agent orchestration; a statusline; permission profiles.

**Avoid.** Credits meter every agent action with no pre-flight estimate, and letting an agent drive a full-screen TUI can wedge the session `[inference]`.

**Evidence.** [CLI docs](https://docs.warp.dev/agents/cli/) · [agent CLI reference](https://docs.warp.dev/_llms-txt/warp-agent-cli.txt)

### 10. GitHub Copilot CLI — plan mode and assisted permissions

**Architecture.** Closed source; an npm umbrella package (`@github/copilot`) shipping platform binaries. It is GitHub-native in a way no competitor can copy.

**Standout UX.** Plan mode (Shift+Tab) is a first-class phase before execution, with ask/execute and autopilot beneath it. Assisted permissions use an LLM to triage tool calls, and a rejection can carry inline feedback — the right direction for approval fatigue, even if the classifier is another model to trust. `/sandbox enable` runs locally; `--cloud` runs remotely. `--allow-tool` and `--deny-tool='shell(rm)'` give scriptable rules, trusted directories fence the workspace, and auto-compaction with `/context` manages the window. `/resume` restores sessions; `/every` and `/after` schedule work; custom agents, hooks, skills and memory extend it.

**What Tamias lacks.** Plan mode; assisted permission triage; compaction and a context meter; custom agents, hooks and scheduling; default GitHub MCP and ACP servers.

**Avoid.** Premium-request metering is opaque, and autopilot combined with broad allow rules is a foot-gun `[inference]`.

**Evidence.** [about Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli) · [usage](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/overview)

## Hosted and IDE agents

### Devin

A cloud VM with shell, editor and browser, organised around long-running sessions rather than a chat pane. Playbooks encode recurring procedures; Slack, Teams, Linear and Jira start work; output arrives as draft pull requests. The CLI's `/handoff` moves a local task into the same environment, and sessions can run for hours because the VM persists and stays inspectable. Pricing is in ACUs, which makes cost legible per unit rather than per token, and work is reviewed as a pull request rather than as a transcript. **Lesson:** sell the environment and the handoff, not the conversation. [docs](https://docs.devin.ai/)

### Cursor (GUI)

Agent plus a Projects coordinator that dispatches parallel work and reviews diffs in one place. Checkpoints restore files but not messages, so the transcript can describe edits that no longer exist. Side chats, `/goal` and a browser tool fill gaps the CLI lacks, and Projects is the coordination layer: several agents, one review surface. The GUI's advantage is review bandwidth, not autonomy. **Lesson:** a checkpoint that does not restore the conversation is half a checkpoint. [docs](https://cursor.com/docs)

### Windsurf / Devin Desktop

Now under Cognition. Cascade has a planning agent and todo list, named checkpoints, memories and rules, and can run simultaneous cascades in separate worktrees, which avoids two agents editing one tree. Named checkpoints cannot actually be reverted, which makes the affordance misleading; memories persist across sessions. The gap between the affordance and its behaviour is the most instructive UX failure in this survey. Worktrees are the right primitive for parallel agents; the missing piece is a merge story. **Lesson:** naming a restore point is not making it reversible. [site](https://windsurf.com/)

### Replit Agent

Plan mode produces an editable task list before code. Checkpoints, one versus ten background tasks by plan, a Design Canvas and one-click publish make the whole loop browser-native. Effort tiers change how many agents run concurrently, and Design Canvas edits the interface visually before code is regenerated. Publishing is part of the agent loop, not a separate deploy step. **Lesson:** the plan should be an artefact the user can edit, and effort should be a visible tier. [docs](https://docs.replit.com/replitai/agent)

### Lovable

Chat, Plan and Build modes; an approved plan stays editable; credit cost differs by mode; connectors require explicit approval; GitHub sync exports the result. Plan mode produces a structured spec that must be approved before Build executes it, and connectors (Slack, GitHub, Supabase) are approved per connection. The plan is the contract; the chat is the steering wheel. **Lesson:** approval belongs at the connector boundary, where data leaves. [docs](https://docs.lovable.dev/)

### Bolt.new

Plan mode, version history and backups, visual edits applied to a live preview, Bolt Cloud database, hosting and domains, GitHub sync and a security scan. Visual edits are translated back into source, every edit is recoverable, and Bolt Cloud ships the artefact from the same surface. The preview is the source of truth for the user; code follows. Tokens meter usage. **Lesson:** let users manipulate the artefact directly and translate that into code. [support](https://support.bolt.new/)

### v0

Ask, Auto and Full permission modes; a sandbox; browser use with screenshots; Design mode with diffable versions; MCP; GitHub-backed previews and PRs; Vercel publish. Design versions can be reviewed like code, screenshots let the agent verify its own output, and previews are backed by commits. Of the hosted cohort, v0 is closest to a governed agent — explicit modes, a sandbox and MCP `[inference]`. **Lesson:** one user-facing autonomy dial beats a page of toggles. [docs](https://v0.app/docs)

## Comparison

The table covers the terminal cohort; hosted products are compared in their sections.

| Agent | Language / architecture | TUI quality | Session & undo | Permissions | Extension | Cost UX | Standout |
|---|---|---|---|---|---|---|---|
| Gemini CLI | TS, React-Ink | Strong | `/rewind`, selective | allow/deny | extensions | quota | rewind |
| Aider | Python, monolithic | Fair | git + `/undo` | none | hooks only | token spend | repo map |
| Cline | TS, OpenTUI | Strong | shadow-git, 3-way | auto-approve | MCP market | BYOK | checkpoints |
| Continue | TS, Ink | Fair | none | policies | config MCP | BYOK | config-as-code |
| Cursor CLI | closed source | Strong | rewind, resume | typed DSL | plugins | plan + usage | permission DSL |
| Goose | Rust | Fair | fork, export | allowlist | MCP-native | BYOK | recipes, ACP |
| Crush | Go, Bubble Tea | Excellent | SQLite sessions | prompts, `--yolo` | MCP + OAuth | provider costs | TUI, LSP |
| Amp | closed, Bun/TS | Strong | thread URLs | per-tool | TS plugins | credits, orbs | durable threads |
| Warp CLI | closed source | Excellent | resume, handoff | profiles | MCP, skills | credits | PTY sharing |
| Copilot CLI | closed, npm | Strong | `/resume` | allow/deny/assist | MCP, hooks | premium requests | plan mode |

## Table stakes, ranked

Ranked by how many of the ten document it and how load-bearing it is.

1. **MCP client** — nine of ten; OAuth expected.
2. **Per-tool allow/ask/deny**, persisted.
3. **Selective checkpoints** — files, chat, or both.
4. **Resume, list, fork.**
5. **Plan mode** — read-only before writes.
6. **`AGENTS.md` rules.**
7. **Headless JSON** for CI.
8. **Context meter and compaction.**
9. **Subagents** with isolated context.
10. **Hooks and skills.**
11. **OS sandbox with network control.**
12. **Model picker and BYOK.**
13. **Per-turn cost display.**

## Differentiators

Almost nobody here can do what Tamias already does:

- **Signed, project-bound policy with expiry** — tools, paths, shell, domains, models.
- **Gateway budgets** — reserve-then-settle, caps and rate limits on a key, not a config file.
- **One provider key at the gateway**, safe from prompt-injection exfiltration.
- **Audit ledger** joining tool decisions to metered calls.
- **Cost-per-success** via `bench.py`.
- **Offline brief and index.**

The risk is not a rival shipping signed policy, but that MCP, checkpoints and resume become expected and Tamias is rejected before the governance argument is heard. Build those first, then sandbox and PTY. Governance is the moat; the table stakes are the door.
