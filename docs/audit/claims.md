# Code-Truth Ledger

This document is the **code-truth ledger** for Tamias. It outranks the SSOT for
behaviour: what the code actually does. Verified against the gate (351 passed,
0 warnings).

---

## Verified Test Counts

| Source | Count | Verified |
|---|---|---|
| **Gate (current)** | **351** | ✅ this run |
| `test_agent.py` | 246 | ✅ passed |
| `test_tui_features.py` | 50 | ✅ shared process |
| `test_premium_features.py` | 40 | ✅ shared process |
| `tests/` (docs + catalog) | 34 | ✅ passed |
| Workspace demo tests | 4 | ✅ passed |
| **Full suite** | **374** | ✅ passed |

> **Note:** `test_tui_features.py` requires the real `rich` package and is run in
> a separate process from `test_agent.py`. The `_real_rich` fixture allows the
> two suites to share one pytest process when both are invoked together.

---

## Model Rates (SSOT:7)

Tamias uses three model tiers. Pricing is hypothetical (no measured savings exist).

| Tier | Example model | Prompt (per 1k) | Completion (per 1k) |
|------|--------------|-----------------|---------------------|
| Free | nemotron-3.5-lightning:free | $0.0000 | $0.0000 |
| Mid | claude-3.5-sonnet | $0.0030 | $0.0150 |
| Premium | claude-3-opus | $0.0150 | $0.0750 |

> **Note:** All dollar figures are hypothetical. The gate reports `cost_usd` as
> `UNKNOWN` when a step did not report a cost; `n/a` ≠ 0.

---

## Router Modes

Tamias has three routing modes. Default is `shadow`.

| Mode | Behaviour |
|---|---|
| **`off`** | Forward unchanged, record no decision |
| **`shadow`** (default) | Record the decision it WOULD make, forward unchanged |
| **`active`** | Rewrite request to `--cheap-model`; opt-in and fail-closed |

> Verified: `ROUTER_MODES = ("shadow", "off", "active")` in `cli.py:65`.

---

## Python Floor

`>=3.11` is the required Python version.

> Verified: declared in `pyproject.toml`.

---

## Doc-Integrity Test

The durable fix is the doc-integrity test (`tests/test_docs_integrity.py`) which
mechanically asserts every authoritative claim resolves and versions agree.

> This test is the canonical assertion that all documents (README, SSOT, claims,
> ROUTES, PRICING, RELEASE-STATUS) are consistent with each other and with the
> code. It is the durable fix recommended by the council (Option D minus C:
> rewrite README, reconcile docs, delete nothing).

---

## Version

**Current gate count:** 351 passed, 0 warnings (verified this run)

**Python:** >=3.11

**Council verdict:** Option D minus C — rewrite README, reconcile docs, delete
nothing. No files deleted. Durable fix: doc-integrity test.