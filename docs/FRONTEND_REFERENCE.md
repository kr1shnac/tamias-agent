# TAMIAS AGENT — FRONTEND REFERENCE

**Single consistent "kinda black" theme. One source of truth. No iterations, no variants.**

This file is the definitive UI/UX reference **and build brief** for the Tamias Agent
terminal frontend. It is derived from the authoritative implementation in
`tui/app.py` (the `TCSS` string + `TAMIASApp`). This is the only frontend design
in the project; the earlier drafts and iterations have been removed.

Tag this file (`docs/FRONTEND_REFERENCE.md`) in any follow-up chat that builds or
restyles the terminal UI. If code and this file disagree, **`tui/app.py` wins** —
then update this file.

---

# ▶ BUILD BRIEF — READ THIS FIRST

**You are building the Tamias Agent terminal frontend.** This file is the complete
spec: theme, widgets, layout, product rules, and the agent integration contract.
Read it top to bottom, then implement in the order in **§B**.

## A. Tech stack (do not change)
- Python 3 + **Textual `8.2.8`** (its CSS dialect is "TCSS") + **Rich `15.0.0`**.
- Theme lives in `tui/app.py` as the `TCSS` string. Put new styles there (or split
  into TCSS files and set `CSS_PATH`, but keep one visual source of truth).
- Run: `cd tamias-agent && .venv/bin/python -m tui.app` (or `textual run --dev tui/app.py`).

## B. What EXISTS today vs what you must BUILD

| Area | Status | Where |
|---|---|---|
| Theme + transcript, turns, tool cards, composer | **EXISTS** | `tui/app.py` |
| Model picker modal | **EXISTS** | `tui/model_picker.py` |
| Event dataclasses (protocol) | **EXISTS, now emitted** | `tui/events.py` |
| Glass / gradient helpers | **EXISTS** | `tui/color_math.py` |
| Agent→TUI adapter (queue producer) | **BUILT** | `tui/bridge.py`, `agent.py` (`on_event`) |
| Credits header readout + F3 dashboard (§5) | **BUILT** | `tui/credits.py`, `tui/widgets.py`, `tui/modals.py` |
| Task board + completion flow (§6) | **BUILT** | `tui/tasks.py`, `tui/modals.py` |
| Model **tier** cycling UX (§7) | **BUILT** — `MODEL_TIERS` + `M` | `tui/app.py` |
| Boundary-violation modal (§8) | **BUILT** — driven by blocked results | `tui/modals.py` |
| Nav bindings `T` / `C` / `H` / `F3` (§9) | **BUILT** (+ nav mode / `/commands`) | `tui/app.py` |
| Session / task / credits panels | **BUILT** — task board + credits dashboard | `tui/app.py` |
| Landing hero / home screen (§4.1) | **BUILT** — no chrome, swap on first turn | `tui/branding.py` |
| Slash-command palette (§4.2) | **BUILT** — `/` menu, `↑↓`/`Tab`/`Enter` | `tui/slash.py` |
| Responsive header (§3.A) | **BUILT** — drops chips, never clips | `tui/app.py` |

## C. Integration contract (how the UI talks to the agent)
- `TAMIASApp(ui_queue, agent_queue, company_id=None)` takes **two `queue.Queue`s**.
- UI → agent: put the user's text on `ui_queue`.
- Agent → UI: `tui/bridge.py` runs the real agent core on a thread and emits
  `events.py` dataclasses on `agent_queue`; the app's `listen_to_agent` worker
  renders them (see §12).
- Launch with `python agent.py` (the TUI is the default on an interactive
  terminal), or `python agent.py --tui` to force it; `--plain` keeps the classic
  text REPL and non-TTY runs never open a screen. `python agent.py --tui
  --company-id acme` bounds work to a company; `python -m tui.bridge` starts the
  bridge standalone. The CLI banner is printed only on the text-REPL path, so it
  never scribbles over the TUI. `agent.run_turn` / `run_task` take an optional
  `on_event` callback, so the CLI (`on_event=None`) is unchanged.

