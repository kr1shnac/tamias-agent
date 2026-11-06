# Routes

Tamias serves the following HTTP routes. The default router mode is `shadow`.

---

## Router Modes and State Diagram

Tamias has three routing modes. The default is `shadow`, which records the
decision it WOULD make without changing the request.

```mermaid
stateDiagram-v2
    [*] --> shadow: default mode
    shadow --> shadow: record decision, forward unchanged
    shadow --> active: opt-in via --router-mode active
    active --> active: rewrite to --cheap-model; fail-closed gate
    active --> shadow: --router-mode shadow
    off --> off: forward unchanged, record no decision
    off --> shadow: --router-mode shadow
```

### Mode Details

| Mode | Behaviour |
|---|---|
| **`off`** | Forward unchanged, record no decision |
| **`shadow`** (default) | Record the decision it WOULD make, forward unchanged |
| **`active`** | Rewrite request to `--cheap-model`; opt-in and fail-closed: the process refuses to start unless the target is named in `--registry`, tool-capable there and priced by the sheet, and a switch the caller's key does not allow is suppressed rather than refused |

---

## Metered Routes

These routes are metered (token usage and cost recorded):

| Route | Method | Metered |
|---|---|---|
| `/v1/chat/completions` | POST | ✅ |
| `/v1/responses` | POST | ✅ |
| `/v1/messages` | POST | ✅ |

### Passthrough Route

| Route | Method | Behaviour |
|---|---|---|
| `/v1/chat/completions` | PASSTHROUGH | Counted-only: one `route="passthrough"` row with no tokens and no cost, never priced |

---

## Non-Metered Routes

These routes pass through without metering:

| Route | Method | Behaviour |
|---|---|---|
| Health checks | GET | No metering |
| Status endpoints | GET | No metering |

---

## Error Markers

Configure `error_markers` in the router configuration (`examples/router.example.toml`)
to set how Tamias handles errors from agent tools.

---

## Version

**Current:** `0.1.0a7` (2026-10-20)

---

*For the design spec, read `TAMIAS-SSOT.md`. For the code-truth ledger, read
`docs/audit/claims.md`.*