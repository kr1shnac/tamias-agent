"""Fetch a real model catalog from the provider and write models/catalog.json.

Only models that advertise **tool calling** are kept: the agent's whole loop is
tool calls, so a model without them is decoration. Nothing here needs an API
key - the provider's /models endpoint is public.

    .venv/bin/python demo/fetch_models.py            # write the catalog
    .venv/bin/python demo/fetch_models.py --dry-run  # print what it would do

Tiers are derived from the provider's own prices, not from a hand-written list:

    free     price is exactly 0                     (`:free` variants)
    mid      prompt <= $0.50 / 1M tokens            (cheap paid)
    premium  everything above that                  (flagship)

The catalog is evidence, not an opinion: every field comes from the API, and
`fetched` records when. Re-run it whenever the provider's lineup moves.
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

URL = "https://openrouter.ai/api/v1/models"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "models", "catalog.json")

# $0.50 per 1M prompt tokens - the line between "cheap" and "flagship"
MID_CEILING_PER_TOKEN = 0.0000005
# never include anything above $20 / 1M prompt: a demo must not be able to
# switch itself onto a model that costs real money by accident
PREMIUM_CEILING_PER_TOKEN = 0.00002
MAX_FREE = 30
MAX_MID = 24
MAX_PREMIUM = 14

# families a reader will recognise; premium prefers these over no-name routers
PREFERRED_FAMILIES = (
    "anthropic/", "openai/gpt-", "google/gemini", "meta-llama/",
    "deepseek/", "qwen/", "mistralai/", "x-ai/", "moonshotai/", "z-ai/",
)


def fetch(url=URL):
    with urllib.request.urlopen(url, timeout=45) as response:
        return json.load(response)["data"]


def _price(entry, key):
    try:
        return float(entry.get("pricing", {}).get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _supports_tools(entry):
    return "tools" in (entry.get("supported_parameters") or [])


def _usable(model_id, prompt, completion):
    """Reject entries that are not a normal, directly-callable chat model.

    Routers report $-1 placeholder prices, batch variants are a different
    endpoint, and ``~`` ids are aliases that can disappear. None of them is
    something an agent can call as a model.
    """
    if not model_id or prompt < 0 or completion < 0:
        return False
    if model_id.startswith("~"):
        return False
    if any(marker in model_id for marker in (":batch", ":floor", "/auto")):
        return False
    if model_id.startswith("openrouter/"):
        return False
    return True


def build(raw):
    kept = []
    for entry in raw:
        model_id = str(entry.get("id") or "")
        if not _supports_tools(entry):
            continue
        prompt = _price(entry, "prompt")
        completion = _price(entry, "completion")
        if not _usable(model_id, prompt, completion):
            continue
        if prompt == 0.0 and completion == 0.0:
            tier = "free"
        elif prompt <= MID_CEILING_PER_TOKEN:
            tier = "mid"
        elif prompt <= PREMIUM_CEILING_PER_TOKEN:
            tier = "premium"
        else:
            continue
        kept.append({
            "id": model_id,
            "name": str(entry.get("name") or model_id),
            "tier": tier,
            "context": int(entry.get("context_length") or 0),
            # per 1k tokens, in USD, exactly as the provider lists it
            "prompt_usd_per_1k": round(prompt * 1000, 8),
            "completion_usd_per_1k": round(completion * 1000, 8),
        })

    def cheapest(model):
        return (model["prompt_usd_per_1k"], model["id"])

    free = sorted((m for m in kept if m["tier"] == "free"),
                  key=lambda m: (-m["context"], m["id"]))[:MAX_FREE]
    mid = sorted((m for m in kept if m["tier"] == "mid"), key=cheapest)[:MAX_MID]

    # premium: one or two per recognised family first (so the list reads like a
    # real lineup), then fill with the cheapest of whatever is left
    premium_pool = sorted((m for m in kept if m["tier"] == "premium"), key=cheapest)
    premium, per_family = [], {}
    for model in premium_pool:
        family = next((f for f in PREFERRED_FAMILIES
                       if model["id"].startswith(f)), None)
        if family is None:
            continue
        if per_family.get(family, 0) >= 2:
            continue
        premium.append(model)
        per_family[family] = per_family.get(family, 0) + 1
        if len(premium) >= MAX_PREMIUM:
            break
    for model in premium_pool:
        if len(premium) >= MAX_PREMIUM:
            break
        if all(model["id"] != p["id"] for p in premium):
            premium.append(model)
    premium = premium[:MAX_PREMIUM]

    models = free + mid + premium
    return {
        "source": URL,
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filter": "supported_parameters includes 'tools'; routers, batch "
                  "variants and '~' aliases excluded",
        "tier_rule": {
            "free": "prompt == 0 and completion == 0",
            "mid": f"0 < prompt <= {MID_CEILING_PER_TOKEN} per token "
                   f"($0.50 / 1M)",
            "premium": f"{MID_CEILING_PER_TOKEN} < prompt <= "
                       f"{PREMIUM_CEILING_PER_TOKEN} per token ($20 / 1M)",
        },
        "counts": {
            "free": len(free),
            "mid": len(mid),
            "premium": len(premium),
            "total": len(models),
            "available_with_tools": len(kept),
        },
        "models": models,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and report, do not write the file")
    args = parser.parse_args()

    try:
        raw = fetch()
    except Exception as exc:
        print(f"fetch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    catalog = build(raw)
    counts = catalog["counts"]
    print(f"available with tools: {counts['available_with_tools']}")
    print(f"selected: {counts['total']} "
          f"(free {counts['free']}, mid {counts['mid']}, premium {counts['premium']})")

    for tier in ("free", "mid", "premium"):
        print(f"\n{tier}:")
        for model in [m for m in catalog["models"] if m["tier"] == tier][:6]:
            print(f"  {model['id']:<48} "
                  f"${model['prompt_usd_per_1k']:.6f}/1k prompt")
        print("  ...")

    if args.dry_run:
        print("\ndry run: nothing written")
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as handle:
        json.dump(catalog, handle, indent=2)
        handle.write("\n")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
