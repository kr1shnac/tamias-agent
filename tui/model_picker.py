import re

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.containers import Vertical

from tui.credits import TIER_LABELS, TIER_COLORS

import model_catalog
import providers

# Fallback list, used only if models/catalog.json is missing. The catalog is
# generated from the provider's live lineup by demo/fetch_models.py, so it also
# carries real prices; this list is just enough to keep the picker usable.
FALLBACK_MODELS = [
    ("Nemotron-3.5 Lightning (Free)", "nvidia/nemotron-3.5-lightning:free", "free"),
    ("Nemotron-3 Ultra 550B (Free)", "nvidia/nemotron-3-ultra-550b-a55b:free", "free"),
    ("Gemma-4 31B IT (Free)", "google/gemma-4-31b-it:free", "free"),
    ("Poolside Laguna S-2.1 (Free)", "poolside/laguna-s-2.1:free", "free"),
    ("LFM-2.5 2.6B (Free)", "liquid/lfm-2.5-2.6b:free", "free"),
    ("North Mini Code (Free)", "cohere/north-mini-code:free", "free"),
    ("Claude Haiku 4.5 (Premium)", "anthropic/claude-haiku-4.5", "premium"),
    ("GLM-4.7 (Premium)", "z-ai/glm-4.7", "premium"),
]


def _short_name(model: dict) -> str:
    """``"NVIDIA: Nemotron-3 Ultra 550B (free)"`` -> ``"Nemotron-3 Ultra 550B"``.

    The provider prefix and the free/paid suffix are noise in a narrow row; the
    tier is appended separately, so the price marker is never lost.
    """
    name = str(model.get("name") or model.get("id") or "")
    if ": " in name:
        name = name.split(": ", 1)[1]
    name = re.sub(r"\s*\((free|paid)\)\s*$", "", name, flags=re.IGNORECASE)
    return name.strip() or str(model.get("id"))


def _build_models() -> list[tuple[str, str, str]]:
    """Models the user can actually run, as ``(label, model_id, tier)``.

    Free models always appear. A paid model appears only when the operator has
    enabled paid spend (``--allow-paid`` / ``AGENT_ALLOW_PAID``) or holds a
    direct key for that provider - see :mod:`providers`. Offering a model the
    run cannot call would be a worse lie than offering fewer models.
    """
    entries = []
    for model in model_catalog.models():
        model_id = model["id"]
        if not providers.model_allowed(model_id):
            continue
        tier = model.get("tier", "paid")
        entries.append((f"{_short_name(model)} ({tier.title()})", model_id, tier))
    return entries


FALLBACK_MODELS = [
    entry for entry in FALLBACK_MODELS if providers.model_allowed(entry[1])
] or [("Nemotron-3.5 Lightning (Free)", "nvidia/nemotron-3.5-lightning:free", "free")]

MODELS = _build_models() or FALLBACK_MODELS


def tier_of_model(model_id: str) -> str:
    """Return the tier for a model id: free, mid, premium, or paid."""
    for _, model, tier in MODELS:
        if model == model_id:
            return tier
    if model_id.endswith(":free"):
        return "free"
    return "paid"


def is_free(model_id: str) -> bool:
    """A `:free` variant bills $0.00; anything else is billed at real rates."""
    return str(model_id).endswith(":free")


def cost_label(model_id: str) -> str:
    """A short price marker so the choice is never a blind one."""
    return "free" if is_free(model_id) else "paid"


def tier_label(tier: str) -> str:
    """Human-readable tier label with color hint."""
    return TIER_LABELS.get(tier, tier.title())


def tier_color(tier: str) -> str:
    """ANSI color for a tier."""
    return TIER_COLORS.get(tier, "#e8e8e8")


def listed_models(allowed=None):
    """The catalogue entries a picker may offer.

    ``allowed`` is the active policy's model allowlist; an empty or absent list
    means every entry is offered. A policy that names models narrows the menu to
    exactly those, so a company can fence routing the way it fences tools.

    Returns a list of ``(name, model_id)`` 2-tuples for backward compatibility.
    Use :func:`listed_models_with_tiers` for 3-tuples including tier.
    """
    entries = list(MODELS)

    if allowed:
        allowed = {m.strip() for m in allowed}
        entries = [(name, model, tier) for name, model, tier in entries if model in allowed]

    return [(name, model) for name, model, _ in entries]


def listed_models_with_tiers(allowed=None):
    """Like :func:`listed_models` but returns ``(name, model_id, tier)`` 3-tuples."""
    entries = list(MODELS)

    if allowed:
        allowed = {m.strip() for m in allowed}
        entries = [(name, model, tier) for name, model, tier in entries if model in allowed]

    return entries


class ModelPicker(ModalScreen[str]):
    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    def __init__(self, allowed=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.allowed = allowed

    CSS = """
    ModelPicker {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #picker-dialog {
        width: 70;
        height: auto;
        padding: 1 2;
        background: #1a1a1a;
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

    #tier-legend {
        margin-top: 1;
        color: #94a3b8;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        self.entries = listed_models(self.allowed)
        self.entries_with_tiers = listed_models_with_tiers(self.allowed)

        with Vertical(id="picker-dialog"):
            yield Static("SELECT AN LLM MODEL", id="picker-title")
            options = [
                f"[{tier_color(tier)}]{name}[/]  [{tier_color(tier)}]· {tier_label(tier)}[/]"
                for name, model, tier in self.entries_with_tiers
            ]
            yield OptionList(*options, id="model-list")
            yield Static(
                "green = free ($0.00)  ·  cyan = mid tier  ·  red = premium/paid",
                id="tier-legend",
            )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        index = event.option_index
        model_id = self.entries_with_tiers[index][1]
        self.dismiss(model_id)

    def action_dismiss_modal(self) -> None:
        self.dismiss("")