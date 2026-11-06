# TAMIAS — Complete Project Brief

**Purpose of this document.** A single, self-contained, honest description of the
whole Tamias project: the idea, what exists today, what does not, and an
independent take on what to keep and what to drop. Written to be handed to a
research model (e.g. Claude) as grounding, so it deliberately separates **fact**
(verified in code/docs) from **opinion**.

**Compiled:** 2026-10-15 · **Compiler:** Big Pickle (opencode)
**Repos read:** `/home/krish/Desktop/tamias` (the gateway), `/home/krish/Desktop/tamias-agent`
(the client), `docs/*`, `../HANDOFF-CODEX.md`.

**Verification legend used throughout**
- `[V]` = verified directly in source or docs during this review.
- `[D]` = documented but not independently re-verified here.
- `[O]` = opinion / judgement of the compiler, not a fact.

**Secrecy note.** `.env` (holds `OPENROUTER_API_KEY`) was never read. No secrets,
tokens, prompt text, or key material appear in this document, by design.

---

# Part I — The Project

## 1. Executive summary

Tamias is best understood in **two halves that fit together**:

- **`tamias`** — the **gateway / control plane**: a local HTTP proxy in front of
  an OpenAI-compatible (or Anthropic Messages / OpenAI Responses) upstream. It
  meters token usage and cost per request, can route to a cheaper model, enforces
  per-key budgets/model allow-lists, issues per-caller keys, and serves a
  **signed, project-bound use-case policy**. `[V]`
- **`tamias-agent`** — the **terminal coding agent** (the client a developer
  actually uses): a Textual TUI + a Python agent core with a local tool/path
  fence, managed mode, and three offline quality tools (brief compiler, context
  index, cost benchmark). `[V]`

The one-line product statement:
> **A company hands an employee an AI coding agent bound to one project, with
> enforceable limits on what it can touch and spend, and a truthful record of
> both.** `[O]`

The project historically grew out of a *research* question about inference cost
(see §3), and has more recently pivoted toward *governance* (bounding the agent
to one use case). The two share the gateway and are best sold as one system.

**Bottom line of the independent take (§10–§16 `[O]`):** the technical core is
real and tested; the project is **not unique as a category** but **is
differentiated as a combination and a trust model**; it "works" only if it stops
positioning itself as *yet another coding agent* and becomes the **boundary that
every agent runs inside** ("an agent firewall"), with OS-level containment to
make the word "cannot bypass" true.

---

## 2. The problem space

Tamias addresses two genuinely separate problems, and the whole product is the
union of the two: `[O]`

1. **Cost blindness.** A coding agent quietly burns tokens. Nobody can say what a
   task cost, whether a cheaper model would have sufficed, or where the money
   went. Existing gateways solve parts of this (§10).
2. **Unbounded agents.** An autonomous agent will happily try to build something
   off-scope, read a secrets file, or write outside the project. Prompts do not
   stop this; runtime enforcement at the tool boundary does. `[V]` (thesis of
   `docs/BOUNDED-AGENT.md`).

**The central claim Tamias makes that most tools do not:** you can put *both* an
economic boundary *and* a scope boundary behind **one server-side enforcement
point**, and have the client **honestly report which regime it is running
under**. `[O]`

---

## 3. What Tamias actually is — the two framings

The repos contain **two north-star framings** that have not been fully
reconciled. A research reader must hold both.

