"""Modal screens for the TAMIAS TUI.

Kept together so the dialog styling follows the same single theme as the main
screen (docs/FRONTEND_REFERENCE.md §1). Every screen uses only palette colours:
cyan ``#00b8ff`` for neutral dialogs, red ``#fca5a5`` for boundary violations,
green ``#00ff9f`` for savings.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from tui.credits import CreditsLedger

DIALOG_CSS = """
ConfirmModal, BoundaryModal, HelpScreen, CreditsDashboard {
    align: center middle;
    background: rgba(0, 0, 0, 0.7);
}
#confirm-dialog, #boundary-dialog, #help-dialog, #credits-dialog {
    width: 62;
    height: auto;
    max-height: 80%;
    padding: 1 2;
    background: #1a1a1a;
    border: round #00b8ff;
    color: #e2e8f0;
}
#boundary-dialog { border: round #fca5a5; }
#credits-dialog { border: round #00ff9f; width: 64; }
#confirm-title, #boundary-title, #help-title, #credits-title {
    text-style: bold;
    color: #00ff9f;
    margin-bottom: 1;
    content-align: center middle;
}
#boundary-title { color: #fca5a5; }
.modal-body { color: #e2e8f0; }
.modal-hint {
    color: #64748b;
    margin-top: 1;
    content-align: center middle;
}
.modal-row { color: #94a3b8; }
.modal-key { color: #00b8ff; text-style: bold; }
"""


class ConfirmModal(ModalScreen[bool]):
    """Yes/No confirmation. Dismisses with True (yes), False (no/cancel)."""

    CSS = DIALOG_CSS

    BINDINGS = [
        ("y", "yes", "Yes"),
        ("n", "no", "No"),
        ("escape", "no", "Cancel"),
    ]

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(self._title, id="confirm-title")
            yield Static(self._body, classes="modal-body")
            yield Static("\\[Y] yes   \\[N] no   \\[esc] cancel", classes="modal-hint")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class BoundaryModal(ModalScreen[None]):
    """The red BLOCKED dialog shown when a tool leaves company work (§8)."""

    CSS = DIALOG_CSS

    BINDINGS = [
        ("enter", "ok", "OK"),
        ("space", "ok", "OK"),
        ("escape", "ok", "OK"),
    ]

    def __init__(self, assigned: str, attempted: str, result: str) -> None:
        super().__init__()
        self._assigned = assigned
        self._attempted = attempted
        self._result = result

    def compose(self) -> ComposeResult:
        with Vertical(id="boundary-dialog"):
            yield Static("◆ BOUNDARY VIOLATION", id="boundary-title")
            yield Static("Outside company work area", classes="modal-body")
            yield Static(f"assigned : {self._assigned}", classes="modal-row")
            yield Static(f"attempted: {self._attempted}", classes="modal-row")
            yield Static("result   : BLOCKED", classes="modal-row")
            yield Static(self._result, classes="modal-hint")
            yield Static("\\[ OK ] → back to transcript", classes="modal-hint")

    def action_ok(self) -> None:
        self.dismiss(None)


class HelpScreen(ModalScreen[None]):
    """The `H` help overlay (§9)."""

    CSS = DIALOG_CSS

    BINDINGS = [("escape", "dismiss_help", "Close"),
                ("h", "dismiss_help", "Close")]

    ROWS = [
        ("↑ / ↓", "move between panels / history"),
        ("← / →", "switch sections (Task / Credits / Session)"),
        ("Enter", "activate focused panel / submit"),
        ("T", "toggle task & progress view"),
        ("C", "complete current task (confirmation modal)"),
        ("M", "cycle models (free → mid → premium)"),
        ("H", "this help overlay"),
        ("Q / Ctrl+C", "quit"),
        ("F1", "toggle fullscreen (hide chrome)"),
        ("F3", "credits dashboard"),
        ("/model", "open the model picker"),
        ("/task", "toggle the task board"),
        ("/complete", "complete the current task"),
        ("/quit", "exit"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static("TAMIAS — help", id="help-title")
            key_w = max(len(f"[{key}]") for key, _ in self.ROWS)
            for key, description in self.ROWS:
                label = f"[{key}]".ljust(key_w)
                yield Static(f"{label}  {description}", classes="modal-row",
                             markup=False)
            yield Static("while typing, use F1 · F3 · Ctrl+T or the /commands",
                         classes="modal-hint")

    def action_dismiss_help(self) -> None:
        self.dismiss(None)


class CreditsDashboard(ModalScreen[None]):
    """The `F3` credits dashboard (§5)."""

    CSS = DIALOG_CSS

    BINDINGS = [("escape", "dismiss_dash", "Close"),
                ("f3", "dismiss_dash", "Close")]

    USAGE = [("free", 65), ("mid", 25), ("premium", 10)]

    # inner width of #credits-dialog (64) minus 2 border and 2×2 padding
    CONTENT_WIDTH = 58

    def __init__(self, ledger: CreditsLedger) -> None:
        super().__init__()
        self._ledger = ledger

    def compose(self) -> ComposeResult:
        with Vertical(id="credits-dialog"):
            yield Static("◆ CREDITS DASHBOARD", id="credits-title")
            for label, value in self._ledger.dashboard_lines():
                yield Static(f"{label}: {value}", classes="modal-row")
            yield Static("", classes="modal-row")
            heading = "MODEL USAGE "
            yield Static(heading + "─" * (self.CONTENT_WIDTH - len(heading)),
                         classes="modal-row")
            for name, pct in self.USAGE:
                filled = int(round(20 * pct / 100))
                bar = "█" * filled + " " * (20 - filled)
                yield Static(f"{name:<8}{bar} {pct:>3}%", classes="modal-row")
            yield Static("\\[esc] close", classes="modal-hint")

    def action_dismiss_dash(self) -> None:
        self.dismiss(None)
