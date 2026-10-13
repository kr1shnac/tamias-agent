# Bounded Agent — making tamias-agent company-safe

**Research date:** 2026-10-13 · **Scope:** agent.py + its local enforcement model
(the model runs remotely over OpenRouter; the *fence* is local, in this repo).

This document answers: *how does a company deploy an agent like tamias-agent so
it can only be used for specific use cases, against local repositories, without
trusting the model to behave?*

---

## 1. The core principle (research consensus)

Every 2026 enterprise survey said the same thing, so it is the anchor:

> **Prompts do not bound an agent. Enforcement happens at runtime, at the tool
> boundary**, evaluated per action — allow, deny, or escalate. See
> *Tool-Scoped Guardrails* (source [1]), *AI Agent Policy Enforcement* (source
> [2]), *AI Agent Sandboxing & Progressive Enforcement* (source [3]).

Three consequences follow:

1. **The policy file is a configuration, not a wish.** `permissions.allow /
   deny / ask` pattern rules (Claude Code `settings.json`, [4][5]), managed
   settings that the agent itself cannot edit ([6]), and MDM-deployed enterprise
   policy ([7]).
2. **Identity + least privilege.** Treat the agent as a software principal:
   its own identity, its own token scoped to the task, and permissions limited
   to the intersection of "what the agent may do" and "what the user may do"
   ([8][9]).
3. **Defence in depth.** Instruction files (`AGENTS.md`) are *read by the model,
   not enforced* ([7]); the real layers are: tool allowlist → filesystem scope →
   network scope → secret control → shell sandbox → audit log ([1][3][10]).

---

## 2. What tamias-agent already has (the foundation)

Verified in `agent.py` (demoed live, test suite green):

| Layer | Mechanism | Where |
|---|---|---|
| Workspace fence | `resolve_in_workspace()` — realpath, symlink-safe | `agent.py:703` |
| Company fence | `resolve_in_company_workspace()` — `company/work/<id>/` | `agent.py:721` |
| Use-case gate | `--company-id <id>` activates the active fence | `bridge.py:108`, `agent.py:1677` |
| Secret control | `refuse_secret()` / `is_sensitive_path()` | `agent.py:400` |
| Shell hardening | cwd = company box, escape guard, scrubbed env, `TAMIAS_ALLOW_SHELL=0` | `agent.py:447-499` |
| Assignment | `--task-id` / `--assignee` recorded into the prompt | `build_system_prompt` |
| Visibility | blocked calls surface (boundary state / violation) | UI |

So the *spatial* boundary (what directories an agent may touch) is done and
tested. What companies also need is the *capability* boundary: **which tools,
which command families, which network hosts, which files**, per agreed use case
— plus an audit trail and a policy file the agent cannot rewrite.

---

## 3. The gap & the target model

| Capability | Industry pattern | tamias-agent today |
|---|---|---|
| Per-use-case tool allowlist | `allow/deny/ask` tool patterns ([4][5][10]) | ✗ all 8 tools always on |
| Command/arg pattern rules | `Bash(git status)` style ([4][10]) | ~ best-effort path guard only |
| Filesystem scope per use case | write only to task dirs ([10]) | only path containment |
| Network host allowlist | permitted hosts/ports ([10]) | ✗ none |
| Read-only mode | plan/review mode ([4][11]) | ✗ none |
| Ask/escalation | human approval for risky calls ([2][10]) | ✗ none |
| Audit log (per action) | agent identity → session → action ([9][12]) | events exist, no policy log |
| Admin-locked policy | policy file the agent can't edit ([6][7]) | ✗ policy would be a plain file |

---

## 4. The proposed design — a per-company policy profile