### 3.1 Framing A — "inference economics" (older, research)
Source: `tamias/docs/ARCHITECTURE.md` (v1.2, dated 2026-09-30, marked "FINAL
BASELINE"). `[V]`

- Central question: *"At a live coding-agent checkpoint, what does changing
  inference configuration `(model, effort)` cost, what does it buy in verified
  task progress, and when is the change better than staying?"* `[V]`
- Three stages: **OBSERVE → EXPERIMENT → CONTROL** (control only if earned by
  evidence). `[V]`
- Self-described product: *"a local, read-only coding-agent cost observability
  tool."* `[V]`
- Explicitly says the research does **not require** a proxy/gateway, memory,
  RAG, or multi-agent orchestration. `[V]`
- Has a **freeze rule**: no new scope without removing equal scope. `[V]`
- Honesty rule set: `UNKNOWN` never becomes `0`; `estimate` never becomes
  `measured`. `[V]`

This framing produced: price sheets, cost computation rules, shadow routing,
session/state model, and the local dashboard. `[V]`

### 3.2 Framing B — "bounded agent / company-safe" (newer, active)
Source: `tamias-agent/docs/BOUNDED-AGENT.md` (dated 2026-10-13). `[V]`

- The anchor: *"Prompts do not bound an agent. Enforcement happens at runtime, at
  the tool boundary, evaluated per action — allow, deny, or escalate."* `[V]`
- Consequences: the policy file is configuration, not a wish; identity +
  least-privilege; managed settings the agent itself cannot edit. `[V]`
- This framing produced: the `PolicyProfile` TOML gate, managed mode
  (`--require-proxy`), signed policy manifests (in the gateway), and the
  boundary modal in the TUI. `[V]`

### 3.3 The reconciliation (what the project *is* now) `[O]`
The two framings share Layer 2 (the gateway). The honest synthesis is a
**three-pillar product**:

| Pillar | Question it answers | Where it lives |
|---|---|---|
| **Boundary** (governance) | *What is this agent allowed to touch, and can it cheat?* | signed policy + local gate + (missing) OS sandbox |
| **Economics** (cost) | *What did it cost, and could it cost less?* | gateway metering + routing + budgets + dashboard + benchmark |
| **Quality** (do more with less) | *How do we need fewer tokens in the first place?* | offline brief compiler + context index |

Unifying promise: **do more, with less, safely, provably.** `[O]`

---

## 4. The architecture: three layers, two boundaries, four trust tiers

### 4.1 The three layers `[V]`
```
 L1  AGENT      tamias-agent (TUI/CLI)   — what the employee touches
 L2  GATEWAY    tamias proxy             — identity · spend · model · policy · the ONLY provider key
 L3  CONTAINMENT OS / network            — where the workspace fence becomes real
```

### 4.2 The two boundaries — and where each is enforced `[V]`
| Boundary | Question | Enforced by | Non-bypassable? |
|---|---|---|---|
| **Usage** | May this call happen / cost this much? | **Gateway (L2)** | **Yes** — credential lives only there |
| **Workspace** | May this action touch this file/tool? | **Agent (L1)** + **OS (L3)** | **Only with L3** |

**The single most important verified fact:** the gateway only meters
`POST /v1/chat/completions` (plus the responses/messages adapters). It **never
sees tool calls or file paths** (`tamias/src/tamias/proxy.py`, `METERED_PATHS`). `[V]`
Therefore the tool/path boundary is **client-side by construction**, and no
amount of gateway logic can make it non-bypassable. That requires an OS sandbox
(L3) or server-side tool execution. `[O]`

### 4.3 The trust tiers `[V]`
- **T0 prompt / `AGENTS.md`** — read by the model, *not* enforced. Never counts.
- **T1 local policy** (`agent.py` dispatch gate, `--policy FILE`) — fast-fail UX;
  **bypassable** (edit the TOML, edit `agent.py`, pass `--unbounded`, or use
  another client).
- **T2 managed mode** (`--require-proxy` → gateway `GET /policy`) — policy is
  served, signed (Ed25519), project-bound, expiring.
- **T3 the gateway itself** — per-key `project`, `models`, `budget_usd`,
  `rpm/tpm`, revocable; **the only holder of the provider credential**.
- **T4 OS / network** — egress to gateway only; no provider key on the machine;
  sandbox.

**"Employees cannot bypass it" = T3 + T4.** The agent (T1/T2) is the *visible,
fast-failing* fence; it *shows* the boundary. It cannot, by itself, enforce it. `[O]`

---

## 5. The surfaces (components), with evidence

| Surface | Where | Entry | Notes |
|---|---|---|---|
| Agent core | `tamias-agent/agent.py` (~2,770 lines) `[V]` | `python agent.py` | chat loop, tools, policy gate, managed mode, ledger |
| Terminal UI | `tamias-agent/tui/` (`app.py` ~1,035 lines + 10 modules) `[V]` | `-m tui.app` / default interactive | Textual 8.2.8 + Rich 15.0.0 `[V]` |
| Gateway | `tamias/src/tamias/proxy.py` | `tamias serve --upstream … --port 8000` | meters/enforces, serves policy `[V]` |
| Dashboard | `tamias/src/tamias/dashboard.py` | `python -m tamias.dashboard --db …` | local web page, replay/compare `[V]` |
| Admin CLI | `tamias/src/tamias/cli.py` | `tamias admin key …` / `manifest …` | mint keys, sign policies `[V]` |
| Benchmark | `tamias-agent/bench.py` (~412 lines) `[V]` | `python bench.py` | cost-per-success, decision gate |
| Offline quality | `brief.py` (~198), `context_index.py` (~289) `[V]` | `agent.py --brief` | D13 / D14, zero model calls |
| Demo | `tamias-agent/demo/` + `company/` + `policies/` `[V]` | various | mock provider, boundary acts |

### 5.1 Gateway capabilities `[V]`
- **Metering:** `/v1/chat/completions`, `/v1/responses`, `/v1/messages`; **never
  stores prompt or response text** (`CONTRACT.md`). `[V]`
- **Pricing:** price sheets; `compute_cost` with strict rules — unknown token
  fields ⇒ `usd=None` (never 0); free models ⇒ 0.0 with an explicit formula. `[V]`
- **Routing:** `STAY`/`SWITCH` decisions; `shadow` (log what it *would* do) vs
  `active` (rewrite, opt-in, fail-closed). `[V]`
- **Budgets:** reserve-then-settle; `budget_usd`+`period_days` (402), per-model
  `model_caps` (402), `rpm`/`tpm` (429); unknown cost charged the ceiling. `[V]`
- **Keys:** `vk-<8hex>-<random>`, stored **SHA-256 only**; fields `label`,
  `project`, `models`, `budget_usd`, `period_days`, `rpm`, `tpm`, `model_caps`,
  `revoked_at`. Revocation is a timestamp (audit trail). `[V]`
- **Signed manifests:** Ed25519; canonical JSON; **`expires` required**;
  project-bound; gateway holds **only the public key**; served at
  `GET /policy`; altered/expired refused (`MANIFEST.md`). `[V]`
- **Dashboard:** self-contained local page; routed vs baseline cost; honours
  "not priced"/"n/a"; **SIMULATED PRICES banner** for simulated sheets. `[V]`
- **Store:** append-only request rows, no text; loopback-only bind. `[V]`

### 5.2 Agent capabilities `[V]`
- **TUI:** header (wordmark, spend readout, model chip), task board, boundary
  modal, model picker, slash-command palette, landing hero, responsive header. `[V]`
- **Core tools:** `read_file`, `search_in_files`, `list_directory`, `edit_file`,
  `write_file`, `run_shell`. `[V]`
- **Model tiers:** free/mid/premium (`MODEL_TIERS`, cycled with `M`). `[V]`
- **Policy gate:** `PolicyProfile` (TOML) with `[use_case]`, `[domain]` allow/deny
  terms, `[tools]` allow/deny/ask, `[run_shell]` families, `[paths]`
  `allow_write`/`deny_read`, `[audit] path`; evaluated inside `dispatch_tool`;
  `ask` escalates to a human (headless = deny, fail-closed). `[V]`
- **Secret guard** (`refuse_secret`), **policy self-protection** (agent cannot
  read/edit its own policy). `[V]`
- **Managed mode:** `--require-proxy` / `TAMIAS_REQUIRE_PROXY=1`; fetches the
  signed policy from the gateway; refuses to start without one; rejects a raw
  provider key (needs a gateway `vk-` token); refuses to run against the default
  provider URL. `[V]`
- **Default deployment fence:** `DEPLOYMENT_POLICY_PATH` / `TAMIAS_DEFAULT_POLICY`;
  `--unbounded` opts out (documented as dev-only). `[V]`
- **Behaviour fixes (uncommitted):** stop-on-block (first deliberate refusal
  ends the turn), blocked ≠ ready (never a fake "100%"), one boundary modal per
  turn, savings note, `--task` unbounded unless a policy is given. `[V]`
- **429 handling:** `is_rate_limit_error`; a clean "provider limit" panel instead
  of a boundary block or a false completion. `[V]`

### 5.3 CLI flags (agent) `[V]`
`--task`, `--policy`, `--require-proxy`, `--unbounded`, `--company-id`,
`--task-id`, `--assignee`, `--brief`, `--tui`, `--plain`, `--max-steps`,
`--max-prompt-tokens`, `--max-task-cost`.

### 5.4 The three offline tools `[V]`
- **`brief.py` (D13):** elaborates a terse brief ("fix it") into a grounded plan
  **before** the first model call — names what is missing, states assumptions,
  cites real files, scores ambiguity. **No model call.** `[V]`
- **`context_index.py` (D14):** offline symbol/name/content index that returns
  **mandatory citations** (`path` or `path:line`); never invents a reference;
  ripgrep with a pure-Python fallback. `[V]`
- **`bench.py` (D17):** `cost_per_success = provider USD / tasks passed`; paired
  bootstrap CIs; a **decision gate** (≥20% improvement, CI lower bound > 0,
  pass-rate drop ≤ 2pp) that keeps routing opt-in otherwise. **Harness exists;
  no live run recorded.** `[V]`

### 5.5 The demo `[V]`
- `company/work/todoinc/…` (todo app + chatbot app + `hr/salaries.csv`) and
  `company/work/acme/…` (codefix bot + payments bot with `SECRET_NOTES.md` +
  `hr/salaries.csv`) — deliberately include "off-limits" targets.
- `policies/todoinc-todo.toml`, `policies/acme-codefix.toml` — real boundaries
  (domain allow/deny, tool allow/ask, shell families, path allow_write/deny_read).
- `demo/mock_provider.py` (OpenAI-compatible mock for offline full-loop),
  `demo/mock_act.sh`, boundary demo scripts, `demo/README.md`.

---

## 6. The end-to-end workflow (plain language)

**The analogy** `[O]`: give an AI agent the four things any new hire needs —
an **ID badge** (key ⇒ identity+project), an **expense card with a limit**
(budget + model allow-list), a **signed work order** (the signed policy), and a
**guard at the filing-room door** (tool/path fence). Add a **receipt printer**
(metering + audit).

**Five moves:** `[V]`+`[O]`
1. **Setup (once).** Admin declares the project, writes its policy, **signs** it,
   and **issues** an employee a key bound to that project (optionally with a
   budget/model scope).
2. **Start.** The employee runs `tamias-agent` — *or any agent* pointed at Tamias.
3. **Every model call** hits the gateway: *who → which project → which model →
   how much → allowed?* It meters and forwards. The provider key lives **only**
   here.
4. **Every action** is checked at the tool boundary: allow / deny / ask. In scope
   proceeds; out of scope is refused **and the turn stops** — never a fake "done".
5. **Report & control.** Dashboard shows true cost and routing savings; audit
   shows what was attempted; keys can be revoked or rotated instantly.

---

## 7. Integrating "inside other agents" (the distribution story)

The user's stated ambition is to embed Tamias into *existing* agents, not only
ship its own. There are **three honest depths**: `[V]`+`[O]`

| Depth | How | Governs | Limit |
|---|---|---|---|
| **1. Proxy** | Point any OpenAI/Anthropic/Responses agent's base URL at Tamias | identity, project, model, spend, metering | **tools/paths ungoverned** (gateway can't see them) |
| **2. Proxy + Tamias as an MCP server** | Agent calls tools *through* Tamias (policy-checked, audited) | + tool calls routed through you | bypassed by an agent's *built-in* tools |
| **3. Proxy + MCP + OS sandbox** | Agent runs in a locked container: project mounted, egress to gateway only | **everything** | ops-heavy; a deployment, not a `pip install` |

