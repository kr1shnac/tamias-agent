"""Tests for the model catalog, provider gating, and rotation.

These cover the two promises the demo makes:

* the roster is real - ids, tiers and prices come from the provider's own
  listing, and only tool-capable models are kept;
* money is never a surprise - free models are always usable, paid models only
  after an explicit opt-in (or a direct key that the configured endpoint can
  actually use).

Everything here is offline. `demo/fetch_models.py` is the only thing that talks
to the network, and its filtering rules are tested with synthetic input.
"""
import importlib.util
import os
import sys

import pytest


# ------------------------------------------------------------------ catalog


def test_catalog_is_a_large_real_roster():
    import model_catalog

    catalog = model_catalog.load()
    models = catalog["models"]

    assert len(models) >= 50, "the roster is the credibility claim; keep it big"
    assert len({m["id"] for m in models}) == len(models), "ids must be unique"
    assert models, "catalog must not be empty"

    for model in models:
        assert model["id"], "every entry needs an id"
        assert model["tier"] in model_catalog.TIERS
        assert model["prompt_usd_per_1k"] >= 0, "prices come from the provider"
        assert model["completion_usd_per_1k"] >= 0
        assert model["context"] > 0

    counts = catalog["counts"]
    assert counts["total"] == len(models)
    assert counts["free"] >= 10, "free models are what make the demo cost $0"


def test_free_tier_is_actually_free_and_paid_tiers_are_not():
    import model_catalog

    for model in model_catalog.models("free"):
        assert model["prompt_usd_per_1k"] == 0
        assert model["completion_usd_per_1k"] == 0

    for tier in ("mid", "premium"):
        paid = model_catalog.models(tier)
        assert paid, f"tier {tier} should not be empty"
        for model in paid:
            assert model["prompt_usd_per_1k"] > 0


def test_catalog_helpers_pick_and_label():
    import model_catalog

    free = model_catalog.pool("free")
    assert len(free) >= 10
    assert all(model_id.endswith(":free") for model_id in free)

    # deterministic and it wraps: that is what makes a rotation reproducible
    assert model_catalog.pick(0) == free[0]
    assert model_catalog.pick(len(free)) == free[0]
    assert model_catalog.pick(1) != free[0]

    first = model_catalog.by_id(free[0])
    assert first and first["tier"] == "free"
    assert model_catalog.tier_of(free[0]) == "free"
    assert model_catalog.tier_of("nobody/knows:free") == "free"
    assert model_catalog.label(free[0])

    assert model_catalog.pool("free", limit=3) == free[:3]
    assert model_catalog.pick(0, "free", limit=3) == free[0]


def test_catalog_degrades_to_empty_instead_of_crashing(tmp_path):
    import model_catalog

    broken = tmp_path / "catalog.json"
    broken.write_text("{not json")

    loaded = model_catalog.load(str(broken))
    assert loaded["models"] == []


# ------------------------------------------------------------- fetch rules