A single TOML policy file, loaded once at startup, that a company admin stores
(outside the agent's fence, e.g. `~/.config/tamias/policies/<company>.toml`),
and that the agent reads but never writes:

```toml
# ~/.config/tamias/policies/acme.toml  — owned by the company admin (chmod 600)
version = "1"

[use_case]
name        = "code-fix-bot"          # "this agent is only for these cases"
root        = "company/work/acme/bots/codefix"
read_only   = false                   # true → plan/review agent
models      = ["nvidia/nemotron-3.5-lightning:free"]

[tools]                                # allowlist: absent = tool disabled
allow = ["read_file", "search_in_files", "edit_file", "write_file", "run_shell", "update_plan"]
deny  = ["run_shell"]                  # policy wins over allow (hard deny)

[run_shell]                            # command-family scope (pattern rules)
allow = ["git status", "git diff", "git add", "python3 -m pytest", "grep "]
deny  = ["rm ", "curl ", "wget ", "git push ", "chmod "]
timeout = 30

[network]                              # egress allowlist (exfiltration path)
allow_hosts = ["pypi.org", "files.pythonhosted.org"]
block_egress = true

[paths]                                # finer filesystem scope on top of the fence
allow_write = ["company/work/acme/bots/codefix/**"]
deny_read   = ["company/work/acme/hr/**", "**/*.pem"]
```

### How the agent would enforce it (each maps to code)

1. **Tool dispatch gate** — before executing any tool, consult the policy:
   `hard deny` (tool-level or arg-pattern) → return `Error: policy deny …` and
   never run. This is *exactly* where `resolve_in_company_workspace` sits today;
   the policy check goes in the same dispatch path (`execute_tool`).
2. **`run_shell` pattern allow/deny** — extend `shell_escapes_company` with a
   second pass over `allow`/`deny` command patterns; deny wins.
3. **Filesystem scope** — `resolve_*` already returns the fence; a policy
   `allow_write`/`deny_read` glob set is a second check next to `refuse_secret`.
4. **Read-only mode** — a write gate: when `read_only = true`, every
   write/edit/create returns the policy error. One flag, high value (plan-agent).
5. **Escalation (ask)** — when a call matches neither allow nor hard deny,
   emit an `ask` event to the UI bridge; interactive run shows a confirm,
   headless run denies.
6. **Audit trail** — each decision (allowed / denied / asked / cmd) appended to
   a local JSONL (per company, rotated), containing `ts, company, tool, args,
   decision, rule_id`. This is the SIEM-ready record companies ask for ([9][12]).
7. **Policy can't be edited by the agent** — the policy file is outside the
   fence, and `is_sensitive_path`-style rules refuse any tool path that touches
   it (same mechanism as `.env` today).

### Honest limits

- `run_shell` is the sharp edge: without an OS sandbox (microVM/gVisor, [13])
  a determined prompt-injected command can still find unguarded operators. For a
  local TUI demo, the *policy allowlist + disabled-shell option* is the
  honest posture; OS-level sandboxes are the follow-on, not a claim we make.
- Free-tier models being 429 is orthogonal to bounding — bounding is fully local
  and testable offline.

---

## 5. Suggested build order (all offline-testable)

1. `PolicyProfile` dataclass + TOML loader (`tui`-free, pure `agent.py`).
2. Dispatch gate: tool allow / hard deny + `read_only` flag (first tests).
3. `run_shell` command-family allow/deny patterns.
4. Filesystem glob scope (`allow_write` / `deny_read`) beside `refuse_secret`.
5. `ask` escalation event + JSONL audit trail.
6. Policy-file self-protection test (agent cannot read/edit its own policy).
7. Demo: `--company-id acme` + a policy whose `deny` blocks `rm`/`curl` — show a
   command getting refused *and* the audit row being written.

Everything is testable with no network and no API key, so a company can evaluate
"our agent only for *our* use case" before any live run.

---

## Sources

[1] Tool-Scoped Guardrails — Agent safety must live next to the action (2026)
[2] AI Agent Policy Enforcement: A Complete 2026 Guide, Sweet Security
[3] AI Agent Sandboxing & Progressive Enforcement — ARMO (Mar 2026)
[4] Claude Code permissions: settings.json allow/deny/ask — Developers Digest
[5] Managed Settings for Claude & Codex — PromptArmor
[6] Claude Code: permission precedence & admin-protected settings — petefreitag.com
[7] Coding agent security guides — Arcjet (hooks + AGENTS.md not being enforced)
[8] WorkOS: the AI agent permissions checklist for SaaS apps (2026)
[9] Orchid: AI agent security best practices (service identity + scoped tokens)
[10] ayautomate: 8 controls for production AI agents (filesystem/network scope)
[11] hidekazu-konishi: Claude Code defaultMode (plan / acceptEdits / bypass)
[12] Northflank: enterprise AI coding agent deployment (audit, PR gates, sandbox)
[13] Modal: best code-execution sandboxes for AI agents 2026 (microVM/gVisor)