`ROUTES.md` lists Codex (`/v1/responses`) and Claude Code (`/v1/messages`) as
targets but marks them **UNVERIFIED** (fixture-tested, no confirmed real
traffic). `[D]` Depth 2 (an MCP boundary) **does not exist yet** and is the
single most important missing piece for the "integrate into other agents" story. `[O]`

---

## 8. What is built today (inventory with status)

**Gateway (`tamias` v0.1.0a6)** `[V]` — metering, pricing, shadow/active routing,
budgets (reserve-then-settle), company keys, **signed manifests + `/policy`**,
dashboard, store, security bind. Recent commits: D12 manifest, D2 active
routing, D10 budget, D11 keys, D3 effort. `[V]`

**Agent (`tamias-agent`, HEAD `d537a7c`)** `[V]` — TUI, tools, policy gate,
managed mode, default deployment fence, stop-on-block / blocked≠ready, 429
handling, the three offline tools (D13/D14/D17). **Working tree has uncommitted
changes** (modified: `.gitignore`, `agent.py`, `test_agent.py`,
`test_tui_features.py`, `tui/app.py`, `tui/modals.py`, `tui/tasks.py`;
untracked: `company/`, `demo/`, `policies/`). `[V]`

**Tests** — `tamias-agent`: **264 tests collected** in
`test_agent.py` + `test_tui_features.py` `[V]` (the older handoff cited 239; the
suite has grown). `tamias`: cited as **616 tests**, ruff clean, 0 xfail/xpass at
the time of the 2026-10-06 handoff `[D]`.

