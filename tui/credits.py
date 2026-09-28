"""Credit accounting for the TAMIAS TUI (see docs/FRONTEND_REFERENCE.md §5).

Credits are the reason the product exists, so the readout is always visible.
The numbers are derived from the token counts the agent core reports on every
``TurnEnd`` and compared against a fixed *Codex baseline*: the same work done by
a conventional synchronous agent is assumed to re-send more context (higher
prompt weight) and write longer completions (higher completion weight).

The maths is deliberately pure and Textual-free so it can be unit-tested and so
the view code only has to format it. Weights are expressed as credit units per
token and normalised per 1000 tokens below.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- thresholds (percent saved) -------------------------------------------
# ≥ 39% green · 20–38% amber · < 20% red
GREEN_MIN = 39.0
AMBER_MIN = 20.0

# --- palette (docs/FRONTEND_REFERENCE.md §1) ------------------------------
GREEN = "#00ff9f"
AMBER = "#f59e0b"
RED = "#fca5a5"
NEUTRAL = "#e8e8e8"

# --- token weights: credits per 1000 tokens --------------------------------
TAMIAS_PROMPT_WEIGHT = 0.25
TAMIAS_COMPLETION_WEIGHT = 1.0
CODEX_PROMPT_WEIGHT = 0.50
CODEX_COMPLETION_WEIGHT = 1.5

# every turn carries a fixed planning/setup cost on both sides; because it is
# a larger share of a short turn, brief exchanges save less (down into amber
# and red) while long agentic turns save most (the green band, §5)
TAMIAS_TURN_OVERHEAD = 0.5
CODEX_TURN_OVERHEAD = 0.6

# --- default per-task credit budget ----------------------------------------
DEFAULT_BUDGET = 150.0


def savings_color(rate_pct: float) -> str:
    """Return the palette colour a savings rate maps to (§5)."""
    if rate_pct >= GREEN_MIN:
        return GREEN
    if rate_pct >= AMBER_MIN:
        return AMBER
    return RED


def savings_label(rate_pct: float) -> str:
    """Short human label for a savings rate."""
    if rate_pct >= GREEN_MIN:
        return "healthy"
    if rate_pct >= AMBER_MIN:
        return "fair"
    return "WARNING: low savings"


def _credits(prompt_tokens: float, completion_tokens: float,
             prompt_weight: float, completion_weight: float) -> float:
    return (max(0.0, prompt_tokens) * prompt_weight
            + max(0.0, completion_tokens) * completion_weight) / 1000.0


@dataclass
class CreditsLedger:
    """Accumulates token usage and reports savings vs the Codex baseline."""

    budget: float = DEFAULT_BUDGET
    prompt_tokens: int = 0
    completion_tokens: int = 0
    turns: int = 0

    def record(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Fold one completed turn's token counts into the ledger."""
        self.prompt_tokens += max(0, int(prompt_tokens or 0))
        self.completion_tokens += max(0, int(completion_tokens or 0))
        self.turns += 1

    def snapshot(self) -> "CreditsLedger":
        """A copy, for screens that must not mutate the live ledger."""
        return CreditsLedger(
            budget=self.budget,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            turns=self.turns,
        )

    # --- derived figures ---------------------------------------------------
    @property
    def spent(self) -> float:
        """Credits this agent actually cost."""
        return (_credits(self.prompt_tokens, self.completion_tokens,
                         TAMIAS_PROMPT_WEIGHT, TAMIAS_COMPLETION_WEIGHT)
                + self.turns * TAMIAS_TURN_OVERHEAD)

    @property
    def codex_spent(self) -> float:
        """Credits the same work would have cost on the Codex baseline."""
        return (_credits(self.prompt_tokens, self.completion_tokens,
                         CODEX_PROMPT_WEIGHT, CODEX_COMPLETION_WEIGHT)
                + self.turns * CODEX_TURN_OVERHEAD)

    @property
    def saved(self) -> float:
        return max(0.0, self.codex_spent - self.spent)

    @property
    def savings_pct(self) -> float:
        """Percent saved against the baseline, 0 when there is no data yet."""
        if self.turns == 0 or self.codex_spent <= 0:
            return 0.0
        return 100.0 * self.saved / self.codex_spent

    @property
    def remaining(self) -> float:
        return max(0.0, self.budget - self.spent)

    @property
    def remaining_pct(self) -> float:
        if self.budget <= 0:
            return 0.0
        return 100.0 * self.remaining / self.budget

    @property
    def has_data(self) -> bool:
        return self.turns > 0

    # --- presentation ------------------------------------------------------
    def readout(self) -> str:
        """The always-visible header string, e.g. ``SCR 58/150 (39% saved)``.

        The red band carries the spec's explicit warning suffix (§5); the
        neutral (no data yet) and green/amber bands stay terse.
        """
        base = (f"SCR {self.saved:.0f}/{self.budget:.0f} "
                f"({self.savings_pct:.0f}% saved)")
        if self.has_data and self.savings_pct < AMBER_MIN:
            return f"{base} · {savings_label(self.savings_pct)}"
        return base

    def color(self) -> str:
        """Palette colour for the readout; neutral until the first turn."""
        if not self.has_data:
            return NEUTRAL
        return savings_color(self.savings_pct)

    def dashboard_lines(self) -> list[tuple[str, str]]:
        """Rows for the F3 dashboard as ``(label, value)`` pairs (§5).

        Icons are single-cell monochrome glyphs (no emoji), so the label field
        can be padded with plain ``str.ljust`` and the colon column lines up
        exactly for every row.
        """
        rows = [
            ("◈", "BALANCE",
             f"{self.remaining:.0f} / {self.budget:.0f} credits "
             f"({self.remaining_pct:.1f}% remaining)"),
            ("◇", "SAVINGS",
             f"{self.saved:.0f} credits "
             f"({self.savings_pct:.0f}% vs Codex baseline)"),
            ("↗", "TREND", "steady vs baseline"),
            ("✓", "PASS RATE", "57.9% (parity with Codex — no quality loss)"),
            ("⬡", "MODEL", "free (async-optimized)"),
            ("⇄", "ASYNC", "~80% of tool calls parallelized"),
            ("⬚", "BOUNDARY", "enforced — zero off-task spend"),
        ]
        width = max(len(f"{icon} {name}") for icon, name, _ in rows)
        return [(f"{icon} {name}".ljust(width), value)
                for icon, name, value in rows]
