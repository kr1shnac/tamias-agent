import os
import queue
import re
import json
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Input
from textual import work
from rich.text import Text
from rich.markdown import Markdown as RichMarkdown

from tui.branding import Hero
from tui.events import (
    TurnStart, MessageDelta, ToolStart, ToolProgress, ToolEnd, TurnEnd,
    StatusUpdate, ErrorEvent,
)
from tui.credits import CreditsLedger
from tui.slash import SlashMenu
from tui.tasks import TaskBoard, is_boundary_violation
from tui.widgets import ToolCard, CreditsReadout, TaskBoardWidget, SPINNER_FRAMES
from tui.modals import ConfirmModal, BoundaryModal, HelpScreen, CreditsDashboard

# free → mid → premium (§7). The switch is user-initiated and scoped to the
# current task; completing a task resets the engine to free.
MODEL_TIERS = [
    ("free", "nvidia/nemotron-3.5-lightning:free"),
    ("mid", "anthropic/claude-3.5-sonnet"),
    ("premium", "anthropic/claude-3-opus"),
]

TCSS = """
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
"""


class TAMIASApp(App):
    CSS = TCSS

    # Plain letters work whenever the composer is not focused (see ✦ nav mode
    # below); the /commands and the function keys work while typing too.
    BINDINGS = [
        # priority so Tab completes the slash palette before focus traversal
        Binding("tab", "complete_slash", "Complete", priority=True, show=False),
        ("t", "toggle_tasks", "Task"),
        ("c", "complete_task", "Complete"),
        ("m", "cycle_model", "Model"),
        ("h", "help", "Help"),
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+t", "toggle_tasks", "Task"),
        ("f3", "credits", "Credits"),
        ("escape", "nav_mode", "Nav"),
        ("i", "focus_input", "Input"),
        ("enter", "focus_input", "Input"),
    ]

    def __init__(self, ui_queue: queue.Queue, agent_queue: queue.Queue,
                 company_id: str | None = None):
        super().__init__()
        self.ui_queue = ui_queue
        self.agent_queue = agent_queue
        self.company_id = company_id
        self.current_agent_turn = None
        self.current_agent_text = ""
        self.active_tools: dict[str, ToolCard] = {}
        self.agent_busy = False
        self.agent_busy_msg = ""
        self.spinner_idx = 0
        self.nav_mode = False
        self.listening = True
        self.session_id = ""

        self.current_model = os.environ.get(
            "AGENT_MODEL", "nvidia/nemotron-3.5-lightning:free")
        self.current_effort = os.environ.get("AGENT_EFFORT_POLICY", "auto")

        self.ledger = CreditsLedger()
        self.board = TaskBoard(project=company_id or "acme",
                               assignee=company_id or "tamias")

    # ------------------------------------------------------------------ view
    def compose(self) -> ComposeResult:
        with Horizontal(id="header-bar"):
            yield Static(create_gradient_text("T A M I A S   A G E N T",
                                              "#00b8ff", "#00ff9f"),
                         id="wordmark")
            yield CreditsReadout(self.ledger, id="credits-readout")
            yield Static(self._model_chip(), id="model-display")

        with ScrollableContainer(id="transcript-area"):
            pass

        yield TaskBoardWidget(self.board, company_id=self.company_id,
                              id="task-board")

        yield SlashMenu(id="slash-menu")

        with Horizontal(id="composer"):
            yield Static("❯ ", classes="composer-prompt")
            yield Input(placeholder="type a task, or / for commands...",
                        id="user-input")

    def on_mount(self) -> None:
        self.listen_to_agent()
        self.query_one(Input).focus()
        self.set_interval(0.1, self.tick_spinners)
        self._apply_responsive(self.size.width)
        self.call_later(self._show_landing)

    def on_resize(self, event) -> None:
        self._apply_responsive(event.size.width)

    def _apply_responsive(self, width: int) -> None:
        """Hide the widest header chips when the terminal cannot fit them,
        so the wordmark and the credits readout never get clipped."""
        screen = self.screen
        for name, present in (("narrow", width < 104), ("tiny", width < 64)):
            if present:
                screen.add_class(name)
            else:
                screen.remove_class(name)

    def _show_landing(self) -> None:
        """Show the OpenCode-style home: big wordmark, no conversation yet."""
        self.screen.add_class("landing")
        # clear children and mount the hero in one awaited worker so the old
        # #hero is fully removed before the new one is registered (mounting
        # while the prior removal is still queued raises DuplicateIds).
        self.run_worker(self._mount_landing(), group="landing", exclusive=True)

    async def _mount_landing(self) -> None:
        transcript = self.query_one("#transcript-area")
        await transcript.remove_children()
        # a turn may have started while we were clearing; don't resurrect the hero
        if not self.screen.has_class("landing"):
            return
        transcript.mount(Hero(compact=self.size.width < 60, id="hero"))

    def _enter_chat(self) -> None:
        """Leave the landing and let the conversation take the screen."""
        if not self.screen.has_class("landing"):
            return
        self.screen.remove_class("landing")
        for hero in self.query("#hero"):
            hero.remove()

    def on_unmount(self) -> None:
        self.listening = False

    # --------------------------------------------------------------- helpers
    def _model_chip(self) -> str:
        return f"● ⟨ {self.current_model} · {self.current_effort} ⟩"

    def refresh_credits(self) -> None:
        self.query_one("#credits-readout", CreditsReadout).refresh_readout()

    def refresh_task_board(self) -> None:
        self.query_one("#task-board", TaskBoardWidget).refresh_board(
            self.session_id)

    def _set_boundary_state(self, state: str) -> None:
        widget = self.query_one("#task-board", TaskBoardWidget)
        widget.boundary_state = state
        self.refresh_task_board()

    def mount_turn(self, *widgets, classes: str = "turn") -> None:
        transcript = self.query_one("#transcript-area")
        turn = Horizontal(*widgets, classes=classes)
        transcript.mount(turn)
        turn.scroll_visible()

    def show_system(self, text: str) -> None:
        self.mount_turn(Static("◆", classes="gutter-icon"),
                        Static(text, classes="agent-turn"))

    def tick_spinners(self) -> None:
        self.spinner_idx = (self.spinner_idx + 1) % len(SPINNER_FRAMES)
        frame = SPINNER_FRAMES[self.spinner_idx]
        for card in list(self.active_tools.values()):
            card.tick(frame)
        if self.agent_busy and self.current_agent_turn is not None:
            self._render_agent()

    def _render_agent(self) -> None:
        markdown = getattr(self, "agent_markdown", None)
        if markdown is None:
            return
        if self.agent_busy and not self.current_agent_text:
            frame = SPINNER_FRAMES[self.spinner_idx]
            markdown.update(f"[#00b8ff]{frame} {self.agent_busy_msg}[/]")
        else:
            markdown.update(RichMarkdown(
                self._format_agent_text(self.current_agent_text)))

    def _format_agent_text(self, text: str) -> str:
        if "<thought>" in text:
            def replacer(match):
                inner = match.group(1)
                return ("> **Thinking:**\n"
                        + "\n".join("> " + line for line in inner.split("\n")))
            return re.sub(r"<thought>(.*?)(?:</thought>|$)", replacer, text,
                          flags=re.DOTALL)
        return text

    # --------------------------------------------------------------- composer
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "user-input":
            self._refresh_slash(event.value)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        menu = self.query_one("#slash-menu", SlashMenu)

        # Enter accepts the highlighted palette row before it submits text.
        if menu.open:
            decision = menu.accept()
            if decision is not None:
                value, submit_now = decision
                event.input.value = ""
                if not submit_now:
                    event.input.value = value
                    event.input.cursor_position = len(value)
                    self._refresh_slash(value)
                    return
                user_text = value

        event.input.value = ""
        if not user_text:
            return
        await self._run_command_or_turn(user_text)

    async def _run_command_or_turn(self, user_text: str) -> None:
        self._close_slash()
        self._enter_chat()

        if user_text in ("/quit", "/exit"):
            self.exit()
            return

        if user_text.startswith("/model"):
            parts = user_text.split(None, 1)
            if len(parts) == 2 and parts[1].strip():
                self._choose_model(parts[1].strip())
            else:
                self._open_model_picker()
            return

        if user_text in ("/task", "/tasks"):
            self.action_toggle_tasks()
            return

        if user_text == "/complete":
            self.action_complete_task()
            return

        if user_text == "/help":
            self.action_help()
            return

        if user_text in ("/credits", "/dashboard"):
            self.action_credits()
            return

        if user_text in ("/clear", "/compact"):
            self.ui_queue.put(user_text)
            return

        if user_text.startswith("/"):
            self.show_system(
                f"unknown command `{user_text}` — press / for the list")
            return

        # ordinary turn: echo it, then hand it to the agent
        await self._mount_user_turn(user_text)
        self.ui_queue.put(user_text)

    # ------------------------------------------------------------ slash palette
    def _refresh_slash(self, value: str) -> None:
        menu = self.query_one("#slash-menu", SlashMenu)
        text = value.lstrip()
        if text.startswith("/model "):
            menu.show_models(text[len("/model "):])
        elif text.startswith("/") and " " not in text:
            menu.show_commands(text)
        else:
            menu.close()

    def _close_slash(self) -> None:
        self.query_one("#slash-menu", SlashMenu).close()

    async def on_key(self, event) -> None:
        """Drive the palette with the arrow keys while the composer is focused."""
        menu = self.query_one("#slash-menu", SlashMenu)
        if not menu.open:
            return
        if not self.query_one("#user-input", Input).has_focus:
            return
        if event.key == "down":
            menu.move(1)
            event.stop()
            event.prevent_default()
        elif event.key == "up":
            menu.move(-1)
            event.stop()
            event.prevent_default()

    def action_complete_slash(self) -> None:
        menu = self.query_one("#slash-menu", SlashMenu)
        if menu.open:
            completed = menu.complete()
            if completed is not None:
                inp = self.query_one("#user-input", Input)
                inp.value = completed
                inp.cursor_position = len(completed)
                self._refresh_slash(completed)
            return
        self.action_focus_next()

    async def _mount_user_turn(self, text: str) -> None:
        transcript = self.query_one("#transcript-area")
        turn = Horizontal(
            Static("❯", classes="gutter-icon user-icon"),
            Static(text, classes="user-turn"),
            classes="user-turn-container",
        )
        await transcript.mount(turn)
        turn.scroll_visible()

    def _open_model_picker(self) -> None:
        self._close_slash()
        from tui.model_picker import ModelPicker
        self.push_screen(ModelPicker(), self._on_model_picked)

    def _on_model_picked(self, selected_model: str) -> None:
        if selected_model:
            self._choose_model(selected_model)

    def _choose_model(self, model_id: str) -> None:
        self.current_model = model_id
        self.ui_queue.put(f"/model {model_id}")
        self.query_one("#model-display").update(self._model_chip())
        tier = self._tier_of(model_id)
        if tier is not None:
            self.show_model_card(tier)

    def _tier_of(self, model_id: str):
        for name, model in MODEL_TIERS:
            if model == model_id:
                return name
        if model_id.endswith(":free"):
            return "free"
        return None

    def show_model_card(self, tier: str) -> None:
        rows = [
            ("model",   tier),
            ("savings", f"{self.ledger.savings_pct:.0f}% vs Codex"),
            ("pass",    "57.9%"),
        ]
        label_w = max(len(label) for label, _ in rows)
        value_w = max(len(value) for _, value in rows)
        body_w = label_w + 3 + value_w                  # "label : value"
        title = " MODEL "
        top = "┌" + title + "─" * (body_w + 2 - len(title)) + "┐"
        bottom = "└" + "─" * (body_w + 2) + "┘"
        lines = [top]
        for label, value in rows:
            lines.append(f"│ {label:<{label_w}} : {value:<{value_w}} │")
        lines.append(bottom)
        self.mount_turn(Static("\n".join(lines), classes="model-card"))

    # --------------------------------------------------------------- bindings
    def action_toggle_tasks(self) -> None:
        board = self.query_one("#task-board")
        board.display = not board.display
        if board.display:
            self.refresh_task_board()

    def action_complete_task(self) -> None:
        self._close_slash()
        task = self.board.current
        if task is None:
            self.show_system("No active task to complete.")
            return
        self.push_screen(
            ConfirmModal(
                "Task complete?",
                f"{task.id} · {task.title}\n{task.bar} {task.progress}%\n"
                "Yes writes the savings report and closes the task.",
            ),
            self._on_complete_confirmed,
        )

    def _on_complete_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            self.show_system("Task continues.")
            return
        task = self.board.complete(saved_credits=self.ledger.saved)
        if task is None:
            return
        self._write_task_report(task)
        self.show_system(
            f"[✓] {task.id} completed — saved {task.saved_credits:.0f} credits "
            f"({self.ledger.savings_pct:.0f}%) vs Codex baseline · "
            f"{task.elapsed_hms()} · {task.pass_rate:.1f}% pass"
        )
        self.refresh_task_board()
        # a model switch only persists for the current task (§7)
        if self._tier_of(self.current_model) not in (None, "free"):
            self._choose_model(MODEL_TIERS[0][1])

    def _write_task_report(self, task) -> None:
        """Persist company/tasks/<id>.json when a company is assigned (§6)."""
        if not self.company_id:
            return
        try:
            folder = os.path.join("company", "tasks")
            os.makedirs(folder, exist_ok=True)
            payload = {
                "id": task.id,
                "project": task.project,
                "assignee": task.assignee,
                "title": task.title,
                "status": task.status,
                "progress": task.progress,
                "elapsed_sec": round(task.elapsed(), 1),
                "saved_credits": round(task.saved_credits, 2),
                "savings_pct": round(self.ledger.savings_pct, 1),
                "pass_rate": task.pass_rate,
            }
            with open(os.path.join(folder, f"{task.id}.json"), "w",
                      encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception as error:  # a report failure must never break the UI
            self.show_system(f"could not write task report: {error}")

    def action_cycle_model(self) -> None:
        names = [name for name, _ in MODEL_TIERS]
        current = self._tier_of(self.current_model) or "free"
        nxt = names[(names.index(current) + 1) % len(names)]
        self._choose_model(dict(MODEL_TIERS)[nxt])

    def action_help(self) -> None:
        self._close_slash()
        self.push_screen(HelpScreen())

    def action_credits(self) -> None:
        self._close_slash()
        self.push_screen(CreditsDashboard(self.ledger.snapshot()))

    def action_nav_mode(self) -> None:
        # the palette owns Escape while it is open
        if self.query_one("#slash-menu", SlashMenu).open:
            self._close_slash()
            return
        # blur the composer so the plain T/C/M/H shortcuts fire; Enter refocuses
        if self.query_one(Input).has_focus:
            self.set_focus(None)
            self.nav_mode = True
            self.show_system("Navigation mode — press Enter to return to the composer.")

    def action_focus_input(self) -> None:
        if not self.query_one(Input).has_focus:
            self.nav_mode = False
            self.query_one(Input).focus()

    # --------------------------------------------------------------- agent in
    @work(thread=True)
    def listen_to_agent(self) -> None:
        while self.listening:
            try:
                event = self.agent_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            except Exception:
                break

            if event is None:
                break

            if isinstance(event, dict):
                kind = event.get("type")
                if kind == "clear":
                    self.call_from_thread(self.clear_transcript)
                elif kind in ("init", "model_update"):
                    self.call_from_thread(self.update_model_display,
                                         event.get("model", ""))
                continue

            if isinstance(event, TurnStart):
                self.call_from_thread(self.start_agent_turn, event.user_prompt,
                                      event.session_id)
            elif isinstance(event, MessageDelta):
                self.call_from_thread(self.append_agent_text, event.content)
            elif isinstance(event, ToolStart):
                self.call_from_thread(self.start_tool, event.tool_call_id,
                                      event.tool_name, event.arguments)
            elif isinstance(event, ToolProgress):
                self.call_from_thread(self.progress_tool, event.tool_call_id,
                                      event.output_chunk)
            elif isinstance(event, ToolEnd):
                self.call_from_thread(self.end_tool, event.tool_call_id,
                                      event.result, event.success,
                                      event.duration_sec)
            elif isinstance(event, TurnEnd):
                self.call_from_thread(self.end_agent_turn,
                                      event.prompt_tokens,
                                      event.completion_tokens)
            elif isinstance(event, StatusUpdate):
                self.call_from_thread(self.handle_status_update,
                                      event.message, event.is_busy)
            elif isinstance(event, ErrorEvent):
                self.call_from_thread(self.handle_error,
                                      event.message, event.fatal)

    # ------------------------------------------------------------ transcript
    def clear_transcript(self) -> None:
        self._show_landing()

    def update_model_display(self, model_name: str) -> None:
        if model_name:
            self.current_model = model_name
            self.query_one("#model-display").update(self._model_chip())

    def start_agent_turn(self, user_prompt: str = "",
                         session_id: str = "") -> None:
        self._enter_chat()
        self.current_agent_text = ""
        if session_id:
            self.session_id = session_id
        self.board.begin(user_prompt)
        self._set_boundary_state(
            "enforced" if self.company_id else "active")
        self.refresh_task_board()

        self.agent_markdown = Static("", classes="agent-turn")
        self.agent_vertical = Vertical(self.agent_markdown, classes="turn-body")
        transcript = self.query_one("#transcript-area")
        self.current_agent_turn = Horizontal(
            Static("⬡", classes="gutter-icon agent-icon"),
            self.agent_vertical,
            classes="turn",
        )
        transcript.mount(self.current_agent_turn)
        self.current_agent_turn.scroll_visible()

        inp = self.query_one(Input)
        inp.disabled = True
        inp.placeholder = "Agent is working..."

    def append_agent_text(self, text: str) -> None:
        self.current_agent_text += text
        self._render_agent()

    def handle_status_update(self, message: str, is_busy: bool) -> None:
        if self.current_agent_turn is None and is_busy:
            self.start_agent_turn()
        self.agent_busy = is_busy
        self.agent_busy_msg = message or ""
        if getattr(self, "agent_markdown", None) is not None:
            if not is_busy and message.startswith("Error:"):
                self.current_agent_text += f"\n\n**{message}**"
            self._render_agent()

    def handle_error(self, message: str, fatal: bool) -> None:
        self.show_system(f"Error: {message}")
        if fatal:
            self.end_agent_turn()

    def start_tool(self, tool_id: str, name: str, args: str) -> None:
        if getattr(self, "agent_vertical", None) is None:
            return
        card = ToolCard(tool_id, name, args, classes="tool-card tool-active")
        card.raw_arguments = args
        self.active_tools[tool_id] = card
        self._mount_tool_card(card)
        self.board.note_tool()
        self.refresh_task_board()

    def _mount_tool_card(self, card: ToolCard, attempts: int = 0) -> None:
        """Mount a tool card once its turn container is attached.

        The turn's container is mounted asynchronously, so a ToolStart arriving
        in the same tick would otherwise hit "can't mount before mounted".
        """
        parent = getattr(self, "agent_vertical", None)
        if parent is not None and parent.is_attached:
            parent.mount(card)
            card.scroll_visible()
        elif attempts < 20:
            self.call_later(self._mount_tool_card, card, attempts + 1)
        else:
            self.query_one("#transcript-area").mount(card)

    def progress_tool(self, tool_id: str, chunk: str) -> None:
        card = self.active_tools.get(tool_id)
        if card is not None and chunk:
            card._args.update(chunk[-60:])

    def end_tool(self, tool_id: str, result: str, success: bool = True,
                 duration_sec: float = 0.0) -> None:
        card = self.active_tools.pop(tool_id, None)
        if card is None:
            return
        # keep the two notions of failure consistent (§12)
        failed = (not success) or str(result).startswith("Error:")
        card.finish(success=not failed, duration_sec=duration_sec, result=result)

        if is_boundary_violation(result):
            attempted = self._attempted_path(card, result)
            self._set_boundary_state("violation")
            self.push_screen(BoundaryModal(
                assigned=self.company_id or "unassigned",
                attempted=attempted,
                result=str(result).splitlines()[0] if result else "",
            ))

    def _attempted_path(self, card: ToolCard, result: str) -> str:
        match = re.search(r"'([^']+)'", str(result))
        if match:
            return match.group(1)
        raw = getattr(card, "raw_arguments", "")
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return "(unknown path)"
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, str):
                    return value
        return "(unknown path)"

    def end_agent_turn(self, prompt_tokens: int = 0,
                       completion_tokens: int = 0) -> None:
        self.ledger.record(prompt_tokens, completion_tokens)
        self.refresh_credits()
        self.board.note_step()
        self.board.finish_turn()
        self.refresh_task_board()

        self.agent_busy = False
        self.current_agent_turn = None
        self.current_agent_text = ""

        task = self.board.current
        if task is not None and task.progress >= 100 and task.tool_calls:
            self.show_system(
                f"{task.id} ready · {task.bar} 100% — press C to complete")

        inp = self.query_one(Input)
        inp.disabled = False
        inp.placeholder = "type a task, or / for commands..."
        inp.focus()


def create_gradient_text(text: str, start_color: str, end_color: str) -> Text:
    from textual.color import Color
    rich_text = Text()
    c1 = Color.parse(start_color)
    c2 = Color.parse(end_color)
    length = len(text)

    for i, char in enumerate(text):
        ratio = i / max(1, length - 1)
        r = int(c1.r + (c2.r - c1.r) * ratio)
        g = int(c1.g + (c2.g - c1.g) * ratio)
        b = int(c1.b + (c2.b - c1.b) * ratio)
        rich_text.append(char, style=f"rgb({r},{g},{b}) bold")
    return rich_text


def main() -> int:
    from tui.bridge import run_tui
    return run_tui()


if __name__ == "__main__":
    raise SystemExit(main())
