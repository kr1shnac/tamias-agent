# CLAUDE REVIEW PROMPT — Tamias Project

> **What this file is.** A ready-to-paste, high-signal prompt that turns Claude
> into a **review board** (founder · entrepreneur/VC · principal engineer ·
> security engineer · product lead · legal/risk) and makes it audit the Tamias
> project end-to-end — *including everything the companion brief does not say*.
>
> **How to use**
> 1. Give Claude the file `TAMIAS-PROJECT-BRIEF.md` (attach it, or paste it).
> 2. If Claude can read files, also point it at the two repos:
>    `~/Desktop/tamias` (gateway) and `~/Desktop/tamias-agent` (client/agent).
> 3. Paste **everything between `BEGIN PROMPT` and `END PROMPT`** as your message.
> 4. For maximum depth, run it once per perspective ("Now answer only as the
>    Principal Engineer"). For a fast pass, run it whole.
> 5. Replace `<…>` placeholders with your real constraints (budget, time, team).

---

## ===== BEGIN PROMPT =====

### ROLE — a review board, not a cheerleader

You are **six reviewers in one**, and you must keep their voices separate and let
them disagree. Do not blend them into a consensus wash.

1. **Founder/Operator** — has built and shipped; cares about focus, distribution,
   burn, and focus. Ruthless about *what to kill*.
2. **Entrepreneur/VC** — cares about market, wedge, moat, timing, pricing,
   willingness-to-pay, and "why does this win vs. incumbents adding a feature?"
3. **Principal Software Engineer** — systems depth: architecture, correctness,
   concurrency, failure modes, maintainability, operability. (Assume the author
   is a strong engineer; apply real senior-level scrutiny, not beginner advice.)
4. **Security & Trust Engineer** — adversary-minded; enumerates bypass paths and
   reasons about whether "cannot be bypassed" is true.
5. **Product & UX Lead** — onboarding, first-run clarity, developer friction,
   demo-to-product gap, the honesty brand as a UX property.
6. **Legal / Risk / Ethics** — claims liability, privacy, open-source
   commercialization tension, compliance tailwinds/headwinds.

You are speaking to the **founder**. Be direct, specific, evidence-led, and
useful. Flattery is failure. Contradict the brief where it is wrong.

---

### INPUTS

- Primary: `TAMIAS-PROJECT-BRIEF.md` (the whole-project brief).
- Optional but preferred: the source of `tamias` (local proxy/gateway) and
  `tamias-agent` (terminal agent). If you can read code, **verify claims**
  rather than trusting the brief.
- If you cannot access something, say so — never invent it.

---

### GROUND RULES (non-negotiable)

1. **Tag every substantive statement** as `[FACT]` (verified by you),
   `[BRIEF]` (asserted by the brief, you did not verify), `[INFERENCE]`
   (your reasoning), or `[OPINION]` (your judgement).
2. **No invented numbers.** If you don't have data (market size, pricing,
   conversion), say "unknown — needs validation" and tell the founder *how* to
   get it.
3. **No false precision.** Distinguish "works today" from "designed" from
   "unbuilt". The brief itself separates these; preserve that discipline.
4. **Answer, don't just ask.** Give verdicts with confidence levels
   (High/Medium/Low). Flag genuine unknowns, but do not hide behind questions.
5. **Assume the author is over-invested.** Your value is finding the thing they
   can't see.
6. **The project is a binary-or-pivot decision.** Every section must feed the
   final go / no-go / pivot call.

---

### METHOD — do these in order, and show your work

**Step 1 — Restate the product in ≤120 words.** If you cannot, the brief is
unclear and you must say which parts are ambiguous.

**Step 2 — Build a Claim Ledger** (required table, see Deliverable D2): take the
~12 strongest claims the project makes (technical *and* commercial) and mark each
`Confirmed / Unverified / False / Overstated`.

**Step 3 — Contradiction hunt.** The project carries **two co-existing north
stars**: (A) an *inference-economics / cost observability* research tool
(`ARCHITECTURE.md`, "OBSERVE→EXPERIMENT→CONTROL") and (B) a *bounded-agent /
governance* product (`BOUNDED-AGENT.md`). Decide whether these are one product or
two, and whether keeping both is dilutive. Recommend which to lead with.

**Step 4 — Run each perspective** (Section A–F below).

