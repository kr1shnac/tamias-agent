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
from dataclasses import dataclass, field
from typing import Optional


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


# --- model tier pricing reference -----------------------------------------
# Free models bill $0.00; paid models bill at real OpenRouter rates.
# These are the *retail* list prices used only for "money saved" analysis --
# they are clearly labelled as hypothetical and never used as a measurement.
TIER_PRICING: dict[str, dict[str, float]] = {
    "free":   {"prompt_per_1k": 0.0000, "completion_per_1k": 0.0000},
    "mid":    {"prompt_per_1k": 0.0030, "completion_per_1k": 0.0150},
    "premium":{"prompt_per_1k": 0.0150, "completion_per_1k": 0.0750},
}

TIER_LABELS: dict[str, str] = {
    "free":   "Free ($0.00)",
    "mid":    "Mid ($0.003/1k prompt, $0.015/1k completion)",
    "premium":"Premium ($0.015/1k prompt, $0.075/1k completion)",
}

TIER_COLORS: dict[str, str] = {
    "free":   "#00ff9f",   # green
    "mid":    "#00b8ff",   # cyan
    "premium":"#fca5a5",   # red
}


@dataclass
class ModelSpend:
    """Spend and usage for one model tier."""
    model_id: str
    tier: str
    turns: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    spent_usd: float = 0.0
    unpriced_steps: int = 0

    def estimated_paid_cost_usd(self) -> float:
        """What this usage *would* cost on this model's retail rate."""
        rate = TIER_PRICING.get(self.tier, TIER_PRICING["free"])
        prompt_cost = (self.prompt_tokens / 1000) * rate["prompt_per_1k"]
        completion_cost = (self.completion_tokens / 1000) * rate["completion_per_1k"]
        return prompt_cost + completion_cost

    @property
    def tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


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
    model_spend: dict[str, ModelSpend] = field(default_factory=dict)
    model_switches: list[dict] = field(default_factory=list)

    # --- recording -----------------------------------------------------------
    def record(self, prompt_tokens: int = 0, completion_tokens: int = 0,
               cost_usd: object = None, unpriced_steps: int = 0,
               model: str = "", tier: str = "",
               model_usage: dict | None = None) -> None:
        """Fold one completed turn into the ledger.

        ``cost_usd`` is the amount the provider reported for the turn (the sum
        of its steps), or ``None`` when it reported none. ``unpriced_steps`` is
        how many of the turn's API steps came back without a cost, so a partial
        turn is never presented as complete.

        ``model_usage`` is the per-model partition of the same turn, produced
        by the agent's ``account_usage``. When present it is authoritative for
        the breakdown; otherwise the single ``model`` is used as a fallback.
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

        # per-model tracking
        if model_usage:
            for model_id, usage in model_usage.items():
                if not isinstance(usage, dict):
                    continue
                ms = self.model_spend.get(model_id)
                if ms is None:
                    ms = ModelSpend(
                        model_id=model_id,
                        tier=str(usage.get("tier") or "free"),
                    )
                    self.model_spend[model_id] = ms
                elif usage.get("tier"):
                    ms.tier = str(usage["tier"])

                ms.turns += 1
                ms.prompt_tokens += max(0, int(usage.get("prompt_tokens", 0) or 0))
                ms.completion_tokens += max(0, int(usage.get("completion_tokens", 0) or 0))
                step_cost = _as_usd(usage.get("cost_usd"))
                if step_cost is not None:
                    ms.spent_usd += step_cost
                ms.unpriced_steps += max(0, int(usage.get("unpriced_steps", 0) or 0))
        elif model:
            key = model
            if key not in self.model_spend:
                self.model_spend[key] = ModelSpend(model_id=model, tier=tier or "free")
            ms = self.model_spend[key]
            ms.turns += 1
            ms.prompt_tokens += max(0, int(prompt_tokens or 0))
            ms.completion_tokens += max(0, int(completion_tokens or 0))
            c = _as_usd(cost_usd)
            if c is not None:
                ms.spent_usd += c
            ms.unpriced_steps += max(0, int(unpriced_steps or 0))

    def record_model_switch(self, old_model: str, new_model: str,
                            old_tier: str, new_tier: str,
                            reason: str = "manual",
                            estimated_savings_usd: float = 0.0) -> None:
        """Record a model switch event for the audit trail."""
        self.model_switches.append({
            "old_model": old_model,
            "new_model": new_model,
            "old_tier": old_tier,
            "new_tier": new_tier,
            "reason": reason,
            "estimated_savings_usd": estimated_savings_usd,
        })

    def snapshot(self) -> "CreditsLedger":
        """A copy, for screens that must not mutate the live ledger."""
        return CreditsLedger(
            spent_usd=self.spent_usd,
            unpriced_steps=self.unpriced_steps,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            turns=self.turns,
            model_spend=dict(self.model_spend),
            model_switches=list(self.model_switches),
        )

    # --- derived figures ----------------------------------------------------
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

    def estimated_paid_cost_usd(self) -> float:
        """What the recorded usage would cost at each model's retail rate."""
        total = 0.0
        for ms in self.model_spend.values():
            total += ms.estimated_paid_cost_usd()
        return total

    def premium_equivalent_usd(self) -> float:
        """What the recorded tokens would cost at the premium list rate.

        This is a hypothetical retail comparison, not a measured saving: the
        run never bought those tokens at that rate. Every surface that shows it
        must say "premium-equivalent" and "hypothetical".
        """
        premium_rate = TIER_PRICING["premium"]
        return (
            (self.prompt_tokens / 1000) * premium_rate["prompt_per_1k"] +
            (self.completion_tokens / 1000) * premium_rate["completion_per_1k"]
        )

    def retail_delta_usd(self) -> float:
        """Premium-equivalent minus actual spend; hypothetical by definition."""
        return max(0.0, self.premium_equivalent_usd() - self.spent_usd)

    def estimated_savings_usd(self) -> float:
        """Deprecated alias for :meth:`retail_delta_usd`.

        Kept so older callers keep working; new display code must not use the
        word "saved" for this figure.
        """
        return self.retail_delta_usd()

    def model_breakdown(self) -> list[dict]:
        """Per-model breakdown for dashboard display."""
        result = []
        for model_id, ms in self.model_spend.items():
            tier_color = TIER_COLORS.get(ms.tier, "#e8e8e8")
            tier_label = TIER_LABELS.get(ms.tier, ms.tier)
            actual = ms.spent_usd
            paid_equiv = ms.estimated_paid_cost_usd()
            result.append({
                "model_id": model_id,
                "tier": ms.tier,
                "tier_label": tier_label,
                "tier_color": tier_color,
                "turns": ms.turns,
                "tokens": ms.tokens,
                "prompt_tokens": ms.prompt_tokens,
                "completion_tokens": ms.completion_tokens,
                "spent_usd": actual,
                "paid_equivalent_usd": paid_equiv,
                # legacy key; display calls it "premium-equivalent"
                "saved_usd": paid_equiv,
                "unpriced_steps": ms.unpriced_steps,
            })
        # sort by spend descending
        result.sort(key=lambda x: x["spent_usd"], reverse=True)
        return result

    # --- presentation --------------------------------------------------------
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

    def premium_equivalent_readout(self) -> str:
        """A short hypothetical list-price comparison for the header."""
        if not self.has_data:
            return "premium-equiv: $0.0000"
        return f"premium-equiv: ${self.premium_equivalent_usd():.4f}"

    def savings_readout(self) -> str:
        """Deprecated alias; the text never says "saved"."""
        return self.premium_equivalent_readout()

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
            ("◇", "PREMIUM-EQUIV (HYPOTHETICAL)",
             f"${self.premium_equivalent_usd():.4f}"),
            ("◇", "PRICING", pricing),
            ("✓", "TURNS", str(self.turns)),
            ("⬡", "TOKENS", f"{self.tokens:,}"),
            ("⇄", "PROMPT", f"{self.prompt_tokens:,}"),
            ("⇄", "COMPLETION", f"{self.completion_tokens:,}"),
        ]
        width = max(len(f"{icon} {name}") for icon, name, _ in rows)
        return [(f"{icon} {name}".ljust(width), value)
                for icon, name, value in rows]

    def model_dashboard_lines(self) -> list[tuple[str, str]]:
        """Per-model rows for the F3 dashboard's model breakdown view."""
        rows = []
        for mb in self.model_breakdown():
            tier_color = mb["tier_color"]
            rows.append((
                f"[{tier_color}]{mb['tier_label']}[/]",
                f"{mb['model_id']}  ·  ${mb['spent_usd']:.4f} spent  ·  "
                f"${mb['paid_equivalent_usd']:.4f} premium-equiv",
            ))
        if not rows:
            rows.append(("NEUTRAL", "no model usage yet"))
        return rows