## D. Build order (do in sequence)
1. **Adapter:** run the agent's model loop and emit `TurnStart / MessageDelta /
   ToolStart / ToolEnd / TurnEnd / StatusUpdate` onto `agent_queue`; read user turns
   from `ui_queue`.
2. **Credits** (§5): compute savings from `TurnEnd` token counts vs the Codex
   baseline; render the always-visible header readout + the F3 dashboard.
3. **Task board + completion modal** (§6); wire the `T` and `C` bindings.
4. **Boundary-violation modal** (§8) driven by blocked-tool results.
5. **Model tiers** (§7) + the `M` binding.
6. **Help overlay** (`H`).

## E. Acceptance criteria (definition of done)
- [x] Credits readout is always visible and color-coded (green ≥39% · amber 20–38% · red <20%).
- [x] Every tool call renders a card that transitions active → finished.
- [x] A task can only be completed through the confirmation modal.
- [x] A boundary violation shows the red `BLOCKED` modal.
- [x] No `.env` value is ever read or rendered.
- [x] The palette is exactly §1 — introduce no new colors.
- [x] No header chip or the composer box is ever clipped, at any terminal width.
- [x] `/` opens a command palette; unknown `/…` never reaches the agent.
- [x] The landing shows no chrome (no header, no bottom bar); the first submitted
      message swaps in the full chat with the header and the bottom composer.
- [x] No fullscreen mode — opening the chat *is* "full screen".

## F. Scope & rules
- **Frontend only.** Do not rewrite `agent.py`'s tool logic or weaken any test.
- **One theme, one design.** The earlier drafts and iteration variants have been
  removed; do not reintroduce a second theme or a parallel TUI.
- `tui/app.py` is authoritative; if you change the theme, update this file too.
- **`.env` is off-limits** — never read, log, echo, or display it.

---

## 0. TL;DR (Cheat Sheet)

```
Background   #0d0d0d      Text        #e8e8e8
User accent  #00ff9f      Agent accent #00b8ff
Panels       #1a1a1a      Panel border #3a3a3a
Glass        rgba(255,255,255,0.03) bg / 0.1 border / 0.3 top edge
```

Navigation: `T` task · `C` complete · `M` model · `H` help · `Q` quit · `F3` credits.
Plain letters work in nav mode (`Esc`); `F3`/`Ctrl+T` and the `/commands` work while typing.
Type `/` for the command palette (`↑↓` move · `Tab` complete · `Enter` run · `Esc` close).
On start you get a chrome-free centred `TAMIAS` wordmark + input; the first message
opens the chat (header appears, composer drops to the bottom). No fullscreen mode.

Credits header always visible → `SCR 58/150 (39% saved)` → green ≥39%, amber 20–38%, red <20%.

---

## 1. CORE THEME — "KINDA BLACK"

**Philosophy.** A near-black terminal (`#0d0d0d`) with extremely low-opacity white
overlays that read as subtle "glass", plus two neon accents: green `#00ff9f` for
the user and cyan `#00b8ff` for the agent. The base is *unwaveringly black* — the
glass is suggested by overlays, not by real transparency.

**Core principle.** The agent is a *focused team member*. The UI shows only what
matters: **work boundary · task status · credits saved**. Nothing decorative
competes with those three signals.

### 1.1 Base palette

| Role | Hex / RGBA | Notes |
|---|---|---|
| `screen.background` | `#0d0d0d` | Base terminal background |
| `screen.color` | `#e8e8e8` | Primary text |
| `panel.background` | `#1a1a1a` | Header bar + composer bar |
| `panel.border` | `#3a3a3a` | Border between panels |
| `user.turn.color` | `#f8fafc` | User message text (very light) |
| `agent.turn.color` | `#e2e8f0` | Agent message text (blue-white) |
| `user.icon` | `#00ff9f` | User gutter icon / green accent |
| `agent.icon` | `#00b8ff` | Agent gutter icon / cyan accent |
| `tool.card.color` | `#94a3b8` | Tool card body text |
| `tool.finished.color` | `#64748b` | Finished tool text (muted) |
| `tool.args.color` | `#64748b` | Dimmed tool args |
| `wordmark.color` | `#00b8ff` | Gradient start (cyan) |
| `model.display.color` | `#00ff9f` | Gradient end (green) / live model chip |
| `error.color` | `#fca5a5` | Boundary violations / failures |

### 1.2 Glass accents (fixed values — no variants)

| Name | Value | Opacity | Usage |
|---|---|---|---|
| `tool.card.background` | `rgba(255,255,255,0.03)` | 3% | Tool card fill (barely-there lift) |
| `tool.card.border` | `rgba(255,255,255,0.1)` | 10% | Tool card outline |
| `tool.card.border-top` | `rgba(255,255,255,0.3)` | 30% | Tool card top edge (depth) |

Tool cards are the only glass surface in the shipped UI — the turn containers are
plain, borderless text (§E). Add a new glass surface by extending these three
values, not by inventing new ones.

---

## 2. AUTHORITATIVE TCSS (from `tui/app.py`)

This is the shipped stylesheet. Treat it as canonical.