@pytest.fixture()
def fetch_module():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "demo", "fetch_models.py")
    spec = importlib.util.spec_from_file_location("demo_fetch_models", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _entry(model_id, prompt, completion=0.0, tools=("tools",), context=1000):
    return {
        "id": model_id,
        "name": model_id,
        "context_length": context,
        "pricing": {"prompt": str(prompt), "completion": str(completion)},
        "supported_parameters": list(tools),
    }


def test_fetch_keeps_only_callable_models(fetch_module):
    raw = [
        _entry("good/free-model:free", 0, 0),
        _entry("good/cheap", 0.0000001, 0.0000002),
        _entry("vendor/expensive", 0.000005, 0.00001),
        _entry("vendor/no-tools", 0, 0, tools=("temperature",)),
        _entry("openrouter/auto", -1, -1),
        _entry("vendor/batch-model:batch", 0.000001, 0.000002),
        _entry("~vendor/alias", 0.000001, 0.000002),
        _entry("vendor/too-expensive", 0.01, 0.02),
    ]

    catalog = fetch_module.build(raw)
    ids = [m["id"] for m in catalog["models"]]

    assert "good/free-model:free" in ids
    assert "good/cheap" in ids
    assert "vendor/expensive" in ids
    for rejected in ("vendor/no-tools", "openrouter/auto", "vendor/batch-model:batch",
                     "~vendor/alias", "vendor/too-expensive"):
        assert rejected not in ids, f"{rejected} is not a directly callable model"

    tiers = {m["id"]: m["tier"] for m in catalog["models"]}
    assert tiers["good/free-model:free"] == "free"
    assert tiers["good/cheap"] == "mid"
    assert tiers["vendor/expensive"] == "premium"


def test_fetch_caps_the_roster_so_the_picker_stays_usable(fetch_module):
    raw = [_entry(f"vendor/m{i}", 0, 0) for i in range(fetch_module.MAX_FREE + 20)]
    catalog = fetch_module.build(raw)

    assert len(catalog["models"]) <= fetch_module.MAX_FREE
    assert catalog["counts"]["total"] == len(catalog["models"])


# ---------------------------------------------------------- provider gating


def test_free_models_are_always_allowed(monkeypatch):
    import providers

    monkeypatch.delenv("AGENT_ALLOW_PAID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert providers.model_allowed("nvidia/nemotron-3.5-lightning:free")
    assert providers.model_allowed("anything/at-all:free")


def test_paid_models_are_blocked_without_opt_in(monkeypatch):
    import providers

    monkeypatch.delenv("AGENT_ALLOW_PAID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert not providers.paid_enabled()
    assert not providers.model_allowed("anthropic/claude-3-opus")
    assert not providers.model_allowed("openai/gpt-oss-20b")

    reason = providers.why_blocked("anthropic/claude-3-opus")
    assert "--allow-paid" in reason
    assert "AGENT_ALLOW_PAID" in reason


def test_allow_paid_enables_every_model(monkeypatch):
    import providers

    monkeypatch.setenv("AGENT_ALLOW_PAID", "1")

    assert providers.paid_enabled()
    assert providers.model_allowed("anthropic/claude-3-opus")
    assert providers.model_allowed("openai/gpt-oss-20b")
    assert providers.model_allowed("nvidia/nemotron-3.5-lightning:free")


def test_a_direct_key_only_counts_when_the_endpoint_matches(monkeypatch):
    import providers

    monkeypatch.delenv("AGENT_ALLOW_PAID", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
    monkeypatch.setenv("TAMIAS_BASE_URL", "https://openrouter.ai/api/v1")

    # an Anthropic key does not make an Anthropic model callable through an
    # OpenRouter endpoint, and pretending otherwise would bill the wrong account
    assert not providers.model_allowed("anthropic/claude-3-opus")

    monkeypatch.setenv("TAMIAS_BASE_URL", "https://api.anthropic.com/v1")
    assert providers.model_allowed("anthropic/claude-3-opus")
    # a different provider's key still does not authorise this model
    assert not providers.model_allowed("openai/gpt-oss-20b")


def test_provider_report_never_leaks_a_key(monkeypatch):
    import providers

    secret = "sk-ant-SUPER-SECRET-VALUE"
    monkeypatch.delenv("AGENT_ALLOW_PAID", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)

    text = "\n".join(providers.report_lines())

    assert secret not in text
    assert "anthropic" in text                # it may name the provider
    assert "free models only" in text


def test_filter_allowed_keeps_free_and_drops_paid(monkeypatch):
    import providers

    monkeypatch.delenv("AGENT_ALLOW_PAID", raising=False)
    ids = ["a/free:free", "b/paid-model", "c/free-2:free"]

    assert providers.filter_allowed(ids) == ["a/free:free", "c/free-2:free"]
    assert providers.filter_allowed(ids, paid=True) == ids


# ------------------------------------------------------------- agent rotation


def _agent():
    import agent
    return agent


def test_rotation_is_off_by_default(monkeypatch):
    agent = _agent()
    monkeypatch.setattr(agent, "MODEL_ROTATE", "off")

    assert agent.rotate_model(0, 1) is None


def test_rotation_walks_the_pool_turn_by_turn(monkeypatch):
    agent = _agent()
    monkeypatch.setenv("AGENT_MODEL_POOL", "one:free,two:free,three:free")
    agent.reset_model_pool()
    monkeypatch.setattr(agent, "MODEL_ROTATE", "turn")

    assert agent.model_pool() == ["one:free", "two:free", "three:free"]
    picks = [agent.rotate_model(turn, step=1) for turn in range(4)]

    assert picks == ["one:free", "two:free", "three:free", "one:free"]
    # inside a turn the model is stable, so the switch is a turn-level fact
    assert agent.rotate_model(1, step=1) == agent.rotate_model(1, step=5)

    agent.reset_model_pool()


def test_rotation_can_switch_every_step(monkeypatch):
    agent = _agent()
    monkeypatch.setenv("AGENT_MODEL_POOL", "a:free,b:free")
    agent.reset_model_pool()
    monkeypatch.setattr(agent, "MODEL_ROTATE", "step")

    assert [agent.rotate_model(0, step) for step in (1, 2, 3, 4)] == [
        "a:free", "b:free", "a:free", "b:free"]

    agent.reset_model_pool()


def test_rotation_defaults_to_the_free_catalog(monkeypatch):
    """With no AGENT_MODEL_POOL, rotation must still cost $0."""
    agent = _agent()
    import model_catalog

    monkeypatch.delenv("AGENT_MODEL_POOL", raising=False)
    agent.reset_model_pool()

    pool = agent.model_pool()
    assert pool == model_catalog.pool("free")
    assert pool, "the catalog ships free models"
    assert all(model_id.endswith(":free") for model_id in pool)

    agent.reset_model_pool()


def test_an_empty_pool_means_no_rotation(monkeypatch):
    agent = _agent()
    monkeypatch.setenv("AGENT_MODEL_POOL", " , , ")
    agent.reset_model_pool()
    monkeypatch.setattr(agent, "MODEL_ROTATE", "turn")

    assert agent.model_pool() == []
    assert agent.rotate_model(0, 1) is None

    agent.reset_model_pool()


def test_runnable_requires_both_policy_and_keys(monkeypatch):
    agent = _agent()

    monkeypatch.delenv("AGENT_ALLOW_PAID", raising=False)
    monkeypatch.setattr(agent, "allowed_models", lambda: [])

    assert agent.model_runnable("x/free:free")
    assert not agent.model_runnable("anthropic/claude-3-opus")

    monkeypatch.setenv("AGENT_ALLOW_PAID", "1")
    assert agent.model_runnable("anthropic/claude-3-opus")

    # even with paid enabled, a policy allowlist still wins
    monkeypatch.setattr(agent, "allowed_models", lambda: ["x/free:free"])
    assert not agent.model_runnable("anthropic/claude-3-opus")
    assert agent.model_runnable("x/free:free")


def test_tier_lookup_reads_the_catalog():
    agent = _agent()
    import model_catalog

    free = model_catalog.pool("free")[0]
    mid = model_catalog.pool("mid")[0]

    assert agent._tier_of_model(free) == "free"
    assert agent._tier_of_model(mid) == "mid"
    # an id the catalog does not know still gets a sane answer
    assert agent._tier_of_model("someone/unknown:free") == "free"
