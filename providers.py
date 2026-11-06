"""Which model providers this machine can actually use - and can pay for.

The rule the operator asked for: **free models always work; paid models are
opt-in.** A free (``:free``) model bills $0.00, so it needs nothing beyond the
gateway credential the agent already has. A paid model is offered only when one
of these is true:

  1. ``AGENT_ALLOW_PAID=1`` (or the ``--allow-paid`` flag) - "I accept spend on
     the configured gateway"
  2. a **direct** provider key is present *and* the gateway URL points at that
     provider (e.g. ``ANTHROPIC_API_KEY`` with ``TAMIAS_BASE_URL`` on Anthropic)

That second rule matters for honesty: an Anthropic key in the environment does
not make ``anthropic/claude-*`` callable through OpenRouter. The key has to be
usable by the endpoint the agent actually talks to.

Nothing here prints, logs or returns a key value. Detection only reports *which
env var names are set*, so it is safe to show in a demo.
"""
from __future__ import annotations

import os

# provider prefix (the part before "/" in a model id) -> env vars that could
# authorise it directly
DIRECT_KEYS: dict[str, tuple[str, ...]] = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "google": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "mistralai": ("MISTRAL_API_KEY",),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "x-ai": ("XAI_API_KEY",),
    "moonshotai": ("MOONSHOT_API_KEY",),
    "cohere": ("COHERE_API_KEY",),
    "meta-llama": ("TOGETHER_API_KEY", "FIREWORKS_API_KEY"),
}

# credentials for the gateway / aggregator the agent is pointed at
GATEWAY_KEYS = ("OPENROUTER_API_KEY", "TAMIAS_API_KEY")

# gateway host -> provider family the URL itself implies
_URL_PROVIDERS = (
    ("openrouter.ai", "openrouter"),
    ("anthropic.com", "anthropic"),
    ("openai.com", "openai"),
    ("generativelanguage.googleapis.com", "google"),
    ("mistral.ai", "mistralai"),
    ("deepseek.com", "deepseek"),
    ("x.ai", "x-ai"),
)


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def detected_direct() -> dict[str, str]:
    """Providers with a direct key set: ``{provider: env_var_name}``.

    Returns variable *names*, never values.
    """
    found: dict[str, str] = {}
    for provider, env_names in DIRECT_KEYS.items():
        for name in env_names:
            if os.environ.get(name, "").strip():
                found[provider] = name
                break
    return found


def has_gateway_key() -> bool:
    return any(os.environ.get(name, "").strip() for name in GATEWAY_KEYS)


def paid_enabled() -> bool:
    """Did the operator accept paid spend?"""
    return _env_truthy("AGENT_ALLOW_PAID")


def base_url_provider(url: str | None = None) -> str:
    """Which provider family the configured gateway URL points at."""
    target = (url if url is not None else os.environ.get("TAMIAS_BASE_URL", "")) or ""
    target = target.lower()
    for needle, provider in _URL_PROVIDERS:
        if needle in target:
            return provider
    return "custom"


def provider_of(model_id: str) -> str:
    return str(model_id or "").split("/", 1)[0]


def is_free_model(model_id: str) -> bool:
    """Free means the provider bills $0.00 - the `:free` variants."""
    return str(model_id or "").strip().endswith(":free")


def model_allowed(model_id: str, paid: bool | None = None) -> bool:
    """True when this model may be offered under the current key situation."""
    if is_free_model(model_id):
        return True

    if paid if paid is not None else paid_enabled():
        return True

    provider = provider_of(model_id)
    if provider in detected_direct() and base_url_provider() == provider:
        return True

    return False


def why_blocked(model_id: str) -> str:
    """A short, non-technical reason a paid model is not offered."""
    provider = provider_of(model_id)
    if detected_direct().get(provider):
        return (f"{model_id} needs the agent pointed at {provider} "
                f"(TAMIAS_BASE_URL); this run uses {base_url_provider()}")
    return (f"{model_id} is a paid model - set AGENT_ALLOW_PAID=1 "
            f"or pass --allow-paid to allow spend")


def filter_allowed(model_ids: list[str], paid: bool | None = None) -> list[str]:
    return [m for m in model_ids if model_allowed(m, paid)]


def report_lines() -> list[str]:
    """A one-line-per-fact summary, safe to print in a demo."""
    direct = detected_direct()
    if paid_enabled():
        spare = f"; direct keys: {', '.join(sorted(direct))}" if direct else ""
        return [f"paid models enabled (AGENT_ALLOW_PAID){spare}"]
    if direct:
        return [
            "paid models OFF - free models only "
            f"(direct keys present: {', '.join(sorted(direct))})",
            "enable paid with --allow-paid or AGENT_ALLOW_PAID=1",
        ]
    return ["paid models OFF - free models only (no paid key detected)"]