```css
Screen {
    background: #0d0d0d;
    layout: vertical;
    color: #e8e8e8;
}

/* --- Transcript --- */
#transcript-area {
    height: 1fr;
    padding: 2 3;
    overflow-y: auto;
    align: left top;
}

/* --- Home screen (OpenCode-style) --------------------------------------
   Before the first message there is no chrome: the header bar is hidden and
   the wordmark + composer sit together in the middle of the screen. The first
   submitted message drops Screen.landing and the full chat takes over. */
Screen.landing {
    align-horizontal: center;
    align-vertical: middle;
}
Screen.landing #header-bar { display: none; }
Screen.landing #transcript-area {
    height: auto;
    width: 76;
    max-width: 100%;
    align: center middle;
}
Screen.landing #composer {
    height: auto;
    width: 76;
    max-width: 100%;
    background: transparent;
    border-top: none;
    padding: 0 3;
}
Screen.landing #slash-menu {
    width: 76;
    max-width: 100%;
}
#hero {
    height: auto;
    width: auto;
}

.turn {
    height: auto;
    margin-bottom: 1;
    max-width: 112;
}

.user-turn-container {
    height: auto;
    margin-bottom: 1;
    max-width: 112;
}

.user-turn {
    color: #f8fafc;
    text-style: bold;
}

.agent-turn {
    color: #e2e8f0;
}

/* the agent turn's inner column must size to its content, not fill the
   viewport, or every turn would push the transcript off screen */
.turn-body {
    height: auto;
    width: 1fr;
}

/* --- Gutter --- */
/* fixed 2-cell gutter (icon + one space) so every turn's text and every
   tool card starts on the same column regardless of the icon glyph */
.gutter-icon {
    width: 2;
    margin-right: 0;
    content-align: left top;
}
.user-icon  { color: #00ff9f; }
.agent-icon { color: #00b8ff; }

/* --- Tool cards --- */
.tool-card {
    height: auto;
    background: rgba(255, 255, 255, 0.03);
    border: round rgba(255, 255, 255, 0.1);
    border-top: round rgba(255, 255, 255, 0.3);
    padding: 0 1;
    margin: 1 0 1 4;
    width: 80%;
    color: #94a3b8;
}

.tool-active {
    border: round #00b8ff;
    border-top: round #00ff9f;
    color: #f8fafc;
}

.tool-finished {
    background: transparent;
    border: none;
    /* pad to the same content column as an active card (margin 4 + border 1
       + padding 1 = 6) so a finished tool name never jumps left */
    padding: 0 1 0 2;
    margin: 0 0 0 4;
    color: #64748b;
}

.tool-header { layout: horizontal; height: 1; }
.tool-name   { text-style: bold; width: 1fr; }
.tool-status { width: auto; }
.tool-args   { color: #64748b; }

/* --- Header bar --- */
#header-bar {
    layout: horizontal;
    padding: 0 3;
    height: 2;
    background: #1a1a1a;
    border-bottom: solid #3a3a3a;
}

#wordmark {
    width: 1fr;
    content-align: left middle;
    text-style: bold;
    color: #00b8ff;
}

/* Credits: always visible, colour-coded by savings rate (§5) */
#credits-readout {
    width: auto;
    content-align: right middle;
    padding: 0 2;
    text-style: bold;
}

#model-display {
    width: auto;
    color: #00ff9f;
    content-align: right middle;
    padding: 0 2;
    margin-left: 2;
    text-style: bold;
    min-width: 34;
}

/* responsive header: drop the wide model chip first, then the small wordmark
   (the credits readout stays visible), so nothing is ever clipped */
Screen.narrow #model-display { display: none; }
Screen.tiny #wordmark { display: none; }
Screen.tiny #header-bar { padding: 0 2; }

/* --- Slash palette (§4) --- */
#slash-menu {
    display: none;
    height: auto;
    max-height: 11;
    padding: 1 3;
    background: #141414;
    border-top: solid #2a2a2a;
    color: #e2e8f0;
}

/* --- Task board (§6) --- */
#task-board {
    display: none;
    height: auto;
    max-height: 10;
    padding: 1 3;
    background: #1a1a1a;
    border-top: solid #3a3a3a;
    color: #e2e8f0;
}

/* --- Composer --- */
#composer {
    height: 4;
    padding: 0 3;
    background: #1a1a1a;
    border-top: solid #3a3a3a;
    color: #e8e8e8;
}

.composer-prompt {
    color: #00ff9f;
    text-style: bold;
    width: 2;
    content-align: center middle;
}

#user-input {
    width: 1fr;
    background: #0d0d0d;
    border: solid #3a3a3a;
    padding: 0 1;
    color: #f8fafc;
}

#user-input:focus {
    border: solid #00b8ff;
    background: #1a1a1a;
}

/* Supporting tokens (§2.1) */
.composer-placeholder {
    color: #64748b;
    content-align: left middle;
}
.active-spinner {
    color: #00ff9f;
}

/* Model switch card (§7) */
.model-card {
    color: #00ff9f;
    margin: 1 0 1 4;
}
```

### 2.1 Supporting tokens

These ship in `app.py`'s `TCSS` and are kept because they carry real UI meaning,
with values normalized to the single consistent theme above:

```css
/* Placeholder text shown when the input is empty */
.composer-placeholder {
    color: #64748b;
    content-align: left middle;
}

/* Spinner tint while a tool / turn is active */
.active-spinner {
    color: #00ff9f;
}
```

**Glass surface scale** (`tui/color_math.py → get_glass_surfaces()`): a three-step
alpha stack used to simulate a physical glass layering without reading the true
terminal background (TTY race conditions make that unreliable):

| Step | Value | Meaning |
|---|---|---|
| `base` | `rgba(255,255,255,0.04)` | resting surface |
| `raised` | `rgba(255,255,255,0.08)` | raised / hovered surface |
| `overlay` | `rgba(255,255,255,0.12)` | overlay / top surface |

The shipped `app.py` uses its own `0.03` / `0.10` / `0.30` values for tool cards
(§2); the `color_math` scale is the general glass vocabulary. Prefer the `app.py`
values in the transcript, the scale above for new surfaces.

**Gradient helper** (`create_gradient_text(text, start, end)`): linearly interpolates
per-character RGB between two colors and applies `bold`. Used for `#wordmark`
(`#00b8ff → #00ff9f`). `color_math.oklch_to_srgb()` is available for perceptually
even gradients if needed.

**Spinner frames.** The busy indicator cycles these glyphs every tick (0.1 s):

```
⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏
```

**Gutter glyphs.** User `❯` (green `#00ff9f`) · Agent `⬡` (cyan `#00b8ff`) ·
System/task `◆`.

**Home screen.** There is no welcome *turn* any more. On mount the transcript is
replaced by a centred `#hero` wordmark (see §4.1); the first submitted message
swaps it out for the live conversation.

