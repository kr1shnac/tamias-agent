"""Brand assets for the TAMIAS landing screen.

The landing is the "home" shown before the first turn: a large gradient
wordmark with a tagline and command hints, like the opening frame of an
OpenCode-style session. It is pure presentation — it holds no state.
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

# ANSI-Shadow style block letters, six rows tall.
_LETTERS = {
    "T": [
        "████████╗",
        "╚══██╔══╝",
        "   ██║   ",
        "   ██║   ",
        "   ██║   ",
        "   ╚═╝   ",
    ],
    "A": [
        " █████╗ ",
        "██╔══██╗",
        "███████║",
        "██╔══██║",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
    "M": [
        "███╗   ███╗",
        "████╗ ████║",
        "██╔████╔██║",
        "██║╚██╔╝██║",
        "██║ ╚═╝ ██║",
        "╚═╝     ╚═╝",
    ],
    "I": [
        "██╗",
        "██║",
        "██║",
        "██║",
        "██║",
        "╚═╝",
    ],
    "S": [
        "███████╗",
        "██╔════╝",
        "███████╗",
        "╚════██║",
        "███████║",
        "╚══════╝",
    ],
}

WORDMARK = "TAMIAS"
TAGLINE = "bounded agentic coding · measured, never guessed"
HINT = "type a task and press Enter  ·  press / for commands"
QUICK = "/model    /task    /credits    /help"


def _art() -> list[str]:
    rows = [""] * 6
    for index, letter in enumerate(WORDMARK):
        glyph = _LETTERS[letter]
        for row in range(6):
            rows[row] += ("" if index == 0 else " ") + glyph[row]
    width = max(len(row) for row in rows)
    return [row.ljust(width) for row in rows]


ART = _art()
ART_WIDTH = len(ART[0]) if ART else 0


def hero_text(start: str = "#00b8ff", end: str = "#00ff9f") -> Text:
    """The landing block: gradient wordmark, tagline and hints.

    The gradient runs diagonally from `start` (top-left) to `end`
    (bottom-right) so the wordmark reads as one object rather than per-line
    colour bands. Text below the mark is centred against the mark's width by
    padding, so the block stays internally aligned at any terminal width.
    """
    from textual.color import Color

    c1 = Color.parse(start)
    c2 = Color.parse(end)
    rows = len(ART)
    span = max(1, rows + ART_WIDTH - 2)

    out = Text()
    for row, line in enumerate(ART):
        for col, char in enumerate(line):
            ratio = (row + col) / span
            r = int(c1.r + (c2.r - c1.r) * ratio)
            g = int(c1.g + (c2.g - c1.g) * ratio)
            b = int(c1.b + (c2.b - c1.b) * ratio)
            out.append(char, style=f"rgb({r},{g},{b})")
        out.append("\n")

    out.append("\n")
    out.append(TAGLINE.center(ART_WIDTH) + "\n", style="#94a3b8")
    out.append("\n")
    out.append(HINT.center(ART_WIDTH) + "\n", style="#64748b")
    out.append(QUICK.center(ART_WIDTH), style="#00b8ff")
    return out


def fallback_text() -> Text:
    """A compact one-line brand for very narrow terminals."""
    text = Text()
    text.append("TAMIAS", style="bold #00ff9f")
    text.append("  AGENT\n", style="bold #00b8ff")
    text.append(TAGLINE + "\n", style="#94a3b8")
    text.append(HINT, style="#64748b")
    return text


class Hero(Static):
    """The centred landing block shown before the first turn."""

    def __init__(self, compact: bool = False, **kwargs):
        super().__init__(fallback_text() if compact else hero_text(), **kwargs)
