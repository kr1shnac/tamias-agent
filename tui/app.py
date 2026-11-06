import os
import queue
import re
import sys
import json
import threading
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Input
from rich.text import Text
from rich.markdown import Markdown as RichMarkdown

from tui.branding import Hero
from tui.events import (
    TurnStart, MessageDelta, ToolStart, ToolProgress, ToolEnd, ToolAsk,
    PlanAsk, TurnEnd, StatusUpdate, ErrorEvent, ModelSwitch, CostBreakdown,
)
from tui.credits import CreditsLedger, TIER_COLORS, TIER_LABELS
from tui.slash import SlashMenu
from tui.tasks import TaskBoard, is_boundary_violation
from tui.widgets import ToolCard, CreditsReadout, TaskBoardWidget, SPINNER_FRAMES
from tui.modals import (
    ConfirmModal, BoundaryModal, HelpScreen, CreditsDashboard,
    BoundaryCard, ReceiptModal, PlanCard, DossierCard, PlanContractModal,
    DiffModal,
)
from tui.policy_view import boundary_sections
from tui.receipt import TurnReceipt
from tui.plan import Plan, parse_plan
from tui.dossier import TurnDossier, INVESTIGATION_TOOLS

import model_catalog
import providers

# Every runnable catalog model, in catalog order (free first). Cycling `m`
# walks this list, so the switch card fires on every press. Paid models only
# appear when the operator has enabled paid spend (see providers.py). Falls back
# to three known ids if models/catalog.json is missing.
_FALLBACK_TIERS = [
    entry for entry in [
        ("free", "nvidia/nemotron-3.5-lightning:free"),
        ("mid", "openai/gpt-oss-20b"),
        ("premium", "z-ai/glm-4.7"),
    ] if providers.model_allowed(entry[1])
] or [("free", "nvidia/nemotron-3.5-lightning:free")]


def _build_tiers() -> list[tuple[str, str]]:
    return [(m.get("tier", "paid"), m["id"])
            for m in model_catalog.models()
            if providers.model_allowed(m["id"])]


# free → mid → premium (§7). The switch is user-initiated and scoped to the
# current task; completing a task resets the engine to free.
MODEL_TIERS = _build_tiers() or _FALLBACK_TIERS

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

/* --- Home screen (OpenCode-style) --- */
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

/* --- Model switch card --- */
.model-switch-card {
    height: auto;
    background: rgba(0, 184, 255, 0.05);
    border: round #00b8ff;
    border-top: round #00ff9f;
    padding: 0 1;
    margin: 1 0 1 4;
    width: 80%;
    color: #f8fafc;
}

