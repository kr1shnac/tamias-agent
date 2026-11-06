# Boundary plan — 2026-10-31

## Goal

Make the company-set boundary **enforced, per action, fail-closed, and visibly
limited to the assigned product** — not merely described. Then separate the
remaining work into demo-blocking, production-blocking, and later.

## Phase 0 — Freeze the evidence (done this run)

The inventory is in `framed-question.md` §7. The twelve query families are:
topic/use case, company, product, read denial, tools, ask, shell, paths,
plan/dossier, managed policy, audit, and secrets.

Known current state from `docs/RELEASE-STATUS.md`:

- 374 tests passing; offline gate 13 passed, 0 failed, 1 skipped.
- Live path: two passes before the `.` prompt change; latest retry 0/2
  rate-limited.
- OS sandbox: not built.
- Client-pinned manifest: not built.
- MCP boundary server: not built.
- Live benchmark: not run.

## Phase 1 — Council (this run)

Five isolated advisors, five anonymous reviewers, one chairman. The framed
question is neutral. The council is asked to distinguish:

1. what the current fence actually enforces,
2. how it can be bypassed or exceeded,
3. which gaps matter for the demo versus production,
4. one concrete next step.

## Phase 2 — Classify the findings by threat model

Every accepted gap gets a threat-model label:

- **Remote model / prompt injection** — the model is untrusted; a tool call is
  the attack surface.
- **Local user / operator** — the person running the agent can edit files,
  environment, Python, and policy. This is not the same threat as a remote model.
- **Gateway / supply chain** — the policy source, manifest, model provider, and
  package are trusted or not.
- **Demo only** — quota, model quality, and TUI rehearsal.

Each gap also gets: P0 (demo-blocking), P1 (production-blocking), P2 (later), or
"document as a limit, do not claim".

## Phase 3 — Fix order (provisional, subject to the council)

### P0 — before claiming the boundary as a guarantee

1. **Shell is inside the product, not just the company.** The policy root must
   bound shell cwd, relative paths, and the test command; a shell call that can
   mutate or read another project must be refused or ask-gated.
2. **Shell is a mutation channel.** Writes are ask-gated; `python3 -m pytest`,
   `git diff --output`, and similar commands are not. Either ask-gate the shell
   or prove the allowlist cannot mutate outside the signed plan.
3. **Tests for the bypasses.** Add probes for shell cross-project access,
   arbitrary Python via an allowed command family, `git diff` output, policy
   and audit access, network egress, and `.`/bare filenames.
4. **Managed mode says what it verifies.** The agent currently trusts the
   gateway response; either verify the signed manifest client-side with a pinned
   key, or state plainly that the gateway is the trust root and pin it.
5. **Audit is not tamper-evident.** Add a hash chain or signed checkpoints, or
   stop implying SIEM-grade evidence.

### P1 — production hardening

6. **OS/container sandbox + network egress allowlist** (microVM/gVisor or a
   constrained container). The current shell guard is best-effort; the kernel
   should be the hard boundary.
7. **MCP boundary server** (the missing integration depth).
8. **Policy file outside the repo**, admin-owned and read-only; local policy
   must not be editable by the agent's own shell.
9. **Domain gate honesty.** The lexical `domain_check` is a spend/scope guard,
   not a security boundary; the prompt and card must say so.

### P2 — later

- Durable Time Travel / session store + resume.
- Flight Recorder / audit export.
- Streaming + cancel; AGENTS.md as project rules.
- Live benchmark; PyPI publish.

## Phase 4 — Verification

- Full suite: 374.
- Offline gate: 13 / 0 / 1.
- New boundary probes, including the bypasses above.
- Two consecutive live gate passes **after** the code change; if 429, say the
  live path is unavailable and show the offline gate. Never claim a live pass
  that did not happen.
- TUI rehearsal: **Y** ask, **N** ask, **V** diff, **Z** checkpoint.

## Phase 5 — Documentation and release

- Update `docs/BOUNDED-AGENT.md`, `docs/FRONTEND_REFERENCE.md` §8,
  `docs/RELEASE-STATUS.md`, `docs/audit/claims.md`, `demo/PRESENT.md`.
- Keep the "best-effort" language until the hard layer exists.
- No commit or push without explicit instruction.

## What else is pending

| # | Item | Type | State |
|---|---|---|---|
| 1 | Restart TUI and verify the `.` path-hint fix end to end | demo | pending |
| 2 | Two consecutive live passes after the prompt change | demo | blocked (latest 0/2, 429) |
| 3 | Live TUI rehearsal of **V** diff and **Z** checkpoint | demo | unconfirmed |
| 4 | Shell product scope and mutation ask-gate | boundary P0 | pending |
| 5 | Bypass tests for shell, network, policy/audit | boundary P0 | pending |
| 6 | Client-pinned manifest / gateway trust statement | boundary P0 | pending |
| 7 | Tamper-evident audit | boundary P0/P1 | pending |
| 8 | OS/container sandbox + egress allowlist | boundary P1 | not built |
| 9 | MCP boundary server | boundary P1 | not built |
| 10 | Session store + resume | product P1 | pending |
| 11 | Durable checkpoints / Flight Recorder | product P1/P2 | pending |
| 12 | Streaming + cancel; AGENTS.md project rules | product P1 | pending |
| 13 | Live benchmark | evidence | unrun |
| 14 | PyPI publish (wheel builds; package not published) | release | pending |
| 15 | Commit the uncommitted work | release | needs explicit instruction |
