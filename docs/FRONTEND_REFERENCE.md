# TAMIAS AGENT — FRONTEND REFERENCE

**Single consistent "kinda black" theme. One source of truth. No iterations, no variants.**

The product thesis behind the accountability surfaces is
[`docs/PREMIUM-AGENT.md`](PREMIUM-AGENT.md). This file remains the UI contract.

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
| Spend (USD) header readout + F3 dashboard (§5) | **BUILT** | `tui/credits.py`, `tui/widgets.py`, `tui/modals.py` |
| Task board + completion flow (§6) | **BUILT** | `tui/tasks.py`, `tui/modals.py` |
| Model **tier** cycling UX (§7) | **BUILT** — `MODEL_TIERS` + `M` | `tui/app.py` |
| Boundary-violation modal (§8) | **BUILT** — driven by blocked results | `tui/modals.py` |
| Boundary Card / receipt / decision card / plan contract / dossier / checkpoint / diff (§10A) | **BUILT** — `B` / `R` / `P` / `D` / `Z` / `V`, `/boundary` / `/receipt` / `/plan` / `/dossier` / `/checkpoint` / `/diff`; plan signature + dossier gate + file rewind + frozen diff | `tui/policy_view.py`, `tui/receipt.py`, `tui/plan.py`, `tui/dossier.py`, `checkpoints.py`, `tui/modals.py`, `tui/bridge.py` |
| Nav bindings `T` / `C` / `B` / `R` / `P` / `D` / `Z` / `V` / `H` / `F3` (§9) | **BUILT** (+ nav mode / `/commands`) | `tui/app.py` |
| Session / task / spend panels | **BUILT** — task board + spend dashboard | `tui/app.py` |
| Landing hero / home screen (§4.1) | **BUILT** — no chrome, swap on first turn | `tui/branding.py` |
| Slash-command palette (§4.2) | **BUILT** — `/` menu, `↑↓`/`Tab`/`Enter` | `tui/slash.py` |
| Responsive header (§3.A) | **BUILT** — drops chips, never clips | `tui/app.py` |

## C. Integration contract (how the UI talks to the agent)
- `TAMIASApp(ui_queue, agent_queue, company_id=None, task_id=None,
  assignee=None)` takes **two `queue.Queue`s**.
- UI → agent: put the user's text on `ui_queue`.
- Agent → UI: `tui/bridge.py` runs the real agent core on a thread and emits
  `events.py` dataclasses on `agent_queue`; the app's `listen_to_agent` worker
  renders them (see §12).
- Launch with `python agent.py` (the TUI is the default on an interactive
  terminal), or `python agent.py --tui` to force it; `--plain` keeps the classic
  text REPL and non-TTY runs never open a screen. `python agent.py --tui
  --company-id acme` bounds work to a company; `--task-id` / `--assignee` name
  the work and its owner and are forwarded to the task board (`run_tui(...)
  → TAMIASApp(...)`) so it shows the real values, never a made-up one;
  `python -m tui.bridge` starts the
  bridge standalone. The CLI banner is printed only on the text-REPL path, so it
  never scribbles over the TUI. `agent.run_turn` / `run_task` take an optional
  `on_event` callback, so the CLI (`on_event=None`) is unchanged.