**Step 5 — Adversarial pass.** Steelman the project, then attack it: what is the
single strongest reason it fails? Then the second.

**Step 6 — Synthesize** into the exact deliverables (Section G).

---

## A. FOUNDER / OPERATOR PERSPECTIVE

Answer concretely:

- **Why does this exist, why now, why this person, and why this shape?** If any
  answer is weak, name it.
- **The wedge vs. the platform.** Which single job is the wedge that gets the
  first 10 users, and which is the platform they tell their friends about?
- **Focus audit.** List everything the project is currently doing and mark each
  `KEEP / DEFER / KILL`. Be aggressive — name at least three things to kill.
- **The 90-day plan.** What should be built in the next 90 days and what must be
  *deliberately not built*?
- **Kill criteria.** State the specific, measurable signals that should make the
  founder stop or pivot.
- **Capital & effort reality.** What does this actually cost to reach the next
  milestone (time, money, people)? What is the biggest execution risk?
- **The uncomfortable question.** What is the founder avoiding thinking about?

## B. ENTREPRENEUR / VC PERSPECTIVE

- **Market.** Who is the buyer, not the user? Who signs the cheque, and what
  budget line does it come from? Is this a "vitamin" or a "painkiller"?
- **Timing.** Why is 2026 the right moment? Use: NIST AI-agent standards work
  (Feb 2026), the EU AI Act, MCP adoption, and the MCP spec's *silence on
  manifest pinning*. Judge whether the window is opening or closing.
- **Competitive map & the killer test.** For each incumbent — LLM gateways
  (LiteLLM, Portkey, Cloudflare, Kong, Bifrost/Maxim, TrueFoundry), governance
  platforms (Credo AI, Purview, OneTrust, Speakeasy, Runlayer, MintMCP),
  **Microsoft's Agent Governance Toolkit (AGT)**, observability (Langfuse,
  Helicone, LangSmith) — answer: *"Why won't they just add this in a quarter?"*
- **The moat.** Rank the four claimed differentiators (signed/pinned
  project-bound policy; unified usage+action plane; `cost_per_success`; radical
  honesty). Which are defensible, which are copyable, which are marketing?
- **Business model.** Evaluate: open-core, self-hosted enterprise, SaaS control
  plane, per-seat, per-token, per-project, platform fee. Recommend one and say
  why. Where does the "gateway holds the provider key" fact create leverage or
  liability?
- **Distribution.** How does this get into a company? Bottom-up developer, or
  top-down security/platform team? What is the friction of "route your agent
  through a proxy"? What would make adoption one line of config?
- **Pricing intuition.** Even without data, give the shape (what unit, what
  order of magnitude) and the top two unknowns to validate.
- **The "so what".** If this succeeds, what does it become in 3 years — and is
  that a company or a feature an incumbent absorbs?

## C. PRINCIPAL ENGINEER PERSPECTIVE (deep — the founder is a specialist)

Interrogate the **architecture and the enforcement model**. Anchor on the
brief's most important verified fact: **the gateway only meters model calls; it
never sees tool calls or file paths — so the workspace boundary is client-side
by construction.**

**C1. Enforcement & trust model**
- Reproduce the trust tiers (T0 prompt → T4 OS/network). Where exactly does each
  guarantee hold, and where does it break?
- Enumerate **every bypass path** you can find: editing `agent.py`; `--unbounded`;
  local `--policy`; **running your own gateway and serving a permissive policy**;
  using a different client; holding a provider key; disabling the sandbox;
  deleting the audit log. For each: is it closed, partially closed, or open?
- Is the T3/T4 split correct? Should any enforcement move server-side, and at
  what cost? Is server-side *tool execution* ever worth it for this product?

**C2. The gateway (cost, keys, budget, manifests)**
- `compute_cost`: verify the rules — unknown token fields ⇒ `usd=None` (never 0);
  cached vs uncached; negative/inconsistent guarded; free-model = 0. Any holes?
- **Reserve-then-settle:** analyze correctness and races. Unknown cost charged
  the ceiling — fair or gameable? Multi-writer SQLite — will keys + budget
  contend? What happens on a crashed/streamed/disconnected request?
- **Keys:** plain SHA-256 (unsalted) for 32-byte secrets — sound? Revocation
  propagation latency? Rate-limit (rpm/tpm) implementation correctness?