---

## 3. WIDGET SPECIFICATIONS

### A. `#header-bar` (top bar)
- `layout: horizontal`, `height: 2`, `padding: 0 3`
- `background: #1a1a1a`, `border-bottom: solid #3a3a3a`
- Contains `#wordmark` (left, flexible), `#credits-readout` (right), and
  `#model-display` (right, `min-width: 34`).
- Hosts the **always-visible credits readout while the chat is open** (see §5).
- **Hidden on the landing.** While `Screen.landing`, the whole bar is
  `display: none` — the home screen is chrome-free (§4.1); it returns the moment
  the first message opens the chat.
- **Responsive.** `TAMIASApp._apply_responsive()` (from `on_resize`) toggles
  `narrow` on the `Screen` below 104 cols and `tiny` below 64. `narrow` hides
  `#model-display`; `tiny` also hides `#wordmark` and tightens the padding. The
  credits readout is the one child that never hides — so the bar never clips the
  model id into the wordmark (the old bug) and never overflows the terminal.

### B. `#wordmark`
- `width: 1fr`, **left**-aligned middle, bold
- Left-aligned (not centred) so it sits on the same column as every other
  left-aligned element (turns, task board, composer) and never drifts as the
  credits readout / model chip change width.
- Renders a **cyan→green gradient** via `create_gradient_text(text, "#00b8ff", "#00ff9f")`.
- Text: `T A M I A S   A G E N T`. Hidden while `Screen.landing` (§4.1) and under
  `Screen.tiny`.

### C. `#model-display`
- `width: auto`, right-aligned middle, `padding: 0 2`, `margin-left: 2`, bold,
  `min-width: 34`
- `color: #00ff9f`
- Shows the **live model chip** with a single-cell status dot:
  `● ⟨ <model> · <effort> ⟩` (defaults: `nvidia/nemotron-3.5-lightning:free`,
  effort `auto`). No emoji — only monochrome glyphs.
- Updated on `init` / `model_update` events. Hidden under `Screen.narrow`.

### D. `#transcript-area`
- `height: 1fr`, `padding: 2 3`, `overflow-y: auto`, `align: left top`
- Holds alternating turn containers; auto-scrolls to newest.
- **Left**-aligned so the turn gutter sits on the same column as `#wordmark`
  (col 3) at every width; `max-width: 112` caps line length for readability
  without ever centring the column (which would drift the left edge on wide
  terminals).
- While `Screen.landing` (§4.1) the rule flips: `height: auto`, fixed column
  `width: 76` (centred), so the hero floats centred above the landing composer.

### E. Turn containers
- **User turn:** `Horizontal(gutter "❯", user-turn)`, class `user-turn-container`.
  Text `#f8fafc`, bold. Gutter icon green `#00ff9f`.
- **Agent turn:** `Horizontal(gutter "⬡", Vertical(agent-markdown, ...tool cards))`,
  class `turn`. Text `#e2e8f0`. Gutter icon cyan `#00b8ff`. While busy, text is
  tinted `#00b8ff` with a spinner frame; on completion it returns to `#e2e8f0`.
- The agent turn's inner `Vertical` carries class `.turn-body`
  (`height: auto; width: 1fr`). This is **required**: a `Vertical` defaults to
  `height: 1fr`, which would make every agent turn fill the viewport and push the
  transcript off screen. Any container that holds turn content must be
  `height: auto`.
- Gutter icons use a fixed 2-cell column (`.gutter-icon { width: 2 }`) so the
  turn text always starts on the same column.
- `<thought>…</thought>` blocks are rendered as `> **Thinking:**` block-quotes.
- Turns are separated by a uniform `margin-bottom: 1` (no extra padding), so the
  transcript rhythm is even.

### F. `.tool-card`
- Idle: `height auto`, `background rgba(255,255,255,0.03)`, `border round
  rgba(255,255,255,0.1)`, `border-top round rgba(255,255,255,0.3)`,
  `padding 0 1`, `margin 1 0 1 4`, `width 80%`, `color #94a3b8`.
- **Active** (`.tool-active`): `border round #00b8ff`, `border-top round #00ff9f`,
  `color #f8fafc`; shows a spinner (`⠧ running...`).
- **Finished** (`.tool-finished`): `background transparent`, `border none`,
  `padding 0 1 0 2`, `margin 0 0 0 4`, `color #64748b`. Arg line is hidden.
  Status stops as `✓ <n.n>s` (or `✓ done`), or `✗ failed` in red on error.
- `ToolCard` subclasses `Vertical`, so `height: auto` is **required** or the card
  would fill the viewport (same `1fr` trap as `.turn-body`).
- The active and finished left padding are chosen so the tool **name lands on the
  same column** in both states (parent + margin 4 + border 1 + padding 1 =
  parent + 6).
- Header row: `.tool-name` (bold, `1fr`) + `.tool-status` (`auto`).

### G. `#composer`
- `height: 4`, `padding: 0 3`, `background: #1a1a1a`, `border-top: solid #3a3a3a`
  (the extra row is required: the bordered `#user-input` is 3 rows, so a 3-row
  composer clipped its bottom border and the text sat on the last terminal row).
- `.composer-prompt` = green bold `❯ ` (`#00ff9f`), width 2, centered middle.
  Dropping the old `│ ` prefix puts the prompt glyph on col 3 — the same column
  as the turn gutters and `#wordmark` — and the input box left edge on col 5,
  the same column as turn text.