## D. Build order (do in sequence)
1. **Adapter:** run the agent's model loop and emit `TurnStart / MessageDelta /
   ToolStart / ToolEnd / TurnEnd / StatusUpdate` onto `agent_queue`; read user turns
   from `ui_queue`.
2. **Spend** (§5): read the provider-billed `cost_usd` from each `TurnEnd`; render
   the always-visible header readout + the F3 dashboard.
3. **Task board + completion modal** (§6); wire the `T` and `C` bindings.
4. **Boundary-violation modal** (§8) driven by blocked-tool results.
5. **Model tiers** (§7) + the `M` binding.
6. **Help overlay** (`H`).

## E. Acceptance criteria (definition of done)
- [x] Spend readout is always visible and shows provider-billed USD only (no baseline, no invented budget).
- [x] Every tool call renders a card that transitions active → finished.
- [x] A task can only be completed through the confirmation modal.
- [x] A boundary violation shows the red `BLOCKED` modal.
- [x] `B` / `/boundary` shows the active policy as a human-readable card; with
      no policy it says "unbounded development mode", never "all clear".
- [x] Every finished turn produces a measured receipt; `R` / `/receipt` opens
      it, and a refused turn is distinguishable from a completed one.
- [x] A policy ask shows a decision card with action, reason, scope and the
      audit outcome of yes/no; denying stays fail-closed.
- [x] A turn that writes or runs a shell command creates a file checkpoint;
      `Z` previews it and restores only after `Y`, and a shell call is shown as
      not captured.
- [x] `V` / `/diff` opens the checkpoint's frozen, read-only diff; binary and
      oversized files say why no inline patch is shown.
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

Navigation: `T` task · `C` complete · `M` model · `B` boundary · `R` receipt ·
`P` plan · `D` dossier · `H` help · `Q` quit · `F3` spend.
Plain letters work in nav mode (`Esc`); `F3`/`Ctrl+T` and the `/commands` work while typing.
Type `/` for the command palette (`↑↓` move · `Tab` complete · `Enter` run · `Esc` close).
On start you get a chrome-free centred `TAMIAS` wordmark + input; the first message
opens the chat (header appears, composer drops to the bottom). No fullscreen mode.

Spend header always visible → `$0.0123` (provider-billed USD; `$0.0000 · no usage yet` before the
first turn). A separate `premium-equiv` chip shows the same tokens at premium
list rates; it is a hypothetical retail comparison, **not** a measured saving.
Unpriced steps append ` + N unpriced`; there is no colour band.

---

## 1. CORE THEME — "KINDA BLACK"

**Philosophy.** A near-black terminal (`#0d0d0d`) with extremely low-opacity white
overlays that read as subtle "glass", plus two neon accents: green `#00ff9f` for
the user and cyan `#00b8ff` for the agent. The base is *unwaveringly black* — the
glass is suggested by overlays, not by real transparency.

**Core principle.** The agent is a *focused team member*. The UI shows only what
matters: **work boundary · task status · spend (USD)**. Nothing decorative
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

/* Spend: provider-billed USD + hypothetical premium-equivalent (§5) */
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
   (the spend readout stays visible), so nothing is ever clipped */
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
- Hosts the **always-visible spend readout while the chat is open** (see §5).
- **Hidden on the landing.** While `Screen.landing`, the whole bar is
  `display: none` — the home screen is chrome-free (§4.1); it returns the moment
  the first message opens the chat.
- **Responsive.** `TAMIASApp._apply_responsive()` (from `on_resize`) toggles
  `narrow` on the `Screen` below 104 cols and `tiny` below 64. `narrow` hides
  `#model-display`; `tiny` also hides `#wordmark` and tightens the padding. The
  spend readout is the one child that never hides — so the bar never clips the
  model id into the wordmark (the old bug) and never overflows the terminal.

### B. `#wordmark`
- `width: 1fr`, **left**-aligned middle, bold
- Left-aligned (not centred) so it sits on the same column as every other
  left-aligned element (turns, task board, composer) and never drifts as the
  spend readout / model chip change width.
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

**Model catalogue** — generated, not hand-written:

`models/catalog.json` holds 54 tool-capable models fetched from the provider by
`demo/fetch_models.py`, each with its real list price. The picker offers only the
models this run can actually call:

- **free** (`:free`, bills $0.00) — always offered: `nvidia/nemotron-3.5-lightning:free`,
  `nvidia/nemotron-3-ultra-550b-a55b:free`, `google/gemma-4-31b-it:free`,
  `poolside/laguna-s-2.1:free`, `thinkingmachines/inkling:free`, … (16 in total)
- **mid / premium** (paid) — offered only with `--allow-paid` / `AGENT_ALLOW_PAID=1`
  or a direct key the configured endpoint can use (see `providers.py`).
  Default: hidden, so no row is a promise the run cannot keep.