**Historical state (from `../HANDOFF-CODEX.md`, dated 2026-10-06)** `[D]`:
that document describes a merge of five clones into `tamias` main; a
"Demo ~92% / Package ~60%" scoreboard; and an old architecture (observer / lab /
controller) rated **3 of 23 freeze items (~15%)** implemented while
`CONTRACT.md` was ~85% implemented. **Caution:** it predates the current
governance work and states `agent.py` = 1,267 lines, which is now ~2,770 — treat
it as history, not current truth. `[V]`/`[O]`

---

## 9. What is **not** built (the gap list)

| # | Gap | Why it matters | Where it belongs |
|---|---|---|---|
| G1 | **First view shows no identity / provenance / tier / expiry** — today the header is wordmark + spend + model, and "enforced" is inferred from `--company-id` presence (a *local* run can say "enforced") `[V]` | the user cannot see *who* they are, *what* binds them, or *whether it is real* | `tui/` (pure UI, offline-testable) |
| G2 | **No managed-only production posture / no pinned config** — an employee can edit `agent.py`, pass `--unbounded`, use `--policy`, **or run their own gateway** and serve a permissive policy `[V]` | the client-side fence is bypassable | `agent.py` + launcher/MDM |
| G3 | **No teams / employees / assignments** — gateway keys have `label`+`project` only; no user/team/registry tables `[V]` | "the team declares the project, assign employees" is not modelled | gateway control plane |
| G4 | **No project-declaration workflow** — manifests can be signed `--project`, but there is no registry of projects `[V]` | teams must hand-roll config | gateway |
| G5 | **No `[network]` egress allow-list** — documented in a proposal, **not implemented** `[V]` | the workspace boundary can be escaped | `agent.py` |
| G6 | **No OS sandbox** — best-effort shell guard only (`agent.py` comment: "Shell cannot be fully sandboxed from pure Python") `[V]` | "cannot bypass" is not yet true | packaging / IT |
| G7 | **Audit is local JSONL** (deletable by the employee); the tool-level trail is not authoritative `[V]` | evidence can vanish | gateway/sidecar + off-box shipping |
| G8 | **No team coordination** (shared board / handoffs); the task board is per-session `[V]` | "whole team coordination" is absent | new |
| G9 | **No MCP boundary server** (integration depth 2) `[V]` | cannot govern other agents' tools | new |
| G10 | **No live benchmark result** (`bench.py` unrun) `[V]` | the economics pillar is unproven | run it |
| G11 | **Live model path is rate-limited** (OpenRouter free tier, 50/day) — demo risk; the live gate passed twice on 28 Oct 2026 (tool call + visible switch, $0.0000), but quota can still fail on stage; a mock provider exists as a workaround `[V]` | demos must not over-claim a live run | ops |