- `#user-input`: `background #0d0d0d`, `border solid #3a3a3a`, `padding 0 1`,
  text `#f8fafc`.
  Focus: `border solid #00b8ff`, `background #1a1a1a`.
- While the agent works: input is disabled, placeholder becomes `Agent is working...`.

### H. `#hero` (home screen, §4.1)
- A `Static` rendering `tui.branding.hero_text()`: a six-row ASCII-Shadow
  `TAMIAS` wordmark with a diagonal cyan→green gradient, a tagline and two hint
  lines. `min-width` is not set — the art is 52 cells wide, so below 60 cols
  `Hero(compact=True)` swaps in `fallback_text()` (a one-line brand).
- `height: auto`, `width: auto`; the transcript centres it while landing.

### I. `#slash-menu` (§4.2)
- `display: none` until a `/` value opens it; `height: auto`, `max-height: 11`
  (1 border + 2 padding rows + heading + six commands + "more"), `padding: 1 3`,
  `background #141414`, `border-top: solid #2a2a2a`.
- Renders a `MODELS`/`COMMANDS` heading and up to six rows as a single Rich
  `Text`; the highlighted row gets `❯` (green) and a bold white label.
- Owned by `tui/slash.py::SlashMenu`; the app owns the keys.

> **The component set is closed.** There is no `.plan-card`, no `.bubble`
> alternate chat layout, and no second theme. Turn containers (§E), tool cards
> (§F), the composer (§G), the landing hero (§H) and the slash palette (§I) are
> the complete component set; a new surface must extend §1/§2, not add a parallel
> design. (The hero and palette are the only additions since the first
> alignment pass; they reuse the existing palette and glyph vocabulary.)

### J. `ModelPicker` modal (`tui/model_picker.py`)

Pushed when the user runs `/model` (or `M`). A centered `ModalScreen[str]` that
dismisses with the chosen model id (or `""` to cancel via `Escape`).

