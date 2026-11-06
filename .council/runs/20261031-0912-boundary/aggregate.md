# Aggregate

Anonymous labels map to styles in `mapping.json`; the mapping was hidden from
the reviewers. Votes are advisory, not proof.

## Ranking aggregation

| Answer | R1 | R2 | R3 | R4 | R5 | Average position | Rank |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 1 | 1 | 1 | 1 | 1 | 1.00 | 1 |
| E | 2 | 2 | 3 | 2 | 2 | 2.20 | 2 |
| A | 4 | 3 | 2 | 3 | 3 | 3.00 | 3 |
| C | 3 | 5 | 4 | 5 | 4 | 4.20 | 4 |
| D | 5 | 4 | 5 | 4 | 5 | 4.60 | 5 |

Source orders:

1. B > E > C > A > D
2. B > E > A > D > C
3. B > A > E > C > D
4. B > E > A > D > C
5. B > E > A > C > D

## Tallies

- Strongest answer: **B** — 5/5.
- Biggest blind spot: **C** — 5/5.
- Answer blamed most for the false reassurance that investigation tools are
  covered by `deny_read`: **C** (and **D** by two reviewers).

## What the reviewers said all five missed

1. **No external audit anchor / no company-held evidence.** R1, R3 and R5 all
   noted that a hash-chained local JSONL is still written by the audited party;
   the company receives nothing. R3 added that rows vanish when no policy is
   active and do not carry resolved path, cwd, policy hash, or plan binding.
2. **The egress demo probe is partly vacuous.** R2 noted `demo/showcase.py`
   blocks `fetch_url`, but `fetch_url` is not in the policy allow list; it
   proves unknown tools are rejected, not that network egress is controlled.
3. **The plan-signed “task” is not off-host attestation.** R2 asked who signs
   the plan and where the key lives. Verification confirmed it is a local
   `signed by user` flag, not cryptographic signing.
4. **Over-blocking / proportionality.** R4 noted the same substring deny that
   blocks malicious commands also blocks legitimate ones (`pytest -k
   "confirm parser"` contains `rm `). No advisor measured false positives.

## Interpretation

The council's strongest useful output is not a vote. It is that the team’s
evidence does not test composition or adversarial input, and that the request
“should not exceed” also has a false-positive side: work is wrongly refused.
