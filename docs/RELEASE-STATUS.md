# Release Status

What is built, what is published, and what is blocked.

---

## Version

**Current:** `0.1.0a7` (2026-10-20; premium slice verified 2026-10-29)

## What is built

| Component | Status | Notes |
|-----------|--------|-------|
| Agent core (`agent.py`) | ✅ Built | Tool dispatch gate, policy enforcement, model routing, managed mode |
| TUI (`tui/`) | ✅ Built | Textual 8.2.8 + Rich 15.0.0, model picker, credits dashboard, boundary modals, boundary card, measured receipt, decision cards, signed plan contract, file-drift enforcement, investigation dossier, pre-write dossier gate, file checkpoint preview/restore, frozen diff review |
| Gateway (`tamias/proxy.py`) | ✅ Built | Metering, pricing, shadow/active routing, signed policy manifests |
| Dashboard | ✅ Built | Local web page, routed vs baseline cost |
| Admin CLI | ✅ Built | Key issuance, manifest signing |
| Benchmark (`bench.py`) | ✅ Built | Cost-per-success harness, no live run recorded |
| Brief compiler (`brief.py`) | ✅ Built | D13, offline, no model calls |
| Context index (`context_index.py`) | ✅ Built | D14, mandatory citations |
| Demo (`demo/`) | ✅ Built | Offline boundary demos, mock provider, live gate (14 checks) |

## What is published

| Item | Status | Notes |
|------|--------|-------|
| PyPI package (`tamias`) | ❌ Not published | `pip install tamias` 404s; install from checkout only |
| Wheel | ✅ Builds | Includes `checkpoints.py`; installs into clean venv |
| `tamias --version` | ✅ `0.1.0a7` | Verified this run |

## What is blocked

| Item | Status | Notes |
|------|--------|-------|
| Live model path | ⚠️ Earlier passes; latest 0/2 | OpenRouter free tier: 50 requests/day; two consecutive `--live` runs on 2026-10-29 were 14/14 (34s and 36s) before the `.` path-hint prompt change. A fresh `--live` after that change was rate-limited 0/2, so no new live pass is claimed. Quota remains a stage risk |
| Live benchmark | ⚠️ Unrun | `bench.py` exists; no live results recorded |
| MCP boundary server | ❌ Not built | Integration depth 2 missing |
| OS sandbox | ❌ Not built | Best-effort shell guard only |
| Client-pinned manifest | ❌ Not built | "Bring your own gateway" bypass possible |
| Company boundary guarantee | ⚠️ Partially hardened, still not a guarantee | Directory-walker `deny_read` is now enforced per returned path (`test_boundary_walkers.py`). Shell, no-policy fail-closed, company-held audit, and managed-policy trust remain open. Evidence: `.council/runs/20261031-0912-boundary/verification.md`, `demo/attack_boundary.py` |
| Performance baseline | ⚠️ Partially measured | Full suite and offline gate timings are recorded in `docs/audit/2026-11-06-boundary-hardening.md`; TUI, large-tree policy checks, and live latency are unmeasured. Plan is in `OPENCODE-AGENT-BRIEF.md` §20 |

## Test gate

| Suite | Count | Status |
|-------|-------|--------|
| `test_agent.py` | 246 | ✅ Passed |
| `test_tui_features.py` | 50 | ✅ Passed (shared process) |
| `test_premium_features.py` | 40 | ✅ Passed (receipt, boundary, plan contract, dossier, decision card, checkpoint, frozen diff) |
| `tests/` (docs + catalog) | 34 | ✅ Passed |
| `test_boundary_walkers.py` | 7 | ✅ Passed (parent-directory deny_read composition) |
| Workspace demo tests | 4 | ✅ Passed |
| **Full suite** | **381** | ✅ All passing |
| **Offline gate pytest check** | **381** | ✅ Passed |

Evidence: `docs/audit/2026-10-28-work-surfaces.md` (plan/dossier views),
`docs/audit/2026-10-28-premium-slice.md` (boundary/receipt/decision),
`docs/audit/2026-10-28-plan-contract.md` (signature, drift, dossier gate),
`docs/audit/2026-10-28-time-travel.md` (file checkpoint preview/restore),
`docs/audit/2026-10-29-diff-capture.md` (frozen diff review) and
`docs/audit/2026-11-06-boundary-hardening.md` (deny_read walkers + attack
harness).

---

*For the design spec, read `TAMIAS-SSOT.md`. For the code-truth ledger, read
`docs/audit/claims.md`.*