Consistent-theme styling (shipped values use `#0f172a`; normalized here to the
theme's `#1a1a1a` panel + `#00b8ff` accent):

```css
ModelPicker {
    align: center middle;
    background: rgba(0, 0, 0, 0.7);   /* dim the transcript behind */
}

#picker-dialog {
    width: 60;
    height: auto;
    padding: 1 2;
    background: #1a1a1a;              /* shipped #0f172a → theme panel */
    border: round #00b8ff;
    color: #e2e8f0;
}

#picker-title {
    text-style: bold;
    color: #00ff9f;
    margin-bottom: 1;
    content-align: center middle;
}

OptionList {
    background: transparent;
    border: none;
}
```

- Title: `Select an LLM Model`.
- List = `OptionList` of the catalogue below; selecting dismisses with the model id.
- `Escape` cancels (`dismiss("")`).

**Model catalogue** (grouped as in `MODELS`):

*Free (`:free`, bills $0.00):*
`nvidia/nemotron-3.5-lightning:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`,
`nvidia/nemotron-3-super-120b-a12b:free`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`,
`poolside/laguna-s-2.1:free`, `poolside/laguna-xs-2.1:free`, `google/gemma-4-31b-it:free`,
`google/gemma-4-26b-a4b-it:free`, `dots-studio/dots-3-note-preview:free`,
`inclusionai/ling-3.0-flash-sante:free`, `liquid/lfm-2.5-2.6b:free`,
`apodex/apodex-1.1-mini:free`, `cohere/north-mini-code:free`,
`thinkingmachines/inkling:free`, `thinkingmachines/inkling-small:free`

*Paid (real rates):*
`anthropic/claude-3.5-sonnet`, `anthropic/claude-3-opus`, `openai/gpt-4o`,
`google/gemini-pro-1.5`, `meta-llama/llama-3-70b-instruct`

Default active model: `nvidia/nemotron-3.5-lightning:free` (env `AGENT_MODEL`).

---

## 4. LAYOUT ARCHITECTURE

```
Screen                          bg #0d0d0d · color #e8e8e8 · vertical
├── #header-bar                 h2 · bg #1a1a1a · border-bottom #3a3a3a · horizontal
│   ├── #wordmark               1fr · left · gradient cyan→green
│   ├── #credits-readout        auto · right · colour-coded SCR readout (§5)
│   └── #model-display          auto · right · green · model chip (● ⟨ … ⟩)
├── #transcript-area            h1fr · padding 2 3 · scroll · align left top
│   ├── Screen.landing → #hero   chrome-free centred wordmark block (§4.1)
│   ├── .turn / .user-turn-container
│   │   ├── .gutter-icon        ❯ (user) / ⬡ (agent) · fixed width 2
│   │   └── .user-turn | .agent-turn  (agent text wrapped in .turn-body)
│   └── .tool-card …            nested inside agent turn
├── #task-board                 hidden by default · T toggles (§6)
├── #slash-menu                 hidden by default · / opens it (§4.2)
└── #composer                   h4 · bg #1a1a1a · border-top #3a3a3a · horizontal
    ├── .composer-prompt        ❯  (green)
    └── #user-input             1fr input
```

**Screen.landing overrides the whole tree** (§4.1): `#header-bar` is
`display: none`, `#transcript-area` shrinks to the hero (`width: 76`, centred,
`height: auto`) and `#composer` loses its bar background, drops below the hero,
and is centred — so the home screen is wordmark + input, nothing else. There is
no fullscreen mode; opening the chat *is* "full screen".

### 4.1 Landing / home screen

On mount — and again after `/clear` — the app shows a **home screen** before any
conversation: `TAMIASApp._show_landing()` clears the transcript, adds
`Screen.landing`, and mounts `#hero` (`tui/branding.py`). The hero is a six-row
ASCII-Shadow `TAMIAS` wordmark with a diagonal `#00b8ff → #00ff9f` gradient,
a `bounded agentic coding · savings-first` tagline and two hint lines
(`type a task…` / `/model /task /credits /help`), all centred against the art's
52-cell width. Below 60 cols `Hero(compact=True)` renders a one-line fallback.

`TAMIASApp._enter_chat()` removes the `landing` class and the hero the first time
a message is submitted or an agent turn starts, and the conversation takes over —
the OpenCode-style "type to open the chat" hand-off. **The header bar, the
credits readout and the bottom-anchored composer appear at that moment** (the
landing is deliberately chrome-free, so the readout is not visible until the chat
opens — §5).

### 4.2 Slash-command palette

Typing `/` (with no space yet) opens `#slash-menu` above the composer with the
matching commands; `/model <partial>` switches it to the filtered model
catalogue. `tui/slash.py` holds the `Command` table, the `SlashMenu` widget
(rows + highlight) and the pure match/accept logic; `TAMIASApp` owns the keys:

| Key | Action |
|---|---|
| `↑` / `↓` | move the highlight (`on_key`, only while the composer is focused) |
| `Tab` | complete the highlighted row into the box, do not run (priority binding) |
| `Enter` | run the highlighted row: a leaf command executes, `/model` fills `/model ` and flips to models, a model row submits `/model <id>` |
| `Esc` | close the palette (and stay in the composer) |

Commands: `/model` (takes an arg) · `/task` · `/complete` · `/credits` · `/help`
· `/clear` · `/quit`. Typing an unrecognised `/…` never reaches
the agent: the app prints `unknown command … — press / for the list` as a system
turn.

**Modal screens** (`ConfirmModal`, `BoundaryModal`, `HelpScreen`,
`CreditsDashboard`) each assign `CSS = DIALOG_CSS` (from `tui/modals.py`) and the
model picker carries its own CSS. This is required: a `ModalScreen`'s child
`Vertical` defaults to `height: 1fr`, so without the stylesheet the dialog fills
the whole screen at the top-left instead of centring. `DIALOG_CSS` sets
`align: center middle` on the screen and `width`/`height: auto` on the dialog.

**Layout trap (fixed).** Textual's `Vertical` defaults to `height: 1fr;
width: 1fr`. Any container used *inside* a turn (the agent text column
`.turn-body`, the `.tool-card`) must set `height: auto`, or it expands to the
viewport and pushes the transcript off screen with a spurious scrollbar.

---

## 5. CREDITS DISPLAY (always visible in the chat)

Credits are the reason the product exists. **Never hide them** while the chat is
open (§4.1: the chrome-free landing intentionally shows no header until the first
message).

**Header readout** (single line in `#header-bar`, right side; always visible):

```
SCR 58/150 (39% saved)
```

The readout is colour-coded (see table below); it is **not** boxed — the model
chip sits to its right on the same line (`● ⟨ model · effort ⟩`).

It is also the one header child that **never hides**: the responsive header
(§3.A) drops `#model-display` first and `#wordmark` second when the terminal is
narrow, so the credits readout is always present and never pushes anything off
screen.

**Color coding by savings rate:**

| Savings | Color | Sample |
|---|---|---|
| **≥ 39%** | green `#00ff9f` | `SCR 58/150 (39% saved)` |
| **20–38%** | amber `#f59e0b` | `SCR 80/150 (27% saved)` |
| **< 20%** | red `#fca5a5` | `SCR 132/150 (12% saved)` + `WARNING: low savings` |

**Detailed dashboard** (`F3` / focused panel). Icons are single-cell
**monochrome glyphs** (no emoji) and every label is padded to the same width, so
the `:` column lines up exactly:

```
◆ CREDITS DASHBOARD
◈ BALANCE  : 92 / 150 credits (61.3% remaining)
◇ SAVINGS  : 58 credits (39% vs Codex baseline)
↗ TREND    : steady vs baseline
✓ PASS RATE: 57.9% (parity with Codex — no quality loss)
⬡ MODEL    : free (async-optimized)
⇄ ASYNC    : ~80% of tool calls parallelized
⬚ BOUNDARY : enforced — zero off-task spend

MODEL USAGE ──────────────────────────────────────────────
free    █████████████         65%
mid     █████                 25%
premium ██                    10%
```

Row icons: `◈` balance · `◇` savings · `↗` trend · `✓` pass rate · `⬡` model ·
`⇄` async · `⬚` boundary. The `MODEL USAGE` rule spans the full dialog content
width, and the bar + `%` column is fixed so the percentages line up.

**How the numbers are computed** (`tui/credits.py`). Each `TurnEnd` folds its
`prompt_tokens` / `completion_tokens` into a `CreditsLedger`. Credits are a
weighted token count (per 1000 tokens) plus a fixed per-turn overhead:

| | prompt | completion | per-turn overhead |
|---|---|---|---|
| Tamias | `0.25` | `1.0` | `0.5` |
| Codex baseline | `0.50` | `1.5` | `0.6` |

`savings = codex_spent − spent`, `savings% = savings / codex_spent`, and
`balance = budget (150) − spent`. The readout
(`SCR <saved>/150 (<pct>% saved)`) is colour-coded by the thresholds above;
before the first turn it is neutral `#e8e8e8`. Brief turns save less (amber /
red), long agentic turns land green — the gauge is an estimate, not a bill.

The dashboard's TREND / PASS RATE / ASYNC / BOUNDARY rows are steady-state
labels; only BALANCE and SAVINGS are derived from live token counts.

---

## 6. TASK COMPLETION FLOW

```
1. Agent works the task; progress bar advances (█ per %)
        │
2. Reaches 100% → modal: "Task complete? [Y/N]"
        │
3. [C] pressed →
        ├── Yes → agent writes savings report
        │         "Saved 58 credits (39%) vs Codex baseline"
        │         saves task.json under company/tasks/
        └── No  → return to transcript, task continues
        │
4. Marked completed →
        ├── task board: "[✓] PROJ-1457 completed"
        └── team view refreshes; next queued task or idle
        │
5. Session log: "PROJ-1457 completed in 00:23:45 · 57.9% pass"
```

**Implementation** (`tui/tasks.py`, `tui/modals.py`). A task begins on
`TurnStart` (id `PROJ-####`, project/assignee from `--company-id`, start time
now). Tool cards nudge progress up to a 95% in-flight cap; `TurnEnd` fills it to
100% and shows a "task ready — press C" line. Completion is *only* possible
through `ConfirmModal` (`C` / `/complete`): **Yes** writes the report, logs the
line, and resets the engine to free; **No** returns to the transcript with the
task still open. When `--company-id` is set the report is written to
`company/tasks/PROJ-####.json`. The board also carries the boundary status
line (§10 item 6): `enforced · company/work/<id>/` when a company is assigned,
`active` otherwise, and `violation` after a blocked tool result.

---

## 7. MODEL SWITCHING PROTOCOL

`M` cycles the engine:

```
free (nemotron-3.5-lightning) → mid-tier → premium → free
```

Each switch shows a small aligned card, then persists for the **current task
only**:

```
┌ MODEL ─────────────────┐
│ model   : premium      │
│ savings : 33% vs Codex │
│ pass    : 57.9%        │
└────────────────────────┘
```

The box is built from the row widths so its edges always line up (rendered as a
`.model-card` turn).

**Rationale.** Free model for ~80% of simple turns (list/read/search), mid-tier
~15%, premium ~5% (multi-file / git / hard reasoning). Switching is always
user-initiated — never automatic without a prompt.

**Tier map** (`MODEL_TIERS` in `tui/app.py`):

| Tier | Model |
|---|---|
| `free` | `nvidia/nemotron-3.5-lightning:free` |
| `mid` | `anthropic/claude-3.5-sonnet` |
| `premium` | `anthropic/claude-3-opus` |

`M` (or `/model <id>`) switches and shows the card; `/model` with no argument
opens the picker. Because printable keys are captured by the composer, `M`
fires in navigation mode (`Esc`) or through `/model` — see §9.

---

## 8. BOUNDARY ENFORCEMENT (work bounding)

The agent may only touch `company/work/<company_id>/`. Anything else is blocked
and surfaced loudly — never silently allowed.

```
◆ BOUNDARY VIOLATION
Outside company work area
assigned : acme
attempted: /etc/passwd
result   : BLOCKED
Error: '/etc/passwd' is outside company work area (company_id=acme)
[ OK ] → back to transcript
```
The `assigned` / `attempted` / `result` labels are padded to the same width so
their colons align. Red border `#fca5a5` + warning text. Enforced in
`resolve_in_company_workspace()` and checked by every file/shell tool. Off-task
requests (personal projects) get the same treatment: the agent is bounded to
assigned company work only.

**Implementation** (`tui/modals.py → BoundaryModal`). The app watches every
`ToolEnd` result; when it contains "outside company work area" or "outside the
workspace", it reads the attempted path out of the result (falling back to the
tool arguments) and pushes the red modal. `assigned` is the `--company-id`.
Closing the modal (`Enter` / `Space` / `Esc`) returns to the transcript; the
tool card still shows `✗ failed`.