Run `.venv/bin/python demo/fetch_models.py` to refresh the roster when the
provider's lineup moves. Counts are printed by the banner: `54 models (16 free)`.

---

## 4. LAYOUT ARCHITECTURE

```
Screen                          bg #0d0d0d · color #e8e8e8 · vertical
├── #header-bar                 h2 · bg #1a1a1a · border-bottom #3a3a3a · horizontal
│   ├── #wordmark               1fr · left · gradient cyan→green
│   ├── #credits-readout        auto · right · provider-billed USD readout (§5)
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
a `bounded agentic coding · measured, never guessed` tagline and two hint lines
(`type a task…` / `/model /task /credits /help`), all centred against the art's
52-cell width. Below 60 cols `Hero(compact=True)` renders a one-line fallback.

`TAMIASApp._enter_chat()` removes the `landing` class and the hero the first time
a message is submitted or an agent turn starts, and the conversation takes over —
the OpenCode-style "type to open the chat" hand-off. **The header bar, the
spend readout and the bottom-anchored composer appear at that moment** (the
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

Commands: `/model` (takes an arg) · `/task` · `/complete` · `/credits` ·
`/boundary` · `/receipt` · `/plan` · `/dossier` · `/checkpoint` · `/diff` ·
`/help` · `/clear` · `/quit`. Typing an unrecognised `/…` never reaches
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

## 5. SPEND DISPLAY (always visible in the chat)

Spend is the reason the product exists. **Never hide it** while the chat is open
(§4.1: the chrome-free landing intentionally shows no header until the first
message).

Every figure is **provider-billed USD**. The ledger never derives a number from
token counts, never compares against a baseline, and never invents a budget; a
step whose provider cost is missing is shown as *unpriced*, never as `$0`.

**Header readout** (single line in `#header-bar`, right side; always visible):

```
$0.0123
```

Before the first turn it reads `$0.0000 · no usage yet`. When any step was
unpriced it appends ` + N unpriced`. The readout is neutral `#e8e8e8` until the
first turn, then cyan `#00b8ff`; it is **not** boxed — the model chip sits to
its right on the same line (`● ⟨ model · effort ⟩`).

It is also the one header child that **never hides**: the responsive header
(§3.A) drops `#model-display` first and `#wordmark` second when the terminal is
narrow, so the spend readout is always present and never pushes anything off
screen.

**Detailed dashboard** (`F3` / focused panel). Icons are single-cell
**monochrome glyphs** (no emoji) and every label is padded to the same width, so
the `:` column lines up exactly. Every row is derived from recorded usage; none
is a literal:

```
◆ SPEND (USD, provider-billed)
◈ SPENT (USD) : $0.0123
◇ PRICING     : provider-billed USD
✓ TURNS       : 4
⬡ TOKENS      : 1,540
⇄ PROMPT      : 1,200
⇄ COMPLETION  : 340
```

When any step was unpriced the `PRICING` row reads `<N> steps unpriced` instead.

Row icons: `◈` spent · `◇` pricing · `✓` turns · `⬡` tokens · `⇄` prompt /
completion.

**How the numbers are computed** (`tui/credits.py`). Each `TurnEnd` carries the
provider-billed `cost_usd` and how many of its steps came back without one; the
app folds both into a `CreditsLedger`:

