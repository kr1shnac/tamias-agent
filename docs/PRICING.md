# Pricing

How token counts become a dollar figure, and when the answer is UNKNOWN.

---

## Provider-billed USD only

Tamias records the **cost** the provider reports for each completed turn.
It never derives a number from token counts, never compares against an
invented baseline, and never guesses a budget. A turn whose cost the provider
did not report is counted as *unpriced*, never as zero.

## Hypothetical retail rates (premium-equivalent only)

The UI's premium-equivalent compares actual spend against what the same usage
would cost at premium list rates. These rates are **hypothetical** — they are
not a measurement, not a guarantee, and not a baseline. The difference is a
**retail delta**, not a measured saving; the UI must never call it "saved".

| Tier | Illustrative rate | Prompt (per 1k) | Completion (per 1k) |
|------|-------------------|-----------------|---------------------|
| Free | free-tier model | $0.0000 | $0.0000 |
| Mid | mid-tier model | $0.0030 | $0.0150 |
| Premium | premium-tier model | $0.0150 | $0.0750 |

## UNKNOWN costs

When a provider step returns no cost field, Tamias charges **UNKNOWN** — never
$0.00. UNKNOWN never becomes 0. A turn with any UNKNOWN step is flagged as
unpriced, so the session total is never mistaken for a complete bill.

## No measured savings

There are no measured savings in Tamias. Every dollar figure in the UI is
provider-billed USD for actual turns, or a hypothetical retail equivalent
clearly labelled as such. Claims of "% saved" or "cost reduction" are
unverified unless backed by a gateway meter reading.

---

*For the design spec, read `TAMIAS-SSOT.md`. For the code-truth ledger, read
`docs/audit/claims.md`.*