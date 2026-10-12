"""Slash-command palette for the TAMIAS composer.

When the composer's value starts with ``/`` the app shows a small suggestion
list directly above the input: matching commands first, then — once the value
is ``/model `` — the model catalogue. The widget holds only the current match
set and the highlighted row; ``tui/app.py`` owns the key handling and actually
runs the command.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual.widgets import Static

MAX_ROWS = 6


@dataclass(frozen=True)
class Command:
    trigger: str
    help: str
    takes_arg: bool = False


COMMANDS: tuple[Command, ...] = (
    Command("/model", "switch engine · pick a model or pass an id", True),
    Command("/task", "toggle the task & progress board"),
    Command("/complete", "complete the current task"),
    Command("/credits", "open the credits dashboard"),
    Command("/help", "show keys & commands"),
    Command("/clear", "clear the transcript"),
    Command("/quit", "exit TAMIAS"),
)


class SlashMenu(Static):
    """A keyboard-driven suggestion list shown above the composer."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode: str | None = None                      # "commands" | "models"
        self.rows: list[tuple[str, str, str, bool]] = []  # display, value, help, arg
        self.highlight = 0

    # ----------------------------------------------------------------- state
    @property
    def open(self) -> bool:
        return self.mode is not None

    def close(self) -> None:
        self.mode = None
        self.rows = []
        self.highlight = 0
        self.display = False
        self.update("")

    def show_commands(self, prefix: str) -> bool:
        query = prefix.lower()
        matches = [c for c in COMMANDS if c.trigger.startswith(query)]
        if not matches:
            self.close()
            return False
        self.mode = "commands"
        self.rows = [(c.trigger, c.trigger, c.help, c.takes_arg) for c in matches]
        self.highlight = 0
        self._paint()
        return True

    def show_models(self, partial: str) -> bool:
        from tui.model_picker import MODELS

        query = partial.strip().lower()
        matches = [(label, model) for label, model in MODELS
                   if not query or query in model.lower() or query in label.lower()]
        if not matches:
            self.close()
            return False
        self.mode = "models"
        self.rows = [(model, model, label, False) for label, model in matches]
        self.highlight = 0
        self._paint()
        return True

    def move(self, delta: int) -> None:
        if not self.open or not self.rows:
            return
        self.highlight = (self.highlight + delta) % len(self.rows)
        self._paint()

    def current(self) -> tuple[str, str, str, bool] | None:
        if not self.open or not self.rows:
            return None
        return self.rows[self.highlight]

    def accept(self) -> tuple[str, bool] | None:
        """Return ``(value, submit_now)`` for the highlighted row.

        Commands that take an argument fill the box (so the id can be typed);
        everything else runs immediately.
        """
        row = self.current()
        if row is None:
            return None
        _, value, _, takes_arg = row
        if self.mode == "models":
            return (f"/model {value}", True)
        if takes_arg:
            return (f"{value} ", False)
        return (value, True)

    def complete(self) -> str | None:
        """Tab behaviour: fill the highlighted row without submitting."""
        row = self.current()
        if row is None:
            return None
        _, value, _, takes_arg = row
        if self.mode == "models":
            return f"/model {value}"
        return f"{value} " if takes_arg else value

    # ---------------------------------------------------------------- render
    def _paint(self) -> None:
        heading = "COMMANDS" if self.mode == "commands" else "MODELS"
        text = Text()
        text.append(heading + "\n", style="bold #64748b")

        start = max(0, self.highlight - MAX_ROWS + 1)
        window = self.rows[start:start + MAX_ROWS]
        for offset, (display, _value, help_text, _arg) in enumerate(window):
            index = start + offset
            selected = index == self.highlight
            text.append("❯ " if selected else "  ",
                        style="#00ff9f" if selected else "#334155")
            if self.mode == "models":
                text.append(display + "\n",
                            style="bold #f8fafc" if selected else "#94a3b8")
            else:
                text.append(f"{display:<11}",
                            style="bold #f8fafc" if selected else "#e2e8f0")
                text.append("  " + help_text + "\n", style="#64748b")

        hidden = len(self.rows) - MAX_ROWS
        if hidden > 0:
            text.append(f"  +{hidden} more\n", style="#475569")

        self.display = True
        self.update(text)