* `spent_usd` = the sum of the costs the provider reported (OpenRouter's
  `usage.cost`, or the OpenAI SDK's `usage.model_extra["cost"]`);
* `unpriced_steps` = API steps that reported no cost;
* `prompt_tokens` / `completion_tokens` = the counts, kept for display.

The ledger has **no budget field**: the per-key USD allowance lives in the
gateway, and until the agent can read it (Phase 4) the UI shows real spend,
unpriced steps, and a separate premium-equivalent that is explicitly
hypothetical. The premium-equivalent is not a budget and not a measured saving;
there is no colour band.

(D16: `test_dashboard_rows_are_all_derived_from_recorded_usage` renders these
rows against a ledger with known figures and fails on any literal the figures do
not produce.)

---

## 6. TASK COMPLETION FLOW

```
1. Agent works the task; the board shows step and tool counts (no invented %)
        │
2. Agent replies → board status "ready to review" (still not 100%)
        │
3. [C] pressed → modal: "Task complete?" with steps, tools and elapsed time
        │
4. [C] → Yes writes the task report
        │         "PROJ-1457 completed · 00:23:45 · $0.0123 spent
        │          this session (provider-billed USD)"
        │         saves task.json under company/tasks/
        └── No  → return to transcript, task continues
        │
5. Confirmed completed →
        ├── task board: "[✓] PROJ-1457 completed  ████████████████████ 100%"
        └── team view refreshes; next queued task or idle
```

**Implementation** (`tui/tasks.py`, `tui/modals.py`). A task begins on
`TurnStart` (id `PROJ-####`, or the `--task-id` given; project from
`--company-id`, assignee from `--assignee`, both `unassigned` when unspecified;
start time now). Tool cards increment step/tool counters; they do **not**
advance a percentage, because a turn has no known denominator while it runs.
`TurnEnd` marks the task `ready` and shows a "ready to review — press C" line.
Completion is *only* possible through `ConfirmModal` (`C` / `/complete`), and
only that confirmation sets progress to 100%: **Yes** writes the report, logs
the line, and resets the engine to free; **No** returns to the transcript with
the task still open. When `--company-id` is set the report is written to
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
┌ MODEL ───────────────────────────┐
│ model : premium                  │
│ spent : $0.0123 this session     │
└──────────────────────────────────┘
```

The box is built from the row widths so its edges always line up (rendered as a
`.model-card` turn).

**Rationale (design intent, not yet measured).** The free model is meant for
simple turns (list/read/search), mid-tier for edits and verification, premium
for multi-file / git / hard reasoning. Switching is always **user-initiated —
never automatic without a prompt**. Percentages of turns per tier are *not*
shown here because the agent has not measured them; when the routing work lands
(the `tamias` proxy's `routing.decide`, D2) the realised mix becomes a measured
number and can appear.

**Tier map** (`MODEL_TIERS` in `tui/app.py`, built from `models/catalog.json`):

| Tier | Source |
|---|---|
| `free` | every `:free` model in the catalog (16 today) |
| `mid` | cheap paid models — only with paid enabled |
| `premium` | flagship paid models — only with paid enabled |

With paid off, `MODEL_TIERS` contains the free models only; `m` walks that list.
Default active model: `nvidia/nemotron-3.5-lightning:free` (env `AGENT_MODEL`).

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

**The `.` path mistake.** A model sometimes starts by asking for `"."`. In a
bounded run that is the **repository root**, not the policy's product root, so
it is still refused. The tool returns a plain retry hint naming the product
root (`Error: '.' is the repository root, not the project. Use
'company/work/…/apps/…'…`) instead of the red violation modal. This is an
ordinary path-base mistake, not an escape attempt; the model can retry with the
full path in the same turn.

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
| `←` / `→` | Switch sections (Task / Spend / Session / Actions) |
| `Enter` | Accept the highlighted slash row, else activate / submit · recharge the composer |
| `T` | Toggle task & progress view |
| `C` | Complete current task (confirmation modal) |
| `M` | Cycle models (free → mid → premium) — same as `/model` |
| `B` | Boundary Card — what this agent may touch |
| `R` | Receipt for the last completed turn |
| `P` | Plan Card — the published plan and its contract state |
| `D` | Investigation Dossier — evidence the agent actually saw |
| `Z` | Checkpoint — preview and restore the last turn's tracked files |
| `V` | Diff — review the last turn's frozen tracked changes |
| `H` | Help overlay |
| `Q` / `Ctrl+C` | Exit |
| `F3` | Spend (USD) dashboard (§5) |
| `Esc` | Close the slash palette, else leave the composer → navigation mode |
| `/` | Open the command palette (§4.2) |
| `/model` | Open the model picker (or `/model <id>` to set one) |
| `/task`, `/complete` | Task board / completion aliases |
| `/boundary`, `/policy` | Boundary Card — the active fence in human language |
| `/receipt` | Receipt for the last completed turn |
| `/plan`, `/todos` | Plan Card — the published plan and contract state |
| `/dossier`, `/investigation` | Investigation Dossier — evidence and unknowns |
| `/checkpoint`, `/checkpoints`, `/undo` | Preview and restore the last file checkpoint |
| `/diff`, `/changes` | Review the last checkpoint's frozen diff |
| `/credits`, `/help` | Spend dashboard / help |
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
1. Spend (USD, provider-billed) — never hidden.
2. Current task: id, project, assignee, start time.
3. Progress (`███████░░░░░`).
4. Model in use (free / mid / premium).
5. Session id (hashed, identifiable, not secret).
6. Boundary status (enforced / active / violation).

**MUST NOT**
1. Hide spend information.
2. Access outside `company/work/<company_id>/`.
3. Auto-switch models without a user prompt.
4. Mark a task complete without the confirmation modal.
5. Show personal/off-task project data.
6. Print raw API keys/tokens (`.env` is never read, logged, or displayed).

**Visual feedback rules**
- Tool activation: border → `#00b8ff`, top → `#00ff9f`, text → `#f8fafc`.
- Tool completion: border removed, background transparent, text → `#64748b`.
- Boundary violation: red `#fca5a5` modal, `BLOCKED`, `[ OK ]` to dismiss.
- Spend is provider-billed USD, with a separately labelled hypothetical
  premium-equivalent; no savings thresholds and no colour band.

---

## 10A. ACCOUNTABILITY SURFACES (PREMIUM SLICE)

The product thesis is in `docs/PREMIUM-AGENT.md`. These surfaces are the first
implementation of it: they answer "what may it touch?", "what did it do?",
"why is it asking me?", "what is it trying to do?" and "what did it actually
see?" without a slide.

### 10A.1 Boundary Card — `B` / `/boundary`

- `tui/policy_view.py::boundary_sections(policy, company_id)` turns the active
  `PolicyProfile` into labelled rows. It reads only policy fields; it does not
  infer a permission that is not there.
- `tui/modals.py::BoundaryCard` renders a neutral cyan card (not the red
  violation modal), scrollable at 80 columns.
- With no policy object it must say **"none loaded"** and **"unbounded
  development mode"**. It must never say "all clear" or imply a fence exists.
- The card is a *view* of the dispatcher's policy, not a second enforcement
  path. The dispatcher remains the authority.

### 10A.2 Receipt — `R` / `/receipt`

- `tui/receipt.py::TurnReceipt` collects `TurnStart`, `ToolStart`, `ToolEnd`,
  `ToolAsk`, `ModelSwitch` and `TurnEnd` data. The model never writes it.
- Every finished turn mounts one `.receipt-line`:
  `receipt · <STATUS> · <measured counts> · <cost> · R to open`.
- The modal shows REQUEST, MODEL, WORK, CHECKS, POLICY, COST and RISKS, plus
  the measured PLAN / INVESTIGATION sections when the turn used
  `update_plan` or an evidence tool, and CHECKPOINT / RESTORE when the turn
  created a file checkpoint or the human restored one. The CHECKPOINT section
  carries the diff summary (`+added -removed`, path count) and the `V / /diff`
  hint.
- Status is factual: `ANSWERED`, `CHECKS PASSED`, `NEEDS REVIEW`, `CHECKS
  FAILED`, `BLOCKED`, `REFUSED`, `PLAN DENIED`, `PLAN BLOCKED`, `ERROR`.
- Honesty rules:
  - a failed, denied or plan-held call never appears as a changed file;
  - a missing provider cost is `cost unknown`, never `$0.0000`;
  - "checks passed" means the named command exited successfully; it does not
    mean the change is correct;
  - no "saved" language, no hypothetical comparison inside the receipt;
  - a changed file with no verification command is called out in RISKS;
  - a plan is called out as unsigned, denied or blocked; a dossier is called
    out as static evidence, with its unknown count;
  - a dossier gate hold is counted under `dossier holds`, not as a tool failure;
  - a checkpoint is **file-only**; a shell call is shown as `ran — not captured`,
    never as restorable;
  - a diff is evidence, not a promise: binary, oversized and truncated diffs
    say so in the card and the receipt, and never imply the whole file was
    reviewed;
  - the plan's cost range is labelled **hypothetical**, separate from the
    provider-billed cost.
- `C` copies the receipt as plain text; `R` / `Esc` closes it.
- The receipt is per-process for now; durable storage is Phase 2.

### 10A.3 Decision Card — ask-gated tools

- `ConfirmModal(title, body, details=[...])` renders action, reason,
  arguments, scope, and the audit outcome of yes/no.
- The hint states the fail-closed default: no answer (or `Esc`) is a denial.
- The decision is counted in the receipt (`approvals`, `approval denials`).
- Details are plain text (`markup=False`), so model-produced arguments cannot
  inject dialog styling.

### 10A.4 Plan Card — `P` / `/plan`

- `tui/plan.py::parse_plan(result)` reads only the deterministic output of
  `agent.update_plan`: the `plan updated` header, `[x]` / `[~]` / `[ ]` steps,
  and the contract facts (`files:`, `verification:`, `risk:`, `cost range:`,
  `contract: signed by user`). An error or a header with no steps returns
  `None`; the card never invents a plan.
- Every turn that publishes a plan mounts one `.plan-line`:
  `plan · <done>/<total> done · <in-progress> [· <n> files] [· signed] · P to open`.
- The modal shows PLAN, STEPS and CONTRACT. CONTRACT reports signed/unsigned,
  files, verification, risks, and the hypothetical cost range. If no files were
  declared it says **"no files declared — path drift is not enforced"**.
- **Plan Contract gate.** In the TUI, `tui.bridge.PlanGate` sends `PlanAsk` and
  blocks the agent worker until the human answers. `PlanContractModal` shows the
  exact steps and contract facts; `Y` signs, `N`/`Esc` denies, and closing the
  screen or timing out is a denial. There is no default yes.
- While a published plan is unsigned, `write_file`, `edit_file`,
  `create_directory` and `run_shell` are held. A denial stops the turn. Status-
  only progress updates reuse the signature; changing steps, files,
  verification, risks or cost range asks again. A task where the model never
  publishes a plan is not forced into one; the gate is opt-in per plan.
- When the signed plan names files, a write outside that list is file drift:
  `Error: plan contract - path ... is not in the signed plan`. The turn stops
  and the receipt says `PLAN BLOCKED`. Shell commands are signature-gated but
  not path-scoped; the card states that limit.
- The receipt gets a `PLAN` section with progress, contract state, files,
  verification, cost range, risks and the steps.
- `C` copies the plan as plain text; `P` / `Esc` closes it.

### 10A.5 Investigation Dossier — `D` / `/dossier`

- `tui/dossier.py::TurnDossier` parses the evidence tools' deterministic text:
  `investigate_target` (`[evidence] path:line`), `trace_feature`
  (`Step N | path:line | text`), `analyze_structure` (`[FILE] path`), and the
  unresolved questions from `finish_investigation`.
- It keeps only what the tools returned: targets, methods, evidence lines,
  limitations, unknowns, confidence. Tool errors are ignored. Duplicate evidence
  is collapsed by `(path, line, text)`.
- Every turn that gathered evidence mounts one `.dossier-line`:
  `dossier · <n> investigation(s) · <n> evidence lines · <n> unknowns · D to open`.
- The modal shows SUMMARY, one INVESTIGATION section per tool result, EVIDENCE,
  LIMITATIONS and UNKNOWNS. Evidence is plain text (`markup=False`).
- Honesty rules: static evidence is not runtime proof; zero evidence is shown
  as zero, not as a conclusion; the gate requires *some* evidence from an
  actual evidence tool, not proof of relevance to the exact write.
  `finish_investigation` alone does not unlock a write.
- **Pre-write dossier gate.** In the TUI, the first mutating call in a turn
  (write tools or `run_shell`) is held until an investigation tool returns
  evidence. The hold is a normal tool error so the model can investigate and
  retry in the same turn; the receipt counts it as `dossier holds`, not a
  failure. `AGENT_DOSSIER_GATE=0` disables it for a quick demo; the default is
  on.
- The receipt gets an `INVESTIGATION` section with targets, evidence count,
  unknowns and methods.
- `C` copies the dossier as plain text; `D` / `Esc` closes it.

### 10A.6 Time Travel checkpoint — `Z` / `/checkpoint`

- `checkpoints.py::Checkpoint` records the pre-write bytes of every path a turn
  is about to create or overwrite (`write_file`, `edit_file`,
  `create_directory`). Capture happens **after** the plan, dossier and policy
  gates allow the call, so a denied write never leaves a checkpoint. A path is
  captured once per turn; the first state wins.
- The last 20 checkpoints are retained in memory for the session; the v1 UI
  exposes the latest. Storage is bounded (2 MB per file, 10 MB per checkpoint).
  A file too large or unreadable is shown as `unavailable`, not silently
  skipped.
- A `run_shell` call sets `shell_ran`. The checkpoint is then explicitly
  **incomplete**: restore puts back the tracked files, but shell changes outside
  them are not captured and the receipt says so.
- Every turn with a checkpoint gets a `.receipt` `CHECKPOINT` section: id, file
  count, shell state, diff summary and `Z / /checkpoint` / `V / /diff`. A later
  read-only turn does not erase the last checkpoint id. `TurnEnd` carries
  `checkpoint_id`, `checkpoint_files`, `checkpoint_shell` and the diff counts;
  the app resolves the full object through `checkpoint_lookup`, which `run_tui`
  wires to `agent.get_checkpoint`.
- `Z` (nav mode) or `/checkpoint` opens a `ConfirmModal` preview: checkpoint id,
  prompt, file count, shell state and up to ten paths with `modified`, `created`,
  `created directory` or `unavailable`. `Y` restores; `N`/`Esc` leaves the files
  untouched. There is no default yes and no silent restore.
- Restore is explicit, per file, atomic (`os.replace`), preserves the file mode,
  and refuses a path that is now a symlink or outside the workspace. A created
  file is removed; a modified file is restored; a created directory is removed
  only when empty. A failed path is listed under `RESTORE` and added to RISKS.
- If a restore has any failure, `restored_at` is not set, so the human can fix
  the blocker and retry. A successful restore marks the checkpoint restored and
  clears the active id.
- **Limits.** No conversation restore, no durable storage across processes, no
  selective per-file restore. Empty parent directories created by a new file may
  remain. This is not a substitute for version control.

### 10A.7 Diff — `V` / `/diff`

- `Checkpoint.freeze_diff()` runs when the turn closes, before the checkpoint is
  appended to the session list. It stores a bounded unified diff per tracked
  file, so a later edit cannot rewrite the evidence the receipt points at.
- `FileDiff` records `display`, `kind` (`modified`, `created`, `deleted`,
  `absent`, `binary`, `large`, `unavailable`, `type changed`), `added`,
  `removed`, `text`, `note` and `truncated`. Counts come from the full textual
  diff; the text may be shorter than the counts when the line cap is hit.
- `V` (nav mode) or `/diff` opens `DiffModal`, a read-only scrollable card:
  checkpoint id, frozen/current label, path count, `+added -removed`, and the
  per-file headers and diff lines. `C` copies it; `V`/`Esc` closes it. It never
  writes a file or runs a command.
- The modal and receipt are honest about what is not shown:
  - binary files say `binary file: N B -> M B; no textual diff`;
  - files over 256 KB say `inline diff skipped` and show the sizes;
  - a per-file cap (600 lines) or total cap (1,200 lines) marks the diff
    `truncated` and adds a RISK to the receipt;
  - a path that is now a symlink, outside the workspace or unreadable is
    `unavailable` and is never read through the link;
  - a shell call adds `shell not captured` to the subtitle.
- The diff is frozen at turn end. If the human edits the file afterwards, `V`
  still shows the turn's evidence, not the new state. That is deliberate: the
  receipt is a record, not a live diff.
- **Limits.** No editing from the diff, no per-file selection, no patch export
  beyond the plain-text copy. It is not a replacement for `git diff`.

### 10A.8 Keys and tests

`B` / `R` / `P` / `D` / `Z` / `V` work in nav mode (Esc first); `/boundary`,
`/receipt`, `/plan`, `/dossier`, `/checkpoint` and `/diff` work while the
composer is focused. Tests live in `test_premium_features.py`,
`test_tui_features.py` and `test_agent.py`; the full suite covers the TUI,
receipt accounting, refusal path, decision card, plan parsing and signature
gate, file drift, dossier parsing, evidence dedupe, the dossier hold, checkpoint
capture/restore, path-escape refusal, symlink refusal, the `Z`
confirmation/cancel paths, frozen diff rendering and diff-summary accounting.

---

## 11. FILE MAP (where things live)

```
tamias-agent/
├── docs/
│   └── FRONTEND_REFERENCE.md   ← THIS FILE (single source of truth)
├── checkpoints.py              ← Time Travel v1: file snapshots, preview,
│                                  restore safety (no UI imports)
├── tui/
│   ├── app.py                  ← authoritative TCSS + TAMIASApp (view + bindings)
│   ├── branding.py             ← landing hero: ASCII wordmark + gradient (§4.1)
│   ├── slash.py                ← slash-command table + SlashMenu widget (§4.2)
│   ├── bridge.py               ← agent→UI adapter: runs the core, emits events
│   ├── events.py               ← event protocol: TUIEvent, TurnStart, MessageDelta,
│   │                              StatusUpdate, ToolStart, ToolProgress, ToolEnd,
│   │                              TurnEnd, ErrorEvent  (emitted via bridge.py)
│   ├── credits.py              ← CreditsLedger (provider-billed USD only, §5)
│   ├── tasks.py                ← Task / TaskBoard + boundary detection (§6)
│   ├── receipt.py              ← TurnReceipt: measured per-turn record (§10A)
│   ├── policy_view.py          ← human-readable boundary rows (§10A)
│   ├── plan.py                 ← parse_plan + Plan model (§10A)
│   ├── dossier.py              ← TurnDossier + evidence parsing (§10A)
│   ├── widgets.py              ← ToolCard, CreditsReadout, TaskBoardWidget
│   ├── modals.py               ← ConfirmModal (decision card), BoundaryModal,
│   │                              BoundaryCard, ReceiptModal, PlanCard,
│   │                              PlanContractModal, DossierCard, HelpScreen,
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
| `TurnEnd` | `prompt_tokens`, `completion_tokens`, `total_duration_sec`, `cost_usd`, `unpriced_steps` | close turn, re-enable input (feeds spend accounting) |
| `ErrorEvent` | `error_type`, `message`, `fatal` | surface an error; `fatal` ends the turn |

Internal dict messages (not dataclasses):
`{"type":"init"}` and `{"type":"model_update"}` update `#model-display`;
`{"type":"clear"}` clears the transcript.

**Note for implementers:** the TUI treats a tool as failed when
`ToolEnd.success` is false **or** the result starts with `Error:` — the two are
kept consistent.

**Spend link:** `TurnEnd.cost_usd` is the provider-billed USD for the turn (and
`unpriced_steps` how many of its steps reported no cost); §5 folds both into the
ledger. Token counts are kept for display only — no number is derived from them.

**Producer.** `tui/bridge.py` is the live backend: it runs `agent.run_turn` with
an `on_event` callback that maps the core's milestones to these dataclasses and
pushes them onto `agent_queue`; `agent.py --tui` starts it. The CLI passes no
callback, so its behaviour is unchanged.

---

*End of reference. If you change the theme, change `tui/app.py` and this file together.*
