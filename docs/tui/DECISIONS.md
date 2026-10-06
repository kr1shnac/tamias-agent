# TUI Design & Architecture Decisions

## 1. Inline vs. Fullscreen Mode
**Decision: Inline-First for Chat, Fullscreen for Dashboards/Diffs.**
*Reasoning*: Prototyping `App(inline=True)` proves that preserving the terminal's native scrollback buffer is vastly superior for a chat interface. Users expect to scroll up with native terminal controls, copy text easily, and not feel "trapped" in an alt-screen application. We will use Textual's inline mode by default for the active conversation turn, ensuring differential rendering is constrained to the active area. For complex modals (e.g., full-screen file diffs or the command palette), we will temporarily push a fullscreen `Screen` (alt-screen mode), restoring the inline state upon exit.

## 2. Background Transparency & OSC 11
**Decision: Query OSC 11 to derive layered surfaces.**
*Reasoning*: While Textual allows `background: transparent;` (which perfectly preserves terminal wallpaper/translucency), we cannot natively apply CSS filters like `backdrop-filter: blur()`. To simulate glass, we need to know the *actual* RGB of the terminal background to mix our 4%, 8%, and 12% "raised" surface tints. 
We will query OSC 11 with a short timeout. If it succeeds, we dynamically update our base TCSS variables. If it times out (e.g., in tmux without passthrough), we fallback to the curated `aurora`, `ember`, or `mono` palettes.

## 3. Streaming Markdown Performance
**Decision: Incremental append-only via `RichLog` or Custom Widget.**
*Reasoning*: Re-rendering a full 10k token `Markdown` widget on every token delta forces the engine to re-parse the entire AST 30 times a second. This causes CPU spikes and potential jitter. Instead, we will use a custom chunking renderer or `RichLog(markup=True)` which supports append-only streaming. Once the turn completes (the `TurnEnd` event fires), we will swap the raw log for a fully-rendered `Markdown` widget to ensure perfect formatting and syntax highlighting without the streaming penalty.

## 4. Synchronized Output (DEC 2026)
**Decision: Enable globally.**
*Reasoning*: Textual v8+ supports DEC 2026 natively if the terminal emulator advertises it. We will ensure this flag is not suppressed, preventing horizontal tearing during rapid inline resizing or streaming.