.model-switch-header { layout: horizontal; height: 1; }
.model-switch-icon   { text-style: bold; width: 2; color: #00ff9f; }
.model-switch-text   { width: 1fr; }
.model-switch-details { color: #94a3b8; margin-top: 0; }

.cost-icon   { text-style: bold; width: 2; color: #fca5a5; }

/* --- Cost analysis card --- */
.cost-card {
    height: auto;
    background: rgba(255, 255, 255, 0.03);
    border: round rgba(255, 255, 255, 0.1);
    border-top: round #fca5a5;
    padding: 0 1;
    margin: 1 0 1 4;
    width: 80%;
    color: #f8fafc;
}

.cost-header { layout: horizontal; height: 1; }
.cost-icon   { text-style: bold; width: 2; color: #fca5a5; }
.cost-text   { width: 1fr; }
.cost-details { color: #94a3b8; margin-top: 0; }

/* --- Receipt line -------------------------------------------------------
   One calm line after a turn; the full proof opens with R or /receipt. */
.receipt-line {
    color: #64748b;
}
.receipt-icon {
    color: #00b8ff;
}

/* --- Work-surface lines ------------------------------------------------
   The plan and the evidence dossier are separate from the receipt: they
   answer "what is the agent trying to do?" and "what has it actually seen?" */
.plan-line {
    color: #64748b;
}
.plan-icon {
    color: #00b8ff;
}
.dossier-line {
    color: #64748b;
}
.dossier-icon {
    color: #00ff9f;
}

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

/* Spend: always visible, provider-billed USD (no savings band) (§5) */
#credits-readout {
    width: auto;
    content-align: right middle;
    padding: 0 2;
    text-style: bold;
}

#savings-readout {
    width: auto;
    content-align: right middle;
    padding: 0 2;
    text-style: bold;
    color: #00ff9f;
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
        ("b", "boundary", "Boundary"),
        ("r", "receipt", "Receipt"),
        ("p", "plan", "Plan"),
        ("d", "dossier", "Dossier"),
        ("z", "checkpoint", "Checkpoint"),
        ("v", "diff", "Diff"),
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
                 company_id: str | None = None, task_id: str | None = None,
                 assignee: str | None = None, ask_gate=None, plan_gate=None,
                 checkpoint_lookup=None):
        super().__init__()
        self.ui_queue = ui_queue
        self.agent_queue = agent_queue
        self.company_id = company_id
        self.ask_gate = ask_gate
        self.plan_gate = plan_gate
        self.checkpoint_lookup = checkpoint_lookup
        self.last_checkpoint_id = ""
        self.current_agent_turn = None
        self.current_agent_text = ""
        self.active_tools: dict[str, ToolCard] = {}
        self.agent_busy = False
        self.agent_busy_msg = ""
        self.boundary_seen = False   # did the fence stop the current turn?
        self.spinner_idx = 0
        self.nav_mode = False
        self.listening = True
        self.session_id = ""

        # One receipt per user turn. It is assembled from measured events, not
        # from the model's own summary, and only the last one is kept on screen.
        self.receipt_count = 0
        self.current_receipt: TurnReceipt | None = None
        self.last_receipt: TurnReceipt | None = None
        self.receipts: list[TurnReceipt] = []
        self._pending_prompt = ""

        # The work surfaces are also measured, not model-written summaries.
        # The plan comes from update_plan; the dossier from the evidence tools.
        self.current_plan: Plan | None = None
        self.last_plan: Plan | None = None
        self.current_dossier: TurnDossier | None = None
        self.last_dossier: TurnDossier | None = None

        self.current_model = os.environ.get(
            "AGENT_MODEL", "nvidia/nemotron-3.5-lightning:free")
        self.current_effort = os.environ.get("AGENT_EFFORT_POLICY", "auto")

        self.ledger = CreditsLedger()
        # The board shows exactly what the run was told (§10): the company is
        # the project area, the assignee is the person, and neither is invented
        # -- an unspecified field reads "unassigned", never a fake name.
        self.board = TaskBoard(project=company_id or "unassigned",
                               assignee=assignee or "unassigned",
                               task_id=task_id)

        # model switch tracking
        self._previous_model: str | None = None

    # ------------------------------------------------------------------ view
    def compose(self) -> ComposeResult:
        with Horizontal(id="header-bar"):
            yield Static(create_gradient_text("T A M I A S   A G E N T",
                                              "#00b8ff", "#00ff9f"),
                         id="wordmark")
            yield CreditsReadout(self.ledger, id="credits-readout")
            yield Static(self._premium_equiv_chip(), id="savings-readout")
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
        # a plain daemon thread, not a Textual thread worker: a worker lives on
        # the event loop's default executor, and asyncio.run()'s shutdown joins
        # that executor - so a listener still looping at teardown hangs the loop
        # close. A daemon thread is abandoned instead, and stops on unmount.
        self._listener = threading.Thread(
            target=self.listen_to_agent, daemon=True, name="tamias-listener")
        self._listener.start()
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
        tier_color = TIER_COLORS.get(self._tier_of(self.current_model) or "free", "#e8e8e8")
        return f"[{tier_color}]● ⟨ {self.current_model} · {self.current_effort} ⟩[/]"

    def _premium_equiv_chip(self) -> str:
        """Hypothetical list-price comparison, never called "saved"."""
        if not self.ledger.has_data:
            return "[#94a3b8]premium-equiv: $0.0000[/]"
        value = self.ledger.premium_equivalent_usd()
        color = "#00ff9f" if value > 0 else "#94a3b8"
        return f"[{color}]premium-equiv: ${value:.4f}[/]"

    def refresh_credits(self) -> None:
        self.query_one("#credits-readout", CreditsReadout).refresh_readout()
        self.query_one("#savings-readout").update(self._premium_equiv_chip())

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

    def show_model_switch(self, old_model: str, new_model: str,
                          old_tier: str, new_tier: str,
                          reason: str = "manual",
                          estimated_savings_usd: float = 0.0) -> None:
        """Show a prominent model switch announcement card in the transcript.

        Safe to call before the transcript is mounted (e.g. during tests): if
        the turn container isn't available yet the announcement is silently
        dropped.
        """
        try:
            old_color = TIER_COLORS.get(old_tier, "#e8e8e8")
            new_color = TIER_COLORS.get(new_tier, "#e8e8e8")
            tier_label_old = TIER_LABELS.get(old_tier, old_tier)
            tier_label_new = TIER_LABELS.get(new_tier, new_tier)

            reason_labels = {
                "manual": "manual switch",
                "cycle": "tier cycle",
                "policy": "policy allowlist",
                "auto-escalation": "auto-escalation",
            }
            reason_text = reason_labels.get(reason, reason)

            lines = [
                f"[{old_color}]◀ {old_model}[/]  →  [{new_color}]▶ {new_model}[/]",
                f"    [{old_color}]{tier_label_old}[/]  →  [{new_color}]{tier_label_new}[/]  "
                f"·  reason: {reason_text}",
            ]
            self.mount_turn(
                Static("🔄", classes="gutter-icon model-switch-icon"),
                Static("\n".join(lines), classes="model-switch-card"),
                classes="turn",
            )
        except Exception:
            # transcript not ready yet; the switch is still recorded in the ledger
            pass

    def show_cost_analysis(self) -> None:
        """Show a cost analysis card: actual spend and a hypothetical list-price
        comparison, with a real per-model breakdown.

        Safe to call before the transcript is mounted (e.g. during tests):
        if the turn container isn't available yet the announcement is silently
        dropped.
        """
        try:
            breakdown = self.ledger.model_breakdown()
            total_spent = self.ledger.spent_usd
            premium_equiv = self.ledger.premium_equivalent_usd()

            lines = [
                f"[bold #fca5a5]◈ COST ANALYSIS[/]",
                f"    total spent  : ${total_spent:.4f} (provider-billed)",
                f"    premium-equiv: ${premium_equiv:.4f} (hypothetical retail)",
                "",
                "    per model:",
            ]
            for mb in breakdown:
                tier_color = mb["tier_color"]
                lines.append(
                    f"      [{tier_color}]{mb['tier_label']}[/]  "
                    f"{mb['model_id'][:40]:<40}  "
                    f"spent: ${mb['spent_usd']:.4f}  "
                    f"premium-equiv: ${mb['paid_equivalent_usd']:.4f}  "
                    f"turns: {mb['turns']}  "
                    f"tokens: {mb['tokens']:,}"
                )
            if not breakdown:
                lines.append("      [#94a3b8]no model usage yet[/]")

            self.mount_turn(
                Static("💰", classes="gutter-icon cost-icon"),
                Static("\n".join(lines), classes="cost-card"),
                classes="turn",
            )
        except Exception:
            pass

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

        if user_text in ("/boundary", "/policy"):
            self.show_boundary_card()
            return

        if user_text in ("/receipt", "/receipts"):
            self.show_receipt()
            return

        if user_text in ("/plan", "/todos"):
            self.show_plan()
            return

        if user_text in ("/dossier", "/investigation"):
            self.show_dossier()
            return

        if user_text in ("/checkpoint", "/checkpoints", "/undo"):
            self.show_checkpoint()
            return

        if user_text in ("/diff", "/changes"):
            self.show_diff()
            return

        if user_text == "/help":
            self.action_help()
            return

        if user_text in ("/credits", "/dashboard"):
            self.action_credits()
            return

        if user_text.startswith("/cost"):
            self.show_cost_analysis()
            return

        if user_text in ("/clear", "/compact"):
            self.ui_queue.put(user_text)
            return

        if user_text.startswith("/"):
            self.show_system(
                f"unknown command `{user_text}` — press / for the list")
            return

        # ordinary turn: echo it, then hand it to the agent. The prompt is kept
        # so a refusal (which arrives without a turn_start) still gets a receipt
        # with the request it refused.
        await self._mount_user_turn(user_text)
        self._pending_prompt = user_text
        self.ui_queue.put(user_text)

    # ------------------------------------------------------------ slash palette
    def _refresh_slash(self, value: str) -> None:
        menu = self.query_one("#slash-menu", SlashMenu)
        text = value.lstrip()
        if text.startswith("/model "):
            menu.show_models(text[len("/model "):], allowed=self._model_allowlist())
        elif text.startswith("/") and " " not in text:
            menu.show_commands(text)
        else:
            menu.close()

    def _model_allowlist(self):
        """The active policy's model allowlist, when the core is loaded."""
        core = sys.modules.get("agent")

        if core is None:
            return []

        try:
            return core.allowed_models()
        except Exception:
            return []

    def _close_slash(self) -> None:
        self.query_one("#slash-menu", SlashMenu).close()

    def on_key(self, event) -> None:
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
        self.push_screen(ModelPicker(allowed=self._model_allowlist()),
                         self._on_model_picked)

    def _on_model_picked(self, selected_model: str) -> None:
        if selected_model:
            self._choose_model(selected_model)

    def _choose_model(self, model_id: str) -> None:
        allowed = self._model_allowlist()

        if allowed and model_id.strip() not in allowed:
            self.show_system(
                f"model `{model_id}` is outside this policy's model allowlist")
            return

        if not providers.model_allowed(model_id):
            self.show_system(providers.why_blocked(model_id))
            return

        old_model = self.current_model
        old_tier = self._tier_of(old_model) or "free"

        self.current_model = model_id
        self.ui_queue.put(f"/model {model_id}")
        self.query_one("#model-display").update(self._model_chip())
        tier = self._tier_of(model_id)
        if tier is not None:
            self.show_model_card(tier)

        # emit model switch announcement
        new_tier = tier or "free"
        if old_model != model_id:
            self.show_model_switch(
                old_model, model_id, old_tier, new_tier,
                reason="manual",
            )
            self.ledger.record_model_switch(
                old_model, model_id, old_tier, new_tier,
                reason="manual",
            )
            self.refresh_credits()

    def _tier_of(self, model_id: str):
        for name, model in MODEL_TIERS:
            if model == model_id:
                return name
        if model_id.endswith(":free"):
            return "free"
        return None

    def show_model_card(self, tier: str) -> None:
        try:
            rows = [
                ("model", self.current_model),
                ("tier", tier),
                ("spent", f"${self.ledger.spent_usd:.4f} this session"),
                ("premium-equiv", f"${self.ledger.premium_equivalent_usd():.4f} (hypothetical)"),
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
        except Exception:
            pass

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
                f"{task.id} · {task.title}\n"
                f"{task.steps} steps · {task.tool_calls} tools · "
                f"{task.elapsed_hms()}\n"
                "Yes writes the task report and closes the task.",
            ),
            self._on_complete_confirmed,
        )

    def confirm_tool_ask(self, tool_name: str, arguments: str,
                         reason: str) -> None:
        """Ask the human to allow a policy ask-gated tool call, once.

        This is a decision card, not a bare yes/no: what will run, why the
        policy asked, what it will touch, and what happens on either answer.
        The agent worker is blocked on the gate while this modal is up; the
        dismiss callback releases it. With no gate attached (or on cancel) the
        answer is no, so the call is denied, never silently run.
        """
        if self.current_receipt is not None:
            self.current_receipt.note_ask(tool_name, reason)

        details = [
            ("action", tool_name),
            ("why", reason or "policy ask"),
            ("arguments", arguments or "(none)"),
            ("scope", "this one call only"),
            ("if yes", "runs once, then is audited as ask-allowed"),
            ("if no", "the call is denied and audited as ask-denied"),
        ]

        def answered(allowed: bool | None) -> None:
            if self.ask_gate is not None:
                self.ask_gate.resolve(bool(allowed))
            self.show_system(
                f"{tool_name}: {'allowed once' if allowed else 'denied'}")

        self.push_screen(
            ConfirmModal(
                f"Allow tool '{tool_name}'?",
                "A human decision is required before this call can run.",
                details=details,
                hint="\\[Y] allow once   \\[N] deny   \\[esc] deny (fail closed)",
            ),
            answered,
        )

    def confirm_plan_contract(self, contract: dict | list[dict]) -> None:
        """Ask the human to sign the plan before any mutating tool may run.

        The worker is blocked in the plan gate while this modal is open. A
        dismissal, timeout or missing gate resolves to "denied", so the project
        is never changed on an unanswered contract.
        """
        if isinstance(contract, list):
            contract = {"todos": contract}
        todos = list(contract.get("todos", []))

        def answered(approved: bool | None) -> None:
            if self.plan_gate is not None:
                self.plan_gate.resolve(bool(approved))

            if self.current_receipt is not None:
                self.current_receipt.note_plan_decision(bool(approved))
                if not approved:
                    rows = [("decision", "denied by user"),
                            ("writes", "held — none ran")]
                    for number, todo in enumerate(todos[:10], 1):
                        status = str(todo.get("status", "pending"))
                        mark = {"completed": "[x]", "in_progress": "[~]"}
                        rows.append((f"{number} {mark.get(status, '[ ]')}",
                                     str(todo.get("content", ""))))
                    self.current_receipt.add_section("PLAN", rows)
                    self.current_receipt.add_risk(
                        "The human denied the plan; no writes ran.")

            self.show_system(
                "Plan signed — writes are now allowed."
                if approved else
                "Plan denied — no writes will run.")

        self.push_screen(PlanContractModal(contract), answered)

    def _on_complete_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            self.show_system("Task continues.")
            return
        task = self.board.complete(spent_usd=self.ledger.spent_usd)
        if task is None:
            return
        self._write_task_report(task)
        self.show_system(
            f"[✓] {task.id} completed · {task.elapsed_hms()} · "
            f"${self.ledger.spent_usd:.4f} spent this session (provider-billed USD)"
        )
        self.refresh_task_board()
        # a model switch only persists for the current task (§7)
        if self._tier_of(self.current_model) not in (None, "free"):
            old_model = self.current_model
            old_tier = self._tier_of(old_model) or "free"
            self._choose_model(MODEL_TIERS[0][1])
            new_tier = "free"
            self.show_model_switch(
                old_model, MODEL_TIERS[0][1], old_tier, new_tier,
                reason="task-reset",
            )

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
                "spent_usd": round(task.spent_usd, 6),
                "prompt_tokens": self.ledger.prompt_tokens,
                "completion_tokens": self.ledger.completion_tokens,
                "unpriced_steps": self.ledger.unpriced_steps,
            }
            with open(os.path.join(folder, f"{task.id}.json"), "w",
                      encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception as error:  # a report failure must never break the UI
            self.show_system(f"could not write task report: {error}")

    def action_cycle_model(self) -> None:
        """Step to the next model in the catalog.

        Cycles by *model*, not by tier name: the catalog has many free models,
        so tier names repeat and indexing by name would jump unpredictably.
        ``_choose_model`` owns the switch card and the ledger entry, so this
        method only decides which model is next.
        """
        allowed = self._model_allowlist()
        tiers = [(tier, model) for tier, model in MODEL_TIERS
                 if not allowed or model in allowed]

        if not tiers:
            self.show_system("no model is in this policy's model allowlist")
            return

        models = [model for _, model in tiers]
        try:
            index = models.index(self.current_model)
        except ValueError:
            index = -1

        self._choose_model(models[(index + 1) % len(models)])

    def action_help(self) -> None:
        self._close_slash()
        self.push_screen(HelpScreen())

    def action_credits(self) -> None:
        self._close_slash()
        self.push_screen(CreditsDashboard(self.ledger.snapshot()))

    # ------------------------------------------------------ accountability
    def _active_policy(self):
        """The live policy object, or None when the core is not loaded."""
        core = sys.modules.get("agent")
        if core is None:
            return None
        try:
            return core.active_policy()
        except Exception:
            return None

    def _policy_name(self) -> str:
        policy = self._active_policy()
        return str(getattr(policy, "name", "") or "") if policy else ""

    def _open_receipt(self, prompt: str) -> None:
        """Start a new receipt for this turn. Only ``end_agent_turn`` closes it."""
        self.receipt_count += 1
        self.current_receipt = TurnReceipt(
            number=self.receipt_count,
            prompt=prompt or "",
            session_id=self.session_id,
            policy_name=self._policy_name(),
        )
        self._pending_prompt = ""

    def action_boundary(self) -> None:
        self.show_boundary_card()

    def action_receipt(self) -> None:
        self.show_receipt()

    def action_plan(self) -> None:
        self.show_plan()

    def action_dossier(self) -> None:
        self.show_dossier()

    def action_checkpoint(self) -> None:
        self.show_checkpoint()

    def action_diff(self) -> None:
        self.show_diff()

    def show_diff(self) -> None:
        """Open the read-only diff for the last checkpoint, if it has one."""
        self._close_slash()
        checkpoint = self._last_checkpoint()
        if checkpoint is None:
            self.show_system(
                "No diff yet — a turn that writes a file creates a checkpoint "
                "with a reviewable diff.")
            return
        diffs = checkpoint.diff_files()
        if not diffs:
            self.show_system(
                f"Checkpoint {checkpoint.id} has no tracked textual changes.")
            return
        self.push_screen(DiffModal(checkpoint))

    def show_checkpoint(self) -> None:
        """Preview and, after confirmation, restore the last turn's files."""
        self._close_slash()
        checkpoint = self._last_checkpoint()
        if checkpoint is None:
            self.show_system(
                "No checkpoint yet — a turn that writes or runs a shell "
                "command creates one.")
            return
        if checkpoint.restored_at:
            self.show_system(
                f"Checkpoint {checkpoint.id} was already restored.")
            return
        if not checkpoint.files:
            self.show_system(
                f"Checkpoint {checkpoint.id} tracks no files; shell changes "
                "are not restorable.")
            return

        details = [
            ("checkpoint", checkpoint.id),
            ("prompt", checkpoint.prompt or "(not recorded)"),
            ("files", str(len(checkpoint.files))),
            ("shell", "ran — not captured" if checkpoint.shell_ran else "none"),
        ]
        details.extend(checkpoint.preview_rows()[:10])
        if len(checkpoint.files) > 10:
            details.append(("more", f"+{len(checkpoint.files) - 10} files"))

        def answered(confirmed: bool | None) -> None:
            if not confirmed:
                self.show_system("Restore cancelled; files were not touched.")
                return
            result = checkpoint.restore_files()
            if result.ok:
                self.last_checkpoint_id = ""
            if self.last_receipt is not None:
                self.last_receipt.note_restore(result)
            if result.ok:
                self.show_system(
                    f"Checkpoint {checkpoint.id} restored · {result.summary()}.")
            else:
                self.show_system(
                    f"Checkpoint {checkpoint.id} restore incomplete · "
                    f"{result.summary()} — open R for the failures.")

        self.push_screen(
            ConfirmModal(
                f"Restore {checkpoint.id}?",
                "This puts the tracked files back to their state before the "
                "turn. Current edits to those files will be overwritten or "
                "removed. Shell changes outside tracked files are not restored.",
                details=details,
                hint="\\[Y] restore files   \\[N] cancel",
            ),
            answered,
        )

    def _last_checkpoint(self):
        if not self.last_checkpoint_id or self.checkpoint_lookup is None:
            return None
        return self.checkpoint_lookup(self.last_checkpoint_id)

    def show_boundary_card(self) -> None:
        """Open the B card: the active fence in human language."""
        self._close_slash()
        policy = self._active_policy()
        name = "unbounded development mode" if policy is None else (
            getattr(policy, "name", "") or "active policy")
        company = (getattr(policy, "company", "") if policy else "") or \
            self.company_id or "unassigned"
        self.push_screen(BoundaryCard(
            boundary_sections(policy, company_id=self.company_id),
            name=name, company=company,
        ))

    def show_receipt(self, receipt: TurnReceipt | None = None) -> None:
        """Open the R card for the last turn, or say none exists yet."""
        self._close_slash()
        receipt = receipt or self.last_receipt
        if receipt is None:
            self.show_system("No receipt yet — run a turn first.")
            return
        self.push_screen(ReceiptModal(receipt))

    def show_plan(self, plan: Plan | None = None) -> None:
        """Open the P card for the current/last turn's published plan."""
        self._close_slash()
        plan = plan or self.current_plan or self.last_plan
        if plan is None:
            self.show_system(
                "No plan recorded yet — the agent publishes one with "
                "update_plan for multi-step work.")
            return
        self.push_screen(PlanCard(plan))

    def show_dossier(self, dossier: TurnDossier | None = None) -> None:
        """Open the D card for the evidence gathered in the current/last turn."""
        self._close_slash()
        dossier = dossier or self.current_dossier or self.last_dossier
        if dossier is None or not dossier.has_content:
            self.show_system(
                "No investigation dossier yet — the agent gathers one with "
                "investigate_target, trace_feature or analyze_structure.")
            return
        self.push_screen(DossierCard(dossier))

    def _review_title(self) -> str:
        task = self.board.current
        if task is not None and task.id:
            return f"{task.id} · {task.title}"
        return "Review this change"

    def _mount_work_line(self, icon: str, text: str,
                         line_class: str, icon_class: str) -> None:
        """One calm line for a measured work surface; P/D opens the details."""
        try:
            self.mount_turn(
                Static(icon, classes=f"gutter-icon {icon_class}"),
                Static(text, classes=line_class),
                classes="turn",
            )
        except Exception:
            pass

    def _mount_receipt_line(self, receipt: TurnReceipt) -> None:
        """One calm line after the turn; the proof itself opens with R."""
        self._mount_work_line(
            "▤", receipt.summary_line(), "receipt-line", "receipt-icon")

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
    def listen_to_agent(self) -> None:
        """Read agent events off the queue until the app stops.

        Runs on a plain daemon thread (started in on_mount), not a Textual
        thread worker: a worker lives on the event loop's default executor, and
        asyncio.run()'s shutdown joins that executor, so a listener still
        looping at teardown hangs the loop close. A daemon thread is abandoned.
        """
        while self.listening and self.is_running:
            try:
                event = self.agent_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            except Exception:
                break

            if event is None:
                break

            try:
                self._dispatch_agent_event(event)
            except RuntimeError:
                # the app stopped under us; nothing left to render
                break

    def _dispatch_agent_event(self, event) -> None:
        if isinstance(event, dict):
            kind = event.get("type")
            if kind == "clear":
                self.call_from_thread(self.clear_transcript)
            elif kind in ("init", "model_update"):
                self.call_from_thread(self.update_model_display,
                                     event.get("model", ""))
            return

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
        elif isinstance(event, ToolAsk):
            self.call_from_thread(self.confirm_tool_ask, event.tool_name,
                                  event.arguments, event.reason)
        elif isinstance(event, PlanAsk):
            self.call_from_thread(self.confirm_plan_contract, event.contract)
        elif isinstance(event, TurnEnd):
            self.call_from_thread(self.end_agent_turn,
                                  event.prompt_tokens,
                                  event.completion_tokens,
                                  event.cost_usd,
                                  event.unpriced_steps,
                                  event.model,
                                  event.tier,
                                  event.model_usage,
                                  event.checkpoint_id,
                                  event.checkpoint_files,
                                  event.checkpoint_shell,
                                  event.checkpoint_added,
                                  event.checkpoint_removed,
                                  event.checkpoint_diff_paths,
                                  event.checkpoint_diff_truncated)
        elif isinstance(event, ModelSwitch):
            self.call_from_thread(self._handle_model_switch_event, event)
        elif isinstance(event, CostBreakdown):
            self.call_from_thread(self._handle_cost_breakdown, event)
        elif isinstance(event, StatusUpdate):
            self.call_from_thread(self.handle_status_update,
                                  event.message, event.is_busy)
        elif isinstance(event, ErrorEvent):
            self.call_from_thread(self.handle_error,
                                  event.message, event.fatal)

    def _handle_model_switch_event(self, event: ModelSwitch) -> None:
        """Handle a model switch event from the agent core."""
        if self.current_receipt is not None:
            self.current_receipt.note_model_switch(
                event.old_model, event.new_model,
                event.old_tier, event.new_tier, event.reason)
        self.update_model_display(event.new_model)
        self.show_model_switch(
            event.old_model, event.new_model,
            event.old_tier, event.new_tier,
            reason=event.reason,
            estimated_savings_usd=event.estimated_savings_usd,
        )
        self.ledger.record_model_switch(
            event.old_model, event.new_model,
            event.old_tier, event.new_tier,
            reason=event.reason,
            estimated_savings_usd=event.estimated_savings_usd,
        )
        self.refresh_credits()

    def _handle_cost_breakdown(self, event: CostBreakdown) -> None:
        """Handle a cost breakdown event - show the analysis card."""
        self.show_cost_analysis()

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
        self.boundary_seen = False
        if session_id:
            self.session_id = session_id

        # a new turn opens a new receipt; it is closed by end_agent_turn
        self.current_plan = None
        self.current_dossier = None
        self._open_receipt(user_prompt or self._pending_prompt)

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
        if not is_busy:
            # A use-case refusal arrives before any turn was opened (the core
            # refuses before it emits turn_start), so the receipt has to be
            # opened here or the refused turn would have no accountable record.
            # The same is true for an error that kills the turn before
            # turn_start: keep the prompt so the receipt can name it.
            needs_receipt = is_boundary_violation(message) or (
                message.startswith("Error:") and self._pending_prompt)
            if self.current_receipt is None and needs_receipt:
                self._open_receipt(self._pending_prompt)
            if self.current_receipt is not None:
                if is_boundary_violation(message):
                    self.current_receipt.note_boundary(message)
                elif message.startswith("Error: plan contract"):
                    if not self.current_receipt.plan_denied:
                        self.current_receipt.note_plan_block(message)
                elif message.startswith("Error:"):
                    self.current_receipt.note_error(message)
        self.agent_busy = is_busy
        self.agent_busy_msg = message or ""
        if getattr(self, "agent_markdown", None) is not None:
            if not is_busy and message.startswith("Error:"):
                self.current_agent_text += f"\n\n**{message}**"
            self._render_agent()

        # a use-case scope refusal is a boundary event: show it the same way a
        # blocked tool call is shown, so "no, that is not what this agent is
        # for" is never silent. Only one modal per turn: a mid-turn block was
        # already surfaced by the tool card that hit the fence.
        if not is_busy and is_boundary_violation(message):
            first = not self.boundary_seen
            # a mid-turn block means the task stopped short of completion; a
            # scope refusal arrives before a turn starts, so it flags nothing
            if self.current_agent_turn is not None:
                self.boundary_seen = True
            self._set_boundary_state("violation")
            if first:
                self.push_screen(BoundaryModal(
                    assigned=self.company_id or "unassigned",
                    attempted="(off-topic request)",
                    result=message,
                    headline="Bounded to your assigned work — this agent is "
                             "for the to-do app and cannot work on other "
                             "projects",
                    note="refused before any model call · 0 tokens · $0.0000",
                ))

    def handle_error(self, message: str, fatal: bool) -> None:
        self.show_system(f"Error: {message}")
        if self.current_receipt is None and self._pending_prompt:
            self._open_receipt(self._pending_prompt)
        if self.current_receipt is not None:
            self.current_receipt.note_error(message)
        if fatal:
            self.end_agent_turn()

    def start_tool(self, tool_id: str, name: str, args: str) -> None:
        if getattr(self, "agent_vertical", None) is None:
            return
        card = ToolCard(tool_id, name, args, classes="tool-card tool-active")
        card.raw_arguments = args
        self.active_tools[tool_id] = card
        if self.current_receipt is not None:
            self.current_receipt.note_tool_start(tool_id, name, args)
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
        # A plan-level denial emits ToolEnd without a ToolStart, so the receipt
        # must still see it even when there is no card to finish.
        if self.current_receipt is not None:
            self.current_receipt.note_tool_end(
                tool_id, getattr(card, "tool_name", "") if card else "",
                result, success=success, duration_sec=duration_sec)
        if card is None:
            return
        # keep the two notions of failure consistent (§12)
        failed = (not success) or str(result).startswith("Error:")
        card.finish(success=not failed, duration_sec=duration_sec, result=result)

        if not failed:
            self._record_work_surface(card, result)

        if is_boundary_violation(result):
            self.boundary_seen = True
            attempted = self._attempted_path(card, result)
            self._set_boundary_state("violation")
            self.push_screen(BoundaryModal(
                assigned=self.company_id or "unassigned",
                attempted=attempted,
                result=str(result).splitlines()[0] if result else "",
            ))

    def _record_work_surface(self, card: ToolCard, result: str) -> None:
        """Turn measured tool output into the P/D work surfaces.

        This only reads deterministic text the tools already returned. A model
        summary is never substituted for a plan step or an evidence line.
        """
        try:
            tool_name = getattr(card, "tool_name", "")
            if tool_name == "update_plan":
                plan = parse_plan(result)
                if plan is not None:
                    plan.gate_active = self.plan_gate is not None
                    self.current_plan = plan
                return
            if tool_name in INVESTIGATION_TOOLS:
                if self.current_dossier is None:
                    self.current_dossier = TurnDossier()
                self.current_dossier.add(tool_name, result)
        except Exception:
            # a malformed tool result must never kill the turn; the receipt and
            # the tool card still hold the raw result
            pass

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
                       completion_tokens: int = 0,
                       cost_usd: float | None = None,
                       unpriced_steps: int = 0,
                       model: str = "",
                       tier: str = "",
                       model_usage: dict | None = None,
                       checkpoint_id: str = "",
                       checkpoint_files: int = 0,
                       checkpoint_shell: bool = False,
                       checkpoint_added: int = 0,
                       checkpoint_removed: int = 0,
                       checkpoint_diff_paths: int = 0,
                       checkpoint_diff_truncated: bool = False) -> None:
        self.ledger.record(prompt_tokens, completion_tokens, cost_usd,
                           unpriced_steps, model=model, tier=tier,
                           model_usage=model_usage)
        self.refresh_credits()
        self.board.note_step()

        # close the turn's receipt before the transcript resets; it is the
        # accountable record of exactly what this turn did and spent
        plan = self.current_plan
        dossier = self.current_dossier
        if plan is not None:
            self.last_plan = plan
        if dossier is not None and dossier.has_content:
            self.last_dossier = dossier
        else:
            dossier = None

        receipt = self.current_receipt
        if receipt is None and self._pending_prompt:
            # a TurnEnd can arrive without a TurnStart (early failure); the
            # prompt is still the request the user made, so keep the receipt
            self._open_receipt(self._pending_prompt)
            receipt = self.current_receipt
        if checkpoint_id:
            self.last_checkpoint_id = str(checkpoint_id)
        if receipt is not None:
            if self.boundary_seen:
                receipt.boundary = True
            if checkpoint_id:
                receipt.note_checkpoint(
                    checkpoint_id, checkpoint_files, checkpoint_shell,
                    checkpoint_added, checkpoint_removed,
                    checkpoint_diff_paths, checkpoint_diff_truncated)
            if plan is not None:
                receipt.add_section("PLAN", plan.receipt_rows())
                if plan.signed:
                    receipt.plan_approved = True
                else:
                    receipt.add_risk(
                        "The plan is unsigned; it did not gate any write.")
            if dossier is not None:
                receipt.add_section("INVESTIGATION", dossier.receipt_rows())
                receipt.add_risk(
                    "Investigation evidence is static; runtime behavior was "
                    "not observed.")
                if dossier.unknowns:
                    count = len(dossier.unknowns)
                    noun = "unknown" if count == 1 else "unknowns"
                    receipt.add_risk(
                        f"Investigation left {count} {noun}; review the "
                        f"dossier before acting.")
            receipt.finish(prompt_tokens, completion_tokens, cost_usd,
                           unpriced_steps, model=model, tier=tier)
            self.last_receipt = receipt
            self.receipts.append(receipt)
            self.current_receipt = None

        if self.boundary_seen:
            # the fence stopped this turn: it is not "ready to complete" and
            # must not read as 100% (the false "ready" this fixes)
            self.board.block()
            self._set_boundary_state("violation")
            self.show_system("⛔ Blocked — the boundary stopped this turn; "
                             "nothing was completed.")
        else:
            self.board.finish_turn()

        self.refresh_task_board()

        self.agent_busy = False
        self.current_agent_turn = None
        self.current_agent_text = ""

        task = self.board.current
        if (not self.boundary_seen and task is not None
                and task.status == "ready" and task.tool_calls):
            self.show_system(
                f"{task.id} ready to review · {task.steps} steps · "
                f"{task.tool_calls} tools — press C to complete")

        if plan is not None:
            self._mount_work_line(
                "▦", plan.summary_line(), "plan-line", "plan-icon")
        if dossier is not None:
            self._mount_work_line(
                "▣", dossier.summary_line(), "dossier-line", "dossier-icon")
        if receipt is not None:
            self._mount_receipt_line(receipt)

        self.current_plan = None
        self.current_dossier = None
        self.boundary_seen = False

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