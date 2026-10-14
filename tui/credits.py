"""Spend accounting for the TAMIAS TUI (see docs/FRONTEND_REFERENCE.md §5).

The readout is always visible because a bounded agent must always show what it
has spent. Every figure here is **provider-billed USD**: the ledger records the
``cost`` the provider reports for each completed turn. It never derives a
number from token counts, never compares against an invented baseline, and
never guesses a budget. A turn whose cost the provider did not report is
counted as *unpriced*, never as zero -- the same rule the tamias proxy uses for
its own ledger, so the two stories cannot disagree.

("Credits" remains the product word for a company's spend allowance; a credit
is a USD unit, and the ledger stores nothing but USD.)

The maths is deliberately pure and Textual-free so it can be unit-tested and so
the view code only has to format it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --- palette (docs/FRONTEND_REFERENCE.md §1) ------------------------------
CYAN = "#00b8ff"
NEUTRAL = "#e8e8e8"


def _as_usd(value: object) -> float | None:
    """A reported cost as a finite, non-negative float, or ``None`` otherwise.

    Booleans are rejected even though ``bool`` is an ``int`` subclass, and a
    negative, NaN or infinite value is rejected too: a malformed cost must be
    treated as *unknown* so it counts as unpriced, never silently folded into
    the total.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        return None
    return number


@dataclass
class CreditsLedger:
    """Provider-billed USD for the session.

    There is deliberately no ``budget`` field. The per-key USD budget lives in
    the gateway; until the agent can read it (Phase 4) the UI must show real
    spend and nothing else rather than invent an allowance.
    """

    spent_usd: float = 0.0
    unpriced_steps: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    turns: int = 0

    def record(self, prompt_tokens: int = 0, completion_tokens: int = 0,
               cost_usd: object = None, unpriced_steps: int = 0) -> None:
        """Fold one completed turn into the ledger.

        ``cost_usd`` is the amount the provider reported for the turn (the sum
        of its steps), or ``None`` when it reported none. ``unpriced_steps`` is
        how many of the turn's API steps came back without a cost, so a partial
        turn is never presented as complete.
        """
        self.prompt_tokens += max(0, int(prompt_tokens or 0))
        self.completion_tokens += max(0, int(completion_tokens or 0))
        self.turns += 1
        unpriced = max(0, int(unpriced_steps or 0))
        cost = _as_usd(cost_usd)
        if cost is None:
            # a turn that reported no cost is itself at least one unpriced step
            unpriced = max(1, unpriced)
        else:
            self.spent_usd += cost
        self.unpriced_steps += unpriced

    def snapshot(self) -> "CreditsLedger":
        """A copy, for screens that must not mutate the live ledger."""
        return CreditsLedger(
            spent_usd=self.spent_usd,
            unpriced_steps=self.unpriced_steps,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            turns=self.turns,
        )

    # --- derived figures ---------------------------------------------------
    @property
    def has_data(self) -> bool:
        return self.turns > 0

    @property
    def fully_priced(self) -> bool:
        """True only when every step of every turn carried a provider cost."""
        return self.has_data and self.unpriced_steps == 0

    @property
    def tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    # --- presentation ------------------------------------------------------
    def readout(self) -> str:
        """The always-visible header string, e.g. ``$0.0123``.

        Before the first turn it reads as a zero with a hint. Once any step was
        unpriced the readout says so, so a partial total is never mistaken for
        the whole bill.
        """
        if not self.has_data:
            return "$0.0000 · no usage yet"
        text = f"${self.spent_usd:.4f}"
        if self.unpriced_steps:
            text += f" + {self.unpriced_steps} unpriced"
        return text

    def color(self) -> str:
        """Palette colour: neutral until the first turn, then cyan.

        There is no savings band any more; a colour cannot be honest about
        spend without a budget to compare it to.
        """
        return CYAN if self.has_data else NEUTRAL

    def dashboard_lines(self) -> list[tuple[str, str]]:
        """Rows for the F3 dashboard as ``(label, value)`` pairs (§5).

        Every value is derived from recorded usage; none is a literal. Icons
        are single-cell monochrome glyphs (no emoji), so the label field can be
        padded with plain ``str.ljust`` and the colon column lines up exactly.
        """
        pricing = ("provider-billed USD" if self.unpriced_steps == 0
                   else f"{self.unpriced_steps} steps unpriced")
        rows = [
            ("◈", "SPENT (USD)", f"${self.spent_usd:.4f}"),
            ("◇", "PRICING", pricing),
            ("✓", "TURNS", str(self.turns)),
            ("⬡", "TOKENS", f"{self.tokens:,}"),
            ("⇄", "PROMPT", f"{self.prompt_tokens:,}"),
            ("⇄", "COMPLETION", f"{self.completion_tokens:,}"),
        ]
        width = max(len(f"{icon} {name}") for icon, name, _ in rows)
        return [(f"{icon} {name}".ljust(width), value)
                for icon, name, value in rows]
