"""Reusable widgets for the TAMIAS TUI (docs/FRONTEND_REFERENCE.md §3).

Styling lives in the app's TCSS; these widgets only carry structure and the
small amount of state (a tool card's spinner, the task board's rows) that the
app ticks or refreshes.
"""

from __future__ import annotations

import re

from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from tui.credits import CreditsLedger
from tui.tasks import TaskBoard as TaskBoardModel

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

_SAFE_ID = re.compile(r"[^a-zA-Z0-9_-]")


def safe_id(raw: str) -> str:
    return _SAFE_ID.sub("-", str(raw)) or "tool"


class ToolCard(Vertical):
    """A tool call rendered as a card that transitions active → finished."""

    def __init__(self, tool_id: str, name: str, args: str, **kwargs):
        super().__init__(id=f"tool-{safe_id(tool_id)}", **kwargs)
        self.tool_id = tool_id
        self.tool_name = name
        self.running = True
        self._args_preview = args if len(args) <= 60 else args[:60] + "..."
        self._name = Static(name, classes="tool-name")
        self._status = Static(f"{SPINNER_FRAMES[0]} running...",
                              classes="tool-status active-spinner")
        self._args = Static(self._args_preview, classes="tool-args")

    def compose(self):
        with Horizontal(classes="tool-header"):
            yield self._name
            yield self._status
        yield self._args

    def tick(self, frame: str) -> None:
        if self.running:
            self._status.update(f"{frame} running...")

    def finish(self, success: bool, duration_sec: float, result: str = "") -> None:
        self.running = False
        if not success:
            text, color = "✗ failed", "#fca5a5"
        elif duration_sec:
            text, color = f"✓ {duration_sec:.1f}s", "#64748b"
        else:
            text, color = "✓ done", "#64748b"
        self._status.update(f"[{color}]{text}[/]")
        self._args.display = False
        self.remove_class("tool-active")
        self.add_class("tool-finished")


class CreditsReadout(Static):
    """The always-visible spend strip in the header bar (§5)."""

    def __init__(self, ledger: CreditsLedger, **kwargs):
        super().__init__(**kwargs)
        self.ledger = ledger
        self.refresh_readout()

    def refresh_readout(self) -> None:
        color = self.ledger.color()
        self.update(f"[{color}]{self.ledger.readout()}[/]")
        self.tooltip = ("provider-billed USD spent this session · "
                        "F3 for the dashboard")


class TaskBoardWidget(Static):
    """The toggleable task / progress panel (§6).

    Also carries the boundary status the UI contract requires be visible
    (§10 item 6): ``enforced`` when a company is assigned, ``active`` when the
    work is bounded only by the workspace, and ``violation`` after a blocked
    tool result — so the state is legible in the panel, not just the red modal.
    """

    def __init__(self, board: TaskBoardModel, company_id: str | None = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.board = board
        self.company_id = company_id
        self.boundary_state = "enforced" if company_id else "active"
        self.refresh_board()

    def refresh_board(self, session_id: str = "") -> None:
        lines = self.board.board_lines()
        lines.append("")
        if self.company_id:
            lines.append(f"boundary: {self.boundary_state} · "
                         f"company/work/{self.company_id}/")
        else:
            lines.append(f"boundary: {self.boundary_state} "
                         f"(no company assigned)")
        if session_id:
            lines.append(f"session: {session_id}")
        body = "\n".join(lines)
        self.update(f"[bold #00b8ff]TASK BOARD[/]\n{body}")