---

# Part II — Independent Take `[O]`

> Everything in this part is judgement, clearly marked. It is meant to be argued
> with, not obeyed.

## 10. Is it unique? Honestly: the category is not; the combination is

The 2026 landscape (web-checked during this review) `[V]`:
- **Enterprise AI gateways:** LiteLLM, Portkey, Cloudflare, Kong, Bifrost/Maxim,
  TrueFoundry — these own **usage** (meter/route/cap).
- **AI governance platforms:** Credo AI, Microsoft Purview, OneTrust, Domo,
  Speakeasy, Runlayer, MintMCP — mostly **advisory/compliance**.
- **MCP tool-boundary enforcement:** **Microsoft Agent Governance Toolkit (AGT)**
  (open-source, MIT, April 2026) and academic PEP work — these own **actions**
  (tool-call interception).
- **Observability:** Langfuse, Helicone, LangSmith.

**Verdict.** Every *half* of Tamias has a large incumbent. What has no clear
incumbent is the **union**: one local, agent-agnostic plane that does
**usage + actions**, with a **signed, project-bound policy**. And there is one
documented, specific gap Tamias already fills: the **MCP spec (and its 2026
roadmap) is silent on manifest pinning** — "teams will have to build it"
(InfoQ, Jul 2026). Tamias's Ed25519 signed, expiring, project-bound manifest
verified with a public key only *is* manifest pinning. `[V]`/`[O]`