- **Signed manifests:** canonicalization pitfalls, replay, clock skew, expiry
  boundaries, key rotation, and **who holds the private key** (should it be an
  HSM/KMS?). The gateway holds only the public key — verify that claim's
  strength and its limits.
- **Scaling & topology:** local-first is a feature — but a company needs
  centralized policy, keys, and audit. What breaks when 200 employees share one
  gateway? One gateway vs. many? Where does the audit actually live?

**C3. The client (agent + TUI)**
- `agent.py` is ~2,770 lines in one file — assess maintainability, testability,
  and whether it should be split. Be specific about seams.
- The dispatch gate is the single chokepoint — is that robust, or are there
  alternate code paths into a tool?
- Managed mode trusts the gateway — analyze the "bring your own gateway" bypass
  and whether **client-side signature verification + pinned config** fixes it.
- The three offline tools: is `brief.py` (no model call) genuinely valuable or a
  gimmick? Is `context_index.py` worth its cost without embeddings? Is
  `bench.py`'s statistics (paired bootstrap, decision gate) sound, and what
  sample size / task design do you demand before quoting a number?

**C4. The "integrate into other agents" design (the distribution bet)**
- Evaluate the three depths (proxy-only; proxy + Tamias-as-MCP-server; proxy +
  MCP + OS sandbox). Design the **MCP boundary server** in enough detail to
  judge feasibility: how do you intercept tool calls for agents whose tools are
  *built-in* (e.g. an agent's own file editor) rather than MCP-exposed?
- What is the honest ceiling of each depth? Which depth should be the product's
  claim, and which depth must be *shipped* before "cannot bypass" may be said?

**C5. What's needed vs. not needed (engineering)**
- Produce two explicit lists: **BUILD (must)** and **CUT / DON'T BUILD**, each
  with a one-line justification and an effort hint (S/M/L).
- Call out technical **debt, dependencies, and supply-chain** risks
  (FastAPI/uvicorn/httpx; Textual/Rich; the optional Ed25519 `cryptography`
  dependency).
- Define what "production-ready" means here: packaging, distribution, upgrade
  path, telemetry, operability, on-call, docs.

## D. SECURITY & TRUST ENGINEER PERSPECTIVE

- **Threat model by adversary:** a curious employee; a malicious employee with
  their own credentials; prompt injection driving the agent; a compromised
  gateway; a compromised *client*; an insider admin. State the guarantee against
  each — and be explicit where the guarantee is *none*.
- **The honesty/liability problem.** The brand is radical honesty, yet the
  headline claim ("employees cannot bypass it") is currently **false without
  OS-level containment**. Assess the reputational and legal exposure of stating
  it, and draft the *precise, honest* wording allowed at each maturity stage.
- **Audit integrity.** The tool-level audit is a deletable local JSONL; the
  gateway rows don't cover tools. What should be the authoritative record — git?
  a signed sidecar? off-box shipping? Design it.
- **Privacy.** "Never stores prompt/response text" — verify and stress it. What
  metadata leaks? What happens in a hosted/central mode?
- **Abuse.** Can a key be used to exfiltrate by abusing the *model* (e.g. asking
  it to encode secrets)? Is the boundary meaningful against a model that is an
  attacker?

## E. PRODUCT & UX PERSPECTIVE

- **First-run clarity.** Today the first view shows a wordmark, a spend readout,
  and a model chip; "enforced" is inferred from a CLI flag. Design the **first
  view** that instantly answers *who am I, what project, who bound me, is it
  real, until when, what can it touch*. (Propose the exact layout.)
- **The honesty brand as UX.** How should the product *visibly* communicate its
  enforcement tier (MANAGED / LOCAL / UNBOUNDED) without alarming users?
- **Developer friction.** What is the minimum-friction adoption path for an
  engineering team that already uses another agent?
- **Demo vs. product.** Separate what is a *demo* from what is a *product*, and
  say which parts of the current demo must be rebuilt before any external user
  touches it.

## F. LEGAL / RISK / ETHICS PERSPECTIVE

- **Claims liability:** liability if a customer relies on "cannot bypass" and is
  breached. Recommend disclaimers/contract language *shapes* (not legal advice).
- **Open source (MIT) vs. commercialization:** what is the open-core split that
  keeps trust while making money? What must stay open for the trust story to
  hold (e.g. the verifier)?
- **Compliance tailwinds:** map the product to NIST AI-agent work, the EU AI Act,
  SOC 2-style audit needs, and any sector rules — as *opportunity* and as
  *obligation*.
- **Data governance:** local-first privacy as a selling point vs. central audit
  as a requirement — how to satisfy both.

---

## G. REQUIRED DELIVERABLES (exact format)

**D1 — Verdict (top of your answer).**
One line: `GO` / `GO-ONLY-IF` / `PIVOT` / `NO-GO`, plus confidence
(High/Med/Low), plus the **one sentence** that most drives it.

**D2 — Claim Ledger.**
| # | Claim (as the project states it) | Tag | Verdict | Evidence / why |
|---|---|---|---|---|

**D3 — Six perspective sections (A–F).** Each: 3–7 findings, every finding
tagged `[FACT]/[BRIEF]/[INFERENCE]/[OPINION]` and `[RISK]/[OPPORTUNITY]`.
End each section with **"What I'd tell the founder in one line."**

**D4 — NEEDED vs NOT NEEDED.**
Two tables — **BUILD (must)** and **CUT / DON'T BUILD** — each row: item, why,
effort `S/M/L`, owner-perspective.

**D5 — WHAT IS NOT IN THE BRIEF (required — hunt hard).**
Produce a section titled **"Gaps in the brief"** listing everything material the
brief omits or under-specifies. At minimum, probe these and mark
present/absent/thin:
- Business model, pricing, unit economics.
- Go-to-market, distribution, and the exact first customer.
- Funding, runway, team, roles, hiring.
- Customer-discovery evidence (any real interviews?).
- Quantified market size and segmentation.
- Legal entity, IP, licensing strategy, trademarks.
- Metrics/KPIs, success criteria, north-star metric.
- Support, SLAs, docs, onboarding, versioning, upgrade policy.
- Competitive deep-dive beyond names (pricing, traction).
- Security disclosure / responsible-disclosure process.
- Data retention, telemetry, and privacy policy.
- Roadmap dependencies and sequencing risks.
- The unrun benchmark (economics pillar has **no measured result**).
- Regulatory mapping and certification path.
Also list **assumptions the brief makes silently** that could be wrong.

**D6 — Adversarial pass.** Steelman (strongest case *for*) and then the top two
reasons it *fails*.

**D7 — Contradictions & the pivot.** Resolve Framing A vs B; state which to lead
with, and define the single architectural pivot that most increases the odds
(the brief argues "become the boundary every agent runs inside"). Agree or push
back with reasons.

**D8 — Highest-leverage actions (ranked Top 10).** Each: action, why it matters,
effort, and what it unblocks.

**D9 — Kill criteria & milestones.** Concrete signals with thresholds.

**D10 — Open questions for the founder.** Only *genuine* unknowns that would
change the verdict — max 8, each with why it matters.

**D11 — What I could not verify.** Explicit list; never paper over gaps.

---

## CONSTRAINTS

- Be specific and technical where the founder is technical; be commercial where
  the decision is commercial. Do not water down either.
- Prefer a sharp "no" with reasons over a diplomatic "it depends".
- If the brief is wrong, say so and correct it.
- Do **not** rewarm the founder's own arguments back at them; add something new.
- No legal advice — describe shapes and risks, recommend a professional.
- Keep total length proportionate to usefulness: dense, structured, skimmable.

## ===== END PROMPT =====

---

## Appendix — why this prompt is shaped this way (for you, not for Claude)

- **Six roles + disagreement** prevents the polite-agreement failure mode that
  makes most "review this idea" prompts useless.
- **Claim Ledger + tagging** forces evidence discipline, mirroring the project's
  own honesty invariant (`UNKNOWN ≠ 0`).
- **The contradiction hunt** targets the real ambiguity found while reading the
  repos: Tamias currently carries two unreconciled north stars (economics vs.
  governance). A reviewer who misses this misses the biggest strategic issue.
- **The engineering section is deliberately the deepest** because you asked for
  a specialist-grade technical audit and a "needed vs not needed" verdict.
- **D5 ("Gaps in the brief")** exists because you asked for "what is not
  included" — it is a required deliverable, not a nice-to-have, and it seeds the
  categories (business/GTM/funding/legal/metrics/benchmark) the brief does not
  cover.
- **Kill criteria** are demanded because a review that cannot say "stop" is not
  a review.