---

## 9. NAVIGATION

| Key | Action |
|---|---|
| `↑` / `↓` | Move the slash-palette highlight (else move between panels / history) |
| `Tab` | Complete the highlighted slash row (else move focus) |
| `←` / `→` | Switch sections (Task / Credits / Session / Actions) |
| `Enter` | Accept the highlighted slash row, else activate / submit · recharge the composer |
| `T` | Toggle task & progress view |
| `C` | Complete current task (confirmation modal) |
| `M` | Cycle models (free → mid → premium) — same as `/model` |
| `H` | Help overlay |
| `Q` / `Ctrl+C` | Exit |
| `F3` | Credits dashboard (§5) |
| `Esc` | Close the slash palette, else leave the composer → navigation mode |
| `/` | Open the command palette (§4.2) |
| `/model` | Open the model picker (or `/model <id>` to set one) |
| `/task`, `/complete` | Task board / completion aliases |
| `/credits`, `/help` | Aliases |
| `/clear`, `/compact`, `/quit` | Forwarded to the agent / exit |

**Nav mode.** The composer owns printable keys, so `T`/`C`/`M`/`H`/`Q` fire
while it is blurred: press `Esc` to enter navigation mode, then `Enter` to
return. `F3`, `Ctrl+T`, `↑`/`↓` and every `/command` work while typing —
and while the slash palette is open, `↑`/`↓`/`Tab`/`Enter`/`Esc` drive it
instead (§4.2). There is **no fullscreen key** — the chat already takes the whole
screen.