So: **not unique as a category, genuinely differentiated as a combination and a
trust model.** The differentiators, ranked:
1. **Signed + pinned, project-bound policy** (the acknowledged MCP gap).
2. **Unified usage + action governance in one local plane.**
3. **`cost_per_success`** as the metric (not raw cost).
4. **Radical honesty** (`n/a` ≠ 0, `UNKNOWN` ≠ 0, simulated banners, "show which
   regime you're in") — a real differentiator in a field of inflated claims. `[O]`

## 11. Will it work? By claim, not by vibe

| Claim | Verdict | Needs |
|---|---|---|
| "See/cut what the agent costs" | **Works** (proven category) | already built; win on *cost-per-success* + honesty |
| "The policy can't be edited away" | **Works today** | signed manifest + expiry + public-key-only gateway (built) |
| "The employee can't bypass it" | **Only with work** | pinned config + client-side signature check + no provider key + egress control (G2, G5) |
| "The agent can't touch the wrong files" | **Not yet** | MCP/action layer **or** OS sandbox (G6/G9) — the gateway cannot do it |
| "Cheaper per success, proven" | **Designed, not shown** | run `bench.py` (G10) |

## 12. The pivot (the one big idea)

**Stop being an agent; become the boundary that every agent runs inside.**
"Tamias = the agent firewall" — a signed, verifiable envelope (identity + spend +
scope) that any agent must pass through, that runs locally, and that tells the
truth about what it enforced. That is a category (firewalls are a category);
"our agent refuses off-topic prompts" is a feature in a field of fifty. `[O]`

## 13. What to keep / cut / add / moderate `[O]`

**Keep**
- The signed, expiring, project-bound manifest and the public-key-only gateway —
  the strongest, most defensible asset.
- The honesty invariants as the brand.
- `cost_per_success` + the benchmark methodology.
- The offline tools (brief/context) — teaching "spend fewer tokens" is on-thesis.
- `tamias-agent` as the **reference client** and the clean demo.

**Cut**
- Competing as a coding agent. Keep the TUI as reference, make the gateway the
  product.
- Building a full IAM/team directory. Integrate with SSO/Okta; keep local keys
  as fallback (the gateway already has `label`+`project` — enough for an MVP).
- Per-tiny-use-case policy sprawl (one policy per project, parameterised).
- Duplicating gateway features that LiteLLM/Portkey already do, unless the trust
  axis is the differentiator.

**Add**
- The **MCP boundary server** (integration depth 2) — the "inside other agents"
  story and the clearest differentiator vs the gateways.
- **Client-side manifest verification / pinned gateway** — closes "bring your own
  gateway".
- **Egress allow-list + a documented sandbox recipe** (depth 3) — makes the claim
  honest.
- The **first-view provenance** (identity/tier/project/expiry).
- A **"why not LiteLLM + a system prompt?"** one-pager.
- The **live benchmark result**.

**Moderate**
- Scope the revolution: pick a beachhead (security-conscious engineering teams
  that must *prove* what agents touched) rather than "everyone".
- Qualify "cannot be bypassed" until depth 3 ships; sell "governed + visible"
  until then. Over-claiming is the one thing that would kill a trust-based brand.
- Apply the architecture's own **freeze rule**: any new scope must remove scope.

## 14. Risks that could kill it `[O]`
1. **Category confusion** (cost tool? governance tool? agent?) — pick one headline.
2. **The L3 gap** — promising non-bypassability without containment; a
   reputational risk amplified by the honesty brand.
3. **Distribution friction** — developers won't route through a proxy unless it
   is frictionless (depth 1 must be one line of config).
4. **Big-player convergence** — Microsoft AGT, Cloudflare, Kong are moving into
   exactly this space.
5. **Thin moat** — "just a proxy" is easy to copy; the signed-policy + MCP +
   benchmark + honesty combination is not.
6. **Mis-positioning the demo** as the product.

## 15. A prioritized path (proposal, not a commitment) `[O]`
- **Phase 0 — Position.** One-page "what it is / is not" + "why not
  LiteLLM + system prompt". Decide north-star and beachhead.
- **Phase 1 — Make the reference client airtight + first view** (G1, G2;
  largely offline-testable). *Mostly done.*
- **Phase 2 — The integration layer** (G9 + depth-2 MCP boundary) — the
  revolution: any agent becomes governed.
- **Phase 3 — Client-pinned manifest + L3 containment** (G5, G6) — makes
  "cannot bypass" true.
- **Phase 4 — Economics proof** (G10 live benchmark) + dashboard story.
- **Phase 5 — Identity/teams via SSO integration** (G3, G4, G8), not reinvention.

## 16. Open decisions (needed before any final plan)
1. **North star:** governance fabric (agent firewall) **or** economics
   (cheapest path to results)? They share the gateway but diverge fast.
2. **Beachhead:** the security team (needs auditability) **or** the eng lead
   (needs lower spend)?
3. **Depth:** commit to depth 3 (sandbox ⇒ "cannot bypass") **or** stay at
   depths 1–2 and sell "governed + visible" honestly?

---

# Part III — Reference

## 17. Glossary
- **Use-case policy:** the TOML fence (tools/paths/shell/domain/models) for one
  product. `[V]`
- **Dispatch gate:** the single point in `dispatch_tool` every tool call passes
  through. `[V]`
- **Managed mode:** agent fetches its signed policy from the gateway and refuses
  to run without it (`--require-proxy`). `[V]`
- **Manifest:** canonical-JSON policy + Ed25519 signature; required expiry;
  project-bound; gateway holds public key only. `[V]`
- **Key (`vk-`):** hashed per-caller credential carrying project/models/budget/
  rates/revocation. `[V]`
- **Reserve-then-settle:** budget is reserved (ceiling) before the call and
  settled to actual cost at log time. `[V]`
- **cost_per_success:** provider USD ÷ tasks that passed. `[V]`
- **Shadow routing:** log the decision it *would* make, without changing the
  request. `[V]`

## 18. Key file map
| Path | Role |
|---|---|
| `tamias-agent/agent.py` | agent core, tools, policy gate, managed mode, ledger |
| `tamias-agent/tui/app.py` + 10 modules | TUI (theme, turns, tools, board, modals) |
| `tamias-agent/brief.py` / `context_index.py` / `bench.py` | D13 / D14 / D17 |
| `tamias-agent/policies/*.toml` | the deployment boundaries |
| `tamias-agent/demo/*` | offline boundary acts + mock provider |
| `tamias-agent/company/work/…` | the fake company workspace (incl. secrets to trip on) |
| `tamias/src/tamias/proxy.py` | the gateway (metering/enforcement, `/policy`) |
| `tamias/src/tamias/keys.py` | company keys (identity/model allow-list) |
| `tamias/src/tamias/budget.py` | reserve-then-settle, caps, rates |
| `tamias/src/tamias/manifest.py` | Ed25519 sign/verify |
| `tamias/src/tamias/dashboard.py` | local dashboard |
| `tamias-agent/docs/BOUNDED-AGENT.md` | governance design + build order |
| `tamias/docs/ARCHITECTURE.md` | the (older) economics research baseline |
| `HANDOFF-CODEX.md` | 2026-10-06 merge handoff (historical) |

## 19. Commands (current)
```bash
# agent tests (the two suites share one process)
cd /home/krish/Desktop/tamias-agent
.venv/bin/python -m pytest test_agent.py test_tui_features.py -q   # 264 tests

# run the agent on one task
.venv/bin/python agent.py --task "..." --policy policies/todoinc-todo.toml

# the gateway + dashboard
tamias serve --upstream <base> --prices prices.toml --db requests.db --port 8000
python -m tamias.dashboard --db requests.db --prices prices.toml --port 8010

# mint a key / sign a policy
tamias admin key issue --label alice --project todoinc --model <m>
tamias admin manifest sign --project todoinc --expires <date>

# offline full-loop demo (no network)
./demo/mock_act.sh --company-id todoinc --policy policies/todoinc-todo.toml
```

## 20. What was verified vs assumed (for the researcher)
- **Verified in source/docs this session `[V]`:** agent line counts, TUI module
  list, CLI flags, policy TOMLs, gateway `METERED_PATHS` (no tool awareness),
  key fields, manifest rules, budget rules, dashboard behaviour, `cost_per_success`
  gate, test count (264), git status, tamias version `0.1.0a6`, the two
  architecture docs.
- **Documented, not re-verified `[D]`:** tamias 616-test count, Tier B live
  rehearsal claims, Codex/Claude Code route verification, the HANDOFF scoreboard.
- **Opinion `[O]`:** uniqueness, feasibility verdicts, the pivot, keep/cut/add,
  risks, roadmap, open decisions.
- The 2026 competitive landscape was web-checked (gateways, governance
  platforms, Microsoft AGT, MCP manifest-pinning gap).

---

*End of brief. If you are a research model reading this: the single sentence to
carry forward is — **the agent shows and fast-fails the boundary; the gateway
governs identity, model and spend; only OS/network containment makes the
workspace boundary non-bypassable.** Everything else is detail.*