---

## 10. AGENT BEHAVIOR RULES (UI contract)

**MUST always show**
1. Credits / savings — never hidden.
2. Current task: id, project, assignee, start time.
3. Progress (`███████░░░░░`).
4. Model in use (free / mid / premium).
5. Session id (hashed, identifiable, not secret).
6. Boundary status (enforced / active / violation).

**MUST NOT**
1. Hide credit information.
2. Access outside `company/work/<company_id>/`.
3. Auto-switch models without a user prompt.
4. Mark a task complete without the confirmation modal.
5. Show personal/off-task project data.
6. Print raw API keys/tokens (`.env` is never read, logged, or displayed).

**Visual feedback rules**
- Tool activation: border → `#00b8ff`, top → `#00ff9f`, text → `#f8fafc`.
- Tool completion: border removed, background transparent, text → `#64748b`.
- Boundary violation: red `#fca5a5` modal, `BLOCKED`, `[ OK ]` to dismiss.
- Savings thresholds: ≥39% green · 20–38% amber · <20% red.

---

## 11. FILE MAP (where things live)

```
tamias-agent/
├── docs/
│   └── FRONTEND_REFERENCE.md   ← THIS FILE (single source of truth)
├── tui/
│   ├── app.py                  ← authoritative TCSS + TAMIASApp (view + bindings)
│   ├── branding.py             ← landing hero: ASCII wordmark + gradient (§4.1)
│   ├── slash.py                ← slash-command table + SlashMenu widget (§4.2)
│   ├── bridge.py               ← agent→UI adapter: runs the core, emits events
│   ├── events.py               ← event protocol: TUIEvent, TurnStart, MessageDelta,
│   │                              StatusUpdate, ToolStart, ToolProgress, ToolEnd,
│   │                              TurnEnd, ErrorEvent  (emitted via bridge.py)
│   ├── credits.py              ← CreditsLedger + savings colour thresholds (§5)
│   ├── tasks.py                ← Task / TaskBoard + boundary detection (§6)
│   ├── widgets.py              ← ToolCard, CreditsReadout, TaskBoardWidget
│   ├── modals.py               ← ConfirmModal, BoundaryModal, HelpScreen,
│   │                              CreditsDashboard
│   ├── model_picker.py         ← /model picker screen
│   ├── color_math.py           ← glass scale + OKLCH gradient helpers
│   └── (no other UI: one design only)
└── agent.py                    ← agent core: Textual TUI (default on a TTY) with
                                   the classic Rich REPL behind `--plain`, plus
                                   company bounding, tools, model switching, and the
                                   `on_event` milestone hook the bridge consumes.
```

> This is the project's only frontend. The earlier drafts, iteration SVGs, and
> prototype UIs have been removed; do not reintroduce a second design.

---

## 12. EVENT PROTOCOL (UI ↔ agent)

The TUI renders by consuming dataclass events from the agent queue
(`tui/events.py`). All events extend `TUIEvent` (base: `to_dict()`, `to_json()`).

| Event | Fields | UI effect |
|---|---|---|
| `TurnStart` | `user_prompt`, `session_id` | open a new agent turn (⬡ gutter) |
| `MessageDelta` | `content`, `model` | append streamed agent text |
| `StatusUpdate` | `message`, `is_busy` | set spinner message + busy tint |
| `ToolStart` | `tool_call_id`, `tool_name`, `arguments` | mount `.tool-card.tool-active` with spinner |
| `ToolProgress` | `tool_call_id`, `output_chunk` | stream long-running tool output |
| `ToolEnd` | `tool_call_id`, `result`, `success`, `duration_sec` | mark card `.tool-finished`, stop spinner, hide args |
| `TurnEnd` | `prompt_tokens`, `completion_tokens`, `total_duration_sec` | close turn, re-enable input (feeds credit accounting) |
| `ErrorEvent` | `error_type`, `message`, `fatal` | surface an error; `fatal` ends the turn |

Internal dict messages (not dataclasses):
`{"type":"init"}` and `{"type":"model_update"}` update `#model-display`;
`{"type":"clear"}` clears the transcript.

**Note for implementers:** the TUI treats a tool as failed when
`ToolEnd.success` is false **or** the result starts with `Error:` — the two are
kept consistent.

**Credit link:** `TurnEnd.prompt_tokens` / `completion_tokens` are the raw input to
the credit-savings math in §5 (compare against the Codex baseline).

**Producer.** `tui/bridge.py` is the live backend: it runs `agent.run_turn` with
an `on_event` callback that maps the core's milestones to these dataclasses and
pushes them onto `agent_queue`; `agent.py --tui` starts it. The CLI passes no
callback, so its behaviour is unchanged.

---

*End of reference. If you change the theme, change `tui/app.py` and this file together.*
