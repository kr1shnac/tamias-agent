# The Premium Agent

**Tamias product thesis and experience architecture — 28 October 2026**

This document answers one question: what would make Tamias feel like a premium
agent rather than a competent one? It is deliberately about the user, not the
feature list. The feature list follows from the user's inner monologue.

The short answer:

> **Tamias is the accountable agent. Its luxury is certainty.**
>
> Not "the fastest agent", not "the agent with the most tools", not "the agent
> that looks like a chatbot". The agent you can put in front of a staff
> engineer, a client, or a compliance review and say: *here is what it did,
> here is why, here is what it touched, here is what it cost, and here is how
> to undo it.*

The first premium slice is built and tested: the **Boundary Card**, the
**Receipt**, and the **Decision Card**. The second slice's views are also built:
the **Plan Card** and the **Investigation Dossier**. The rest of this document
explains why those are the right first surfaces, what comes next, and what not
to build.

---

## 0. The decision in one page

| Decision | Recommendation | Why |
|---|---|---|
| **Positioning** | The accountable agent | The field competes on autonomy and speed; nobody makes the audit trail the interface. It is defensible with Tamias's policy, cost and audit substrate. |
| **Premium definition** | Certainty, control, continuity, craft, candor | Premium is the removal of uncertainty, not the addition of features. |
| **First signature** | Boundary Card + Receipt + Decision Card | They use data Tamias already has, are demoable in one turn, and make the governance story visible without a slide. |
| **Second signature** | Plan Contract + Investigation Dossier + Time Travel | The senior-engineer ritual: investigate, propose, approve, execute, rewind. Signed plans, file-drift enforcement, the dossier view, the pre-write dossier gate and file rewind are built; conversation rewind and durable checkpoints are next. |
| **Long-term moat** | Project Brain + Flight Recorder + Handoff | Memory and proof compound; a competitor can copy a modal, not an operating record. |
| **Primary surface** | Terminal-first TUI, with shareable receipt/export later | The terminal is the identity and the constraint. The receipt can travel outside it. |
| **Autonomy model** | Plan-first, then a Trust Dial (Observe / Propose / Act / Auto) | One control the user understands; policy caps it underneath. |
| **Target user** | Staff engineer / tech lead at a 20–200 person company with real review or compliance pressure | They feel the pain of black-box autonomy and can pay for certainty. Individual developers are the adoption wedge. |
| **What not to build** | A chat-first clone with more tools | It would lose to Claude Code, Codex and OpenCode on their terms. |

The one-sentence product promise:

> **"You will never have to wonder what your agent did."**

Every surface should be judged against that sentence. If a feature does not
remove a question the user would otherwise ask, it is not premium; it is
decoration.

---

## 1. What "premium" actually means

Premium is not a colour palette, a serif font, or a higher price. In tools, it
is a specific feeling: **the product is calm, precise, prepared, and on your
side.** It respects your attention. It does not make you babysit it, and it does
not make you look foolish in front of your team.

A premium agent has ten properties:

1. **It answers the next question before you ask it.** "What did it do?" "Can I
   undo?" "What did it cost?" "Why did it stop?" "Will it remember?"
2. **It is quiet when nothing needs you.** No token waterfall, no cheerful
   filler, no fake progress. Silence is a feature.
3. **It is loud at the right moment.** A boundary, a decision, a failure, a
   completion. The user's attention is spent only where it changes an outcome.
4. **It makes the user feel capable, not stupid.** No unexplained modes, no
   magic, no "trust me".
5. **It has a point of view.** It says no. It refuses off-topic work. It has a
   boundary and it is proud of it.
6. **It is legible at a glance.** One screen tells you what is happening, what
   it costs, and what you need to decide.
7. **It is reversible where it matters.** Not every action, but the ones that
   can hurt. Undo is a promise, not a menu item.
8. **It remembers the relationship.** Your conventions, your architecture, your
   past decisions. You do not repeat yourself every session.
9. **It hands off cleanly.** The agent does not just edit; it gives you a
   reviewable change, a test record and a brief.
10. **It is honest under failure.** Rate limits, errors and cancellations are
    explained plainly; work is preserved; nothing is claimed that was not
    measured.

### The premium test

Ask these after every turn. If the answer is "the user has to ask", the product
failed:

| Question | Surface that should answer it |
|---|---|
| What is this agent allowed to touch? | Boundary Card |
| What is it about to do? | Plan Contract |
| Why is it asking me? | Decision Card |
| Is it stuck? | Quiet status / current step |
| What did it change? | Diff + Receipt |
| Did it actually work? | Verification evidence |
| What did it cost? | Receipt / spend ledger |
| Can I undo it? | Time Travel |
| Will it remember? | Project Brain |
| Can I hand this off? | Handoff brief |
| Can I prove it later? | Flight Recorder / audit export |

### Normal agent vs. premium agent

| Normal agent | Premium agent |
|---|---|
| Chat is the product | The work record is the product; chat is one view |
| "Thinking..." | "Read 14 files. Found the auth boundary at `src/auth/session.ts:42`. No writes yet." |
| Permission pop-up | Decision card with action, reason, effect, scope, audit |
| "Done!" | Receipt with files, checks, cost, risks |
| Cost is a monthly bill | Cost is a per-turn receipt and a session ledger |
| Session dies with the terminal | Resume, fork, remember |
| Undo is a git command you hope works | Time travel with a preview |
| Model picker is a puzzle | Conductor chooses, explains, and respects a budget |
| Trust is requested | Trust is demonstrated |

---

## 2. The user's inner monologue

This is the part most agent products miss. Users do not think in feature names.
They think in small, anxious questions. The interface's job is to answer them
before they become doubts.

### 2.1 The journey

| Moment | What the user asks themselves | Emotional state | What today's agents do | What Tamias should do |
|---|---|---|---|---|
| **Discover** | "What is this? Is it for me?" | Curious, skeptical | A wall of features and benchmarks | One promise, one proof, one boundary |
| **Install** | "Will this break my setup?" | Cautious | A config maze | One command, one visible policy, no hidden keys |
| **First launch** | "What can it touch?" | Apprehensive | An empty chat box | A boundary card and a three-question setup |
| **First task** | "Did it understand my project?" | Hopeful | It starts editing immediately | Investigation dossier before any write |
| **Plan** | "What will it do, and how long?" | Evaluative | It streams a plan into chat | Signed Plan Contract with files, risks and cost range |
| **Approval** | "Why is it asking me this?" | Annoyed, suspicious | Generic yes/no | Decision card with reason, effect, scope, audit |
| **Working** | "Is it stuck? Is it doing the right thing?" | Impatient | "Thinking..." or a token waterfall | Current step, evidence, elapsed time, cancel |
| **Interruption** | "Can I stop it without losing work?" | Anxious | Ctrl+C kills the turn | Steering, queue, pause, safe cancel |
| **Review** | "What did it change? Did it work?" | Skeptical | A diff and a claim | Receipt + diff + verification evidence |
| **Undo** | "Can I go back?" | Fearful | "Use git" | Time travel with preview |
| **Handoff** | "Can I show this to my team?" | Pride / stress | Manual PR write-up | Handoff brief, PR body, test report |
| **Return** | "Does it remember?" | Hopeful | Blank slate | Project Brain + session resume |
| **Audit** | "Can I prove who approved what?" | Accountable | Log file | Flight Recorder + exportable receipts |

### 2.2 The three moments that decide adoption

**Moment 1: the first boundary.**
The user asks something slightly outside the project, or the agent reaches for a
file it should not touch. A normal agent either does it or shows a scary stack
trace. Tamias shows a calm, specific card:

> "That path is outside `company/work/todoinc/apps/todo/**`. Nothing was read.
> The turn stopped. Here is the boundary."

This is the moment the user decides whether the agent is safe. It must feel
like a rule, not an error.

**Moment 2: the first receipt.**
The turn ends. Instead of "Done!", the user sees one line:

> `receipt · NEEDS REVIEW · 2 files changed · 1/1 checks passed · $0.0000 · R to open`

They press `R` and see exactly what happened. This is the moment they stop
re-checking everything. The receipt is the product.

**Moment 3: the first rewind.**
Something breaks. The user does not reach for git; they press `Z`, preview the
checkpoint from that turn, and restore the tracked files. This is the moment
they trust the agent with more autonomy.

### 2.3 What users never say out loud

- "I don't want to babysit it; I want to be able to prove I didn't have to."
- "I don't need it to be human. I need it to be predictable."
- "I don't want more options. I want the right default and a way out."
- "I don't want it to be fast if fast means I have to re-check it."
- "I don't want it to be impressive in a demo. I want it to be boring on a
  Tuesday afternoon."
- "I want to look good in front of my team, not explain what the robot did."

These are the sentences to design for.

---

## 3. Why the market leaves this open

The field has converged on autonomy, tools, MCP, plan modes and checkpoints.
It has not converged on **accountability as an interface**.

| Product | Center of gravity | Trust model | What is missing for Tamias's user |
|---|---|---|---|
| **Claude Code** | Prompt + loop + hooks | Anthropic + permission prompts | Audit is not the interface; cost is opaque; permission fatigue |
| **Codex CLI** | Sandbox + approvals + plan | OpenAI + OS sandbox | Heavy; boundary is technical, not human-readable; cost opaque |
| **OpenCode** | Provider-agnostic runtime | User-configured | Maximalist; allow-all culture; little governance UX |
| **Cursor** | IDE + agent | Vendor | Closed; trust is the vendor's; cost is opaque |
| **Cline** | IDE + plan/act + checkpoints | User approvals | IDE-bound; no policy/cost ledger |
| **Gemini CLI** | Open CLI + rewind | Google | Consumer-grade; no audit trail |
| **Aider** | Git-native pair programming | User + git | No governance; no plan mode; no audit |
| **Goose** | Extensible local agent | User | No accountability surface |
| **Crush** | Terminal craft | User | No governance/cost story |
| **Warp** | Agentic terminal | Vendor | Credits, not receipts; closed |
| **Devin** | Hosted environment | Vendor | Trust is outsourced; expensive; no local policy |
| **Copilot CLI** | GitHub-native | GitHub | No project-bound policy; audit is vendor-side |

The gap is consistent:

- **Audit is a log file, not a product surface.** Users cannot see it at the
  moment of decision.
- **Governance is a settings page.** The boundary is buried, not felt.
- **Cost is a bill.** The per-turn price is invisible until the invoice.
- **Undo is a feature, not a promise.** It is not part of the trust story.
- **Memory is session-scoped.** The agent does not accumulate a relationship.
- **Handoff is manual.** The agent edits; the human still writes the PR.

Tamias already has the hard substrate: a project-bound policy, a fail-closed
ask gate, a provider-billed cost ledger, an audit trail, investigation tools and
a model roster. The opportunity is to turn that substrate into the interface.

**The category is not "another coding agent". It is auditable autonomy.**

---

## 4. The Tamias thesis

### 4.1 The sentence

> **Tamias is the agent that shows its work.**

Not "the autonomous agent". Not "the AI engineer". The agent that investigates
before it acts, asks before it crosses a line, proves what it did, and lets you
go back.

### 4.2 The five pillars

| Pillar | User feeling | Product proof |
|---|---|---|
| **Certainty** | "I know what happened." | Receipt, evidence, diff, verification |
| **Control** | "I decide how far it goes." | Trust Dial, Plan Contract, Decision Cards |
| **Continuity** | "It knows my project." | Project Brain, sessions, resume |
| **Craft** | "This feels made for me." | Typography, copy, motion, keyboard-first flow |
| **Candor** | "It tells me the truth, even when it fails." | Provider-billed costs, unpriced flags, honest limits |

### 4.3 The interface hierarchy

Most agents are organised as:

```
chat message → tool call → chat message → tool call → "done"
```

Tamias should be organised as:

```
intent → boundary → plan → evidence → decision → execution → receipt → handoff
```

The chat is one way to see that record. The record is the product.

### 4.4 The design law

> **Every surface must answer a question the user would otherwise ask.**

If it does not, remove it. If it answers a question with a claim instead of
evidence, fix it. This is the law that keeps "premium" from becoming "more".

---

## 5. The signature system

These are not ten features. They are one story told in ten places. Each one is
listed with the question it answers, the data it needs, and whether it is built.

### 5.1 The Boundary Card — *"What may this agent touch?"* — **BUILT**

**What the user sees.** Press `B` (or type `/boundary`). A calm cyan card, not a
red error:

> **◆ BOUNDARY CARD**
> todo-app · company todoinc
>
> **STATUS**
> use case: todo-app
> company: todoinc
> product root: company/work/todoinc/apps/todo
> mode: read / write
> enforcement: checked before every tool call
>
> **WHAT I MAY REACH**
> tools: 18 tools · read_file, search_in_files, ...
> approval needed: write_file, edit_file, create_directory
> shell allowed: python3 -m pytest, git status, ...
> writes: company/work/todoinc/apps/todo/**
> reads denied: company/work/todoinc/hr/**, **/*.pem
> models: all runnable models (free unless paid is enabled)
>
> **WHAT I WILL WORK ON**
> must mention: todo, task, checklist, ...
> refused: chatbot, llm, clone, ...
>
> **RECORD**
> audit: policies/todoinc-todo.audit.jsonl
> receipt: every turn, from measured events
> ask policy: no answer = no (fail closed)

**Why it is premium.** It turns a TOML file into a contract a human can read in
five seconds. It is the first screen a skeptical reviewer wants. It is also a
sales asset: a screenshot of this card explains the product.

**Data source.** `agent.active_policy()` → `PolicyProfile` →
`tui/policy_view.py`. No invented fields. If no policy is loaded, the card says
so plainly: *unbounded development mode, not a bounded demo*.

**Moat.** A competitor can copy the modal, but not the policy engine that makes
the values true.

### 5.2 The Receipt — *"What did it actually do?"* — **BUILT**

**What the user sees.** One calm line after every turn:

> `▤ receipt · NEEDS REVIEW · 2 files changed · 1/1 checks passed · $0.0000 (provider-billed) · R to open`

Press `R` (or `/receipt`) for the full record: request, model, tools, files
read/written/edited, verification commands and exit status, approvals, policy
denials, tokens, duration, cost, and risks. It can be copied as plain text.

**Why it is premium.** It replaces "trust me" with "here is the record". It is
the artifact the user can paste into a PR, a Slack thread, or an audit. It is
also the moment the user stops re-checking everything.

**Data source.** `TurnStart / ToolStart / ToolEnd / ToolAsk / ModelSwitch /
TurnEnd` plus the policy gate. The receipt is deterministic; the model never
writes its own receipt.

**Honesty rules.**
- A failed write is not a change.
- A denied call is not a change.
- A missing provider cost is "cost unknown", not `$0.0000`.
- "checks passed" means the named commands exited 0; it does not mean the work
  is correct.
- No "saved" language. No hypothetical savings in the receipt.
- A changed file with no verification command → the risk section says so.

**Moat.** The receipt joins tool decisions to metered calls. That join is the
product; a pretty modal without the join is theatre.

### 5.3 The Decision Card — *"Why is it asking me?"* — **BUILT**

**What the user sees.** When the policy asks for a human:

> **Allow tool 'write_file'?**
> A human decision is required before this call can run.
>
> action: write_file
> why: policy asks for writes
> arguments: {"file_path": "company/work/.../todo.py", ...}
> scope: this one call only
> if yes: runs once, then is audited as ask-allowed
> if no: the call is denied and audited as ask-denied
>
> `[Y] allow once   [N] deny   [esc] deny (fail closed)`

**Why it is premium.** It treats the user as a decision-maker, not a click
target. It shows the consequence and the audit outcome. It also makes the
fail-closed default explicit.

**Next.** The same card should show a diff preview, the affected checkpoint,
and a "remember this decision for this session" option. That is the Trust Dial.

### 5.4 The Plan Contract — *"What will it do?"* — **BUILT: SIGNED PLAN + FILE DRIFT**

**Built (2026-10-28).** The agent's `update_plan` result becomes a deterministic
card: `P` or `/plan` opens it, a quiet line in the transcript says
`plan · 1/3 done · 1 in progress · P to open`, and the receipt records the
plan under a `PLAN` section. The tool now carries optional **files**,
**verification commands**, **risks** and a **hypothetical cost range**; all four
appear in the card and the receipt. The tool description and system prompt tell
the model to include those facts when it knows them.

In the interactive TUI, publishing a plan opens a **Plan Contract** modal. The
agent worker blocks until the human presses `Y` (sign) or `N`/`Esc` (deny).
While a published plan is unsigned, `write_file`, `edit_file`,
`create_directory` and `run_shell` are held. A denial stops the turn and the
receipt says `PLAN DENIED`; no write runs. Status-only progress updates reuse the
signature; changing steps, files, verification, risks or cost range requires a
new signature.

When the signed plan names files, a write outside that list is **file drift** and
stops the turn with `Error: plan contract - path ... is not in the signed plan`.
The receipt records `PLAN BLOCKED`. The card is explicit when no files were
declared: path drift is then **not enforced**. Shell commands are signature-gated
but not path-scoped; that limit is stated on the card.

**Still next.** Human editing of steps inside the modal, a persisted task-level
contract, and a shell-command allowlist tied to the verification plan. The gate
applies **once a plan is published**; a task where the model never publishes a
plan is not forced into one, by design. Why it matters: plan mode is table
stakes, but a **contract** is premium. It turns the plan into an accountable
artifact, not a chat message, and gives the user a natural place to say "no, do
it this way" before execution spend.

### 5.5 The Investigation Dossier — *"Does it understand my project?"* — **BUILT: VIEW + PRE-WRITE GATE**

**Built (2026-10-28).** The investigation tools' evidence becomes a first-class
card: `D` or `/dossier` opens targets, methods, `file:line` evidence, the
limitations the tools reported, and the unknowns they left open. The receipt
records the same measured counts under an `INVESTIGATION` section. The parser is
deterministic; a tool error contributes nothing and duplicate evidence is
collapsed.

The interactive TUI also enables a **pre-write dossier gate**. The first
mutating call in a turn (`write_file`, `edit_file`, `create_directory` or
`run_shell`) is held until `investigate_target`, `trace_feature` or
`analyze_structure` has returned evidence. The hold is a normal tool error, not
a turn-ending refusal, so the model can investigate and retry in the same turn.
The receipt counts `dossier holds` separately from failures. Operators can
disable the gate for a quick demo with `AGENT_DOSSIER_GATE=0`.

**Limits.** The gate requires *some* evidence from an actual evidence tool, not
proof that the evidence is relevant to the exact write; the plan signature is
the human check on relevance. `finish_investigation` is a summary and does not
unlock a write by itself. The evidence is static (`file:line` and structure),
not runtime proof. The card and receipt state both limits.

This is the senior-engineer ritual: homework before action. Tamias already has
the investigation tools and the evidence requirement; the premium move was to
make the dossier visible and to make "no homework, no write" enforceable.

### 5.6 Time Travel — *"Can I undo it?"* — **BUILT: FILE CHECKPOINTS (V1)**

**Built (2026-10-28; diff 2026-10-29).** Before the first write of a turn,
Tamias captures the original bytes of every path the turn will create or
overwrite (`write_file`,
`edit_file`, `create_directory`). The last 20 are retained in memory for the
session; the v1 UI exposes the latest. The receipt gets a `CHECKPOINT` section
with its id, file count, shell state, diff summary and `Z / /checkpoint` /
`V / /diff` hints.

`Z` or `/checkpoint` opens a preview of the tracked paths and their state
(`modified`, `created`, `created directory`, or `unavailable`). A second `Y`
restores the files; `N`/`Esc` leaves them untouched. The restore is explicit,
path-scoped, atomic per file, preserves file mode, and refuses a path that is
now a symlink or outside the workspace. A created file is removed; a modified
file is put back. The receipt records the restore result under `RESTORE`, and a
failed path is never hidden.

`V` or `/diff` opens a read-only review of the turn's tracked changes. The diff
is **frozen at turn end**, so later edits cannot rewrite the evidence. It is
bounded (600 lines per file, 1,200 total, 256 KB per side); binary, oversized
and truncated files say so instead of pretending the whole file was reviewed.
A path replaced by a symlink or moved outside the workspace is never read
through the link.

**Limits.** This is files-only v1: shell commands mark the checkpoint
**incomplete** because their changes outside tracked files are not captured;
conversation restore, durable storage across processes, and selective per-file
restore are next. The diff is not editable, not a per-file patch export, and not
a replacement for `git diff`. Empty parent directories created by a new file may
remain. The checkpoint is not a substitute for version control.

This is the single biggest trust feature after the receipt. Without undo,
autonomy is frightening. With undo, the user can let the agent run.

### 5.7 The Handoff — *"Can I show this to my team?"* — **LATER**

One command produces: a branch, a PR body, a reviewer brief, a test report, and
a "what I did not verify" section. The user looks good because the agent did the
boring part of the handoff.

This is the feature that turns a personal tool into a team tool.

### 5.8 The Project Brain — *"Will it remember?"* — **LATER**

A readable, editable, versioned document of the project's conventions,
architecture, decisions and gotchas. The agent proposes updates; the user
approves them. Not a hidden embedding. A project wiki the agent maintains.

This is the long-term moat: memory compounds. A competitor can copy a receipt
modal; it cannot copy six months of your project's decisions.

### 5.9 The Flight Recorder — *"Can I prove it later?"* — **LATER**

A searchable, exportable timeline of every decision, model call, tool call,
cost and approval. The audit trail becomes a product, not a log file.

This is where the enterprise story becomes real. It also makes the receipt
trustworthy: the receipt is a view of the recorder.

### 5.10 The Trust Dial — *"How much autonomy?"* — **LATER**

One control: **Observe** (read-only) → **Propose** (plan + diff, no writes) →
**Act** (writes with approvals) → **Auto** (bounded autonomy). The policy caps
the dial; the user can lower it at any time.

One control is premium. Fifty toggles are not. The dial should be visible in the
header and explained in one sentence when it changes.

### 5.11 The Conductor — *"Which model?"* — **PARTIAL**

The agent chooses the right model per phase (explore, edit, review), shows why,
and respects a budget. The user can pin a model when they care. The current
roster and switch cards are the foundation; the premium version is a **policy**
("free for exploration, mid for edits, premium for review") with a visible
reason and a cost contract.

### 5.12 Quiet Focus — *"Is it stuck?"* — **PARTIAL**

A calm status line: current step, tool, elapsed time, and a cancel affordance.
No token waterfall. No "thinking..." loops. The agent speaks when it has a
finding, a decision, or a completion.

The current spinner is a start; the premium version is a **timeline of steps**,
not a stream of consciousness.

---

## 6. What was built in this round

### 6.1 Boundary Card

- `tui/policy_view.py` turns the active policy into labelled sections.
- `tui/modals.py::BoundaryCard` renders it as a scrollable cyan card.
- `B` (nav mode) and `/boundary` open it.
- If no policy is loaded, it says **unbounded development mode**; it never
  pretends a fence exists.
- It shows the same fields the dispatcher checks: tools, asks, shell, writes,
  read denials, models, domain scope, audit path.

### 6.2 Receipt

- `tui/receipt.py::TurnReceipt` collects measured events.
- Every turn ends with a one-line receipt; `R`/`/receipt` opens the full record.
- It distinguishes **answered**, **checks passed**, **needs review**,
  **blocked**, **refused**, and **checks failed**.
- A failed write is not a change; a denied call is not a change; a missing cost
  is not zero.
- It copies as plain text for a PR or a review.
- It never says "saved" or claims a verification that did not run.

### 6.3 Decision Card

- Policy asks now show action, reason, arguments, scope, and the audit outcome
  of yes/no.
- The hint states the fail-closed default.
- The decision is recorded in the receipt.

### 6.4 Tests

- 18 tests for the first slice: receipt, boundary view, TUI keys, refusal
  receipt, plan-level denial, early error and decision card.
- 9 more tests for the second slice: plan parsing, dossier parsing (investigate,
  trace, structure, finish), evidence dedupe, `P`/`D` cards, receipt sections,
  and the honest empty state.
- The contract slice adds core tests for signed plans, denial, status-only
  re-signing, changed-contract re-signing, no-approver fail-closed, a crashing
  approver, file drift, and the dossier gate; plus TUI tests for `PlanGate`,
  `PlanContractModal`, approval/denial receipts and the dossier hold.
- The Time Travel slice adds core tests for created/overwritten files, created
  directories, shell incompleteness, read-only turns, path-escape refusal,
  symlink refusal, failed-restore retry, frozen diffs, binary files and
  symlink-safe diff reads; plus TUI tests for the `Z` preview/restore,
  cancellation, failed retry, `V` diff, receipt diff rows and the bridge event
  fields.
- Full suite: **374 passed** (including docs integrity and model catalog); the
  offline gate's pytest check is **351**.
- The offline gate was re-run on 29 October 2026: 13 passed, 0 failed, 1
  skipped. The contract/dossier core live gate passed twice consecutively on 28
  October, and the diff slice passed twice again on 29 October (14 passed, 0
  failed, 0 skipped, 34s/36s): a real free model called a tool and rotation
  showed the switch card at `$0.0000`. The later `.` path-hint prompt change is
  offline-verified only: a fresh live retry was rate-limited 0/2. The live gate
  does not drive the TUI; the contract, dossier, checkpoint and diff surfaces
  are verified by the TUI/core tests.

### 6.5 What this round does **not** claim

- No human editing of plan steps yet; the modal signs or denies the agent's
  proposed plan.
- No persisted task-level contract yet; a contract is per turn.
- No shell path allowlist yet; shell commands are signature-gated but not
  path-scoped.
- No diff capture yet; the receipt lists changed files, not patches.
- File checkpoints are built, but conversation restore, durable storage across
  processes and selective per-file restore are not.
- Shell changes are not captured by a checkpoint; a shell call marks it
  incomplete.
- No tamper-evident audit; the audit trail is JSONL, not signed.
- No session resume yet.
- The receipt is a view of the current process, not a durable database.
- The boundary card is a view of the policy; it does not replace the
  dispatcher's enforcement.

---

## 7. The experience, screen by screen

### 7.1 First launch

**Today.** A gradient wordmark and a composer. It is beautiful, but it does not
answer "what can this thing touch?"

**Premium version.**
1. The wordmark, one promise: *"The agent that shows its work."*
2. Three setup questions: *What project? What may it touch? What may it spend?*
3. A boundary card, generated from the answers, with a "start with this" action.
4. A sample task that demonstrates the receipt, not a generic "hello".

The first launch should feel like a concierge, not a settings page.

### 7.2 First task

**Today.** The agent starts thinking; tool cards appear.

**Premium version.**
1. The request is echoed with a one-line intent summary.
2. A compact boundary reminder: `bounded to company/work/todoinc/apps/todo`.
3. A dossier: "Read 6 files. Found the todo model at `src/todo.py:12`. No
   writes yet."
4. A signed Plan Contract if the task needs more than one step.
5. A clear "nothing has been changed" line before the first write.

### 7.3 During work

**Today.** Spinner, tool cards, model switch cards.

**Premium version.**
- One current step, one elapsed time, one cancel affordance.
- Tool cards show the target, not just the tool name.
- The cost meter updates per model call, not per turn.
- If the provider rate-limits, the agent says: *"Free tier is busy. I can wait,
  switch to X, or stop. Context is preserved."*
- If the model is stuck, the agent says what it is waiting for, not "thinking".

### 7.4 Approval

**Today.** A yes/no modal.

**Premium version.** The Decision Card above, plus:
- A diff preview for writes/edits.
- The checkpoint that will be created.
- "Allow once / allow for this session / deny".
- A "why this is ask-gated" line from the policy.

### 7.5 Review

**Today.** A reply and a task board.

**Premium version.**
- Receipt first, then diff, then verification.
- A "review by file" mode: changed files, per-file rationale, test evidence.
- A "what I did not verify" section.
- A "copy receipt" and "open handoff" action.
- No "Done!" until the human confirms.

### 7.6 Failure and interruption

**Premium version.**
- Cancel is safe: the agent stops after the current tool, preserves the
  checkpoint, and writes a partial receipt.
- A rate limit is not a boundary violation; it is a provider event with
  options.
- An error says what changed, what did not, and what to do next.
- A failed verification is not hidden; it is the headline of the receipt.

### 7.7 Return next day

**Premium version.**
- The session list shows what each session did, what it cost, and whether it
  was completed or blocked.
- Resume restores conversation, files, and the project brain version.
- The agent opens with: "Last time we changed X; the tests passed; the open risk
  is Y."

### 7.8 Team and audit

**Premium version.**
- Every receipt is exportable.
- Every approval is attributable.
- The policy version and the model are in the record.
- The audit trail is searchable by file, decision, model, or cost.
- The boundary card is shareable with a reviewer.

---

## 8. What to keep, cut and add

### Keep

- The policy engine and fail-closed ask gate. This is the moat.
- The provider-billed cost ledger and the unpriced-step discipline.
- The model roster and free-first/paid-opt-in gate.
- The task board's honest semantics (no invented percentages).
- The boundary violation modal.
- The "Kinda Black" theme: it is distinctive and calm.
- The investigation tools and evidence requirement.
- The offline index and brief compiler.

### Cut

- **Chat-first as the only view.** The transcript is a log, not a workspace.
- **Fake progress.** No percentage without a denominator.
- **"Savings" language.** It is a hypothetical comparison, not a measurement.
- **Tier cycling as the primary model UX.** It is a demo affordance, not a
  product.
- **Permission fatigue.** Every prompt must carry a reason, an effect and a
  scope.
- **"Thinking..." as the only status.** Show the current step.
- **Emojis and cutesy copy.** Premium is respectful, concise, specific.
- **Feature maximalism.** More tools is not more premium.

### Add

| Feature | Why | Reference lesson | Tamias twist | Priority |
|---|---|---|---|---|
| **Boundary Card** | Trust at first glance | Nobody makes policy visible | Human-readable contract | **Built** |
| **Receipt** | Proof after every turn | Claude/Codex show diffs; nobody joins audit+cost | One artifact, exportable | **Built** |
| **Decision Card** | Approval fatigue | Codex/Cursor approvals | Reason + effect + audit outcome | **Built** |
| **Plan Contract** | What will it do? | Cline/Codex plan mode | Signed, costed, file drift stopped | **Built** |
| **Investigation Dossier** | Does it understand? | Claude Code exploration | Evidence-first card + pre-write gate | **Built** |
| **Time Travel** | Can I undo? | Cline/Gemini checkpoints | File preview + frozen diff + explicit restore + receipt link (v1) | **Built (v1)** |
| **Diff review** | What exactly changed? | Git diff / Claude diffs | Frozen, bounded, receipt-linked, read-only | **Built (v1)** |
| **Session Resume** | Continuity | OpenCode/Codex | Receipt-aware sessions | P1 |
| **Handoff** | Team adoption | Devin/Cursor PR flow | Reviewer brief + "not verified" | P2 |
| **Project Brain** | Memory | Claude Code AGENTS.md | Readable, versioned, consent-based | P2 |
| **Flight Recorder** | Proof over time | Audit logs | Searchable, exportable, receipt-linked | P2 |
| **Trust Dial** | Autonomy control | Codex approvals | One dial, policy-capped | P2 |
| **MCP client** | Extension economy | Codex/Goose | Policy-gated tools | P2 |
| **Headless JSON** | CI/automation | Codex/OpenCode | Receipt JSON + exit codes | P2 |
| **Streaming + cancel** | Table stakes | Everyone | Quiet Focus, not a waterfall | P1 |
| **AGENTS.md** | Project rules | Codex/Claude Code | Seed for Project Brain | P1 |

### The order matters

Do not build the Project Brain before the Receipt. Memory without proof is a
liability. Do not build Auto mode before durable Time Travel. Autonomy without
undo is reckless. Do not build a dashboard before the Boundary Card. The first
screen must answer the first question.

---

## 9. Roadmap

### Phase 0 — Truth and safety (done)

- Twelve stop-ship fixes.
- Policy applies to headless runs unless `--unbounded`.
- Honest costs, no fabricated savings.
- Audit redaction, policy-state cleanup.
- Packaging and bundled catalog.

### Phase 1 — The accountable turn (this round, done)

- Boundary Card.
- Receipt.
- Decision Card.
- Tests and docs.
- Demo runbook update.

**Acceptance:** a new user can press `B` before a task and `R` after it, and
answer "what may it touch?" and "what did it do?" without asking the agent.

### Phase 2 — The contract (in progress, started 2026-10-28)

1. **Plan Contract** — *built*. **Built:** deterministic Plan Card (`P` /
   `/plan`), transcript line, receipt section; optional files, verification,
   risks and hypothetical cost range; human sign/deny gate; status-only updates
   reuse the signature; changed contracts re-ask; file drift stops the turn;
   denial and drift states in the receipt. **Next:** human editing, persisted
   task-level contracts, shell path allowlist.
2. **Investigation Dossier** — *built*. **Built:** `D` / `/dossier` card and
   receipt section with `file:line` evidence, limitations, unknowns; pre-write
   gate requiring evidence, with the hold counted separately from failures.
   **Next:** relevance checks and runtime evidence.
3. **Checkpoints + Time Travel** — *built (v1)*. Per-turn file checkpoints,
   preview, explicit restore, frozen diff review, receipt link; `Z` /
   `/checkpoint` and `V` / `/diff`. **Next:** conversation restore, durable
   storage, selective per-file restore.
4. **Session store + resume** — *next*. SQLite/JSONL, list/replay/fork;
   receipt-aware.

**Acceptance:** the user can see the plan, approve it, watch the agent stay
inside it, and rewind the tracked files to before the turn. The current slice
satisfies "see the plan", "see the evidence", approval, file-drift enforcement
and file rewind; conversation rewind and durable checkpoints remain.

### Phase 3 — The handoff (2–3 weeks)

1. **Diff capture and review-by-file** — *built (v1)*. Frozen inline diff,
   bounded and receipt-linked; `V` / `/diff`. **Next:** patch export and
   per-file selection.
2. Verification evidence (commands, exit codes, output digest).
3. Handoff brief + PR body + "not verified" section.
4. Headless JSON with receipt and exit codes.

**Acceptance:** a user can hand a turn to a reviewer without writing the summary
themselves.

### Phase 4 — The memory (3–4 weeks)

1. Project Brain: readable, versioned, consent-based.
2. Flight Recorder: searchable audit, export, receipt links.
3. Trust Dial: Observe / Propose / Act / Auto, policy-capped.
4. Conductor: model policy by phase, visible reason, budget.

**Acceptance:** a returning user does not repeat project context, and an auditor
can reconstruct a turn from the record.

### Phase 5 — Scale (later)

MCP client, subagents, LSP, PTY, server/client split, team policy management.

**Rule:** every phase ships with a receipt update, a boundary update, and a
demo moment. The premium story must remain visible, not buried under
infrastructure.

---

## 10. Decisions

### Decision 1 — Positioning

**Options:** (A) accountable agent, (B) premium craft terminal, (C) project
memory agent.

**Recommendation: A.** Craft is necessary but not sufficient; memory is a
feature, not a category. Accountability is the only position that uses Tamias's
existing moat and is hard for a competitor to copy quickly.

**Consequence:** every feature is judged by "does it increase certainty?" If a
feature only increases speed, it is table stakes, not the pitch.

### Decision 2 — Primary surface

**Options:** (A) terminal-only, (B) terminal + local web receipt, (C) desktop
app.

**Recommendation: A now, B next.** The terminal is the identity and the
constraint. The receipt is the artifact that can travel: export it as HTML/PDF
or a PR comment later. Do not build a desktop app; it would dilute the craft.

### Decision 3 — Autonomy default

**Options:** (A) ask on every write, (B) plan-first + ask on risky, (C) auto.

**Recommendation: B.** Ask-on-every-write causes approval fatigue; auto is
reckless without undo. Plan-first gives the user one meaningful approval, then
bounded execution. Add the Trust Dial after Time Travel.

### Decision 4 — Signature first

**Options:** (A) Receipt, (B) Boundary Card, (C) Plan Contract.

**Recommendation: B + A now, C next.** The Boundary Card is the first question;
the Receipt is the proof. Both use existing data and are demoable immediately.
The Plan Card and Dossier are now built as views; the signed contract and the
pre-write dossier gate are built as enforcement. Checkpoints are the next layer
and need the contract to be credible.

### Decision 5 — Memory

**Options:** (A) session-only, (B) hidden embeddings, (C) readable Project
Brain.

**Recommendation: C, later.** A readable, versioned, consent-based brain is
premium and auditable. Hidden memory is a trust liability. Do not build it
before the Receipt and the Flight Recorder.

### Decision 6 — Target user

**Options:** (A) individual power user, (B) staff engineer/tech lead in a
20–200 person company, (C) enterprise platform team.

**Recommendation: B.** They feel the pain, can adopt without procurement, and
can pay for certainty. A is the wedge; C is the expansion.

### Decision 7 — Pricing (later)

**Options:** (A) per seat, (B) usage, (C) seat + usage cap.

**Recommendation: C.** The receipt makes usage legible; the seat makes the
value legible. Do not price before the receipt is trusted.

---

## 11. Metrics

Do not measure "tokens saved" or "turns per session". Measure trust and accepted
work.

| Dimension | Metric | Target direction |
|---|---|---|
| **Time to first value** | Time from launch to first accepted change | Down |
| **Trust** | % of turns where the receipt is opened | Up, then stable |
| **Trust** | Rework rate after acceptance | Down |
| **Trust** | "I knew what it was doing" survey | Up |
| **Approval fatigue** | Approvals per accepted change | Down |
| **Safety** | Boundary violations caught before execution | 100% |
| **Undo** | Time to restore a checkpoint | Down |
| **Cost** | Estimate error vs. actual | Down |
| **Cost** | Unpriced steps | 0 |
| **Cost** | Cost per accepted change | Down |
| **Quality** | Verification coverage of changed files | Up |
| **Quality** | Test pass rate after agent changes | Up |
| **Continuity** | Session resume rate | Up |
| **Continuity** | Project Brain usage | Up |
| **Handoff** | Time from turn end to PR | Down |
| **Audit** | Turns reconstructable from the record | 100% |

Guardrail: never trade rework for speed. A fast turn that has to be redone is
not premium.

---

## 12. Risks and countermeasures

| Risk | Why it matters | Countermeasure |
|---|---|---|
| **Friction** | Too many cards and approvals make the agent slower than doing it yourself | Quiet by default; one decision per turn; receipts are post-hoc, not blocking |
| **Over-design** | Premium becomes decoration | The one-sentence test; remove any surface that does not answer a question |
| **Perceived slowness** | Certainty can feel like overhead | Show the fast path; receipts appear after the turn, not before |
| **Enterprise vs. individual** | The accountability story sells to teams, but individuals want speed | Position as "for work you can't afford to redo"; individual wedge, team expansion |
| **Scope creep** | Ten signature features is a roadmap, not a release | Ship one phase at a time; each phase has one demo moment |
| **Copycats** | A modal is easy to copy | The moat is the integration: policy + audit + cost + checkpoints + memory |
| **False claims** | One fabricated metric destroys the trust story | Receipts are deterministic; no "saved"; unpriced is unknown; verification is explicit |
| **TUI ceiling** | Rich receipts and diffs are hard in a terminal | Export receipt/diff as HTML/PDF; keep the TUI as the control surface |
| **Model dependence** | A weak model may produce a poor receipt narrative | The receipt is generated from events, not the model |
| **Legal/compliance** | Audit trail is not tamper-evident | Do not claim it; add signing/hash chain later |
| **Context loss** | A long session still has limits | Compaction + Project Brain + session resume |
| **Security** | The boundary card could be mistaken for the enforcement | The card says it is a view of the dispatcher's policy; the gate remains the authority |

---

## 13. Demo script for the premium moments

Add 90 seconds to the faculty runbook:

1. **Before the task.** Press `Esc`, then `B`.
   > "This is the contract, not a settings page. It is generated from the same
   > policy the dispatcher checks. If it is not on this card, the agent cannot
   > touch it."
2. **Run the task.** Ask for an in-scope change.
3. **At the approval.** Show the Decision Card.
   > "It is not asking 'yes/no'. It is showing the action, the reason, the
   > scope, and what happens on either answer. Deny is fail-closed."
4. **After the turn.** Press `R`.
   > "This is the receipt. Files, checks, policy decisions, model, tokens, cost.
   > No 'saved' number, no hypothetical claim. If a check did not run, it says
   > so."
5. **Boundary probe.** Ask for an off-project path. The red modal appears; the
   receipt says **BLOCKED**.
   > "The turn stopped. Nothing outside the fence ran. The receipt is the proof."

If the live model is rate-limited, show the offline receipt and boundary card,
and say it is offline. Do not claim a live run you did not get.

---

## 14. Open decisions for the user

These are the decisions that change the build order. Recommended answers are
included; a different answer changes the roadmap, not the thesis.

1. **Do we commit to "the accountable agent" as the product identity?**
   Recommended: yes. It is the only position that uses the policy/cost/audit
   moat and is not a feature race.
2. **Do we make Time Travel durable and complete next?**
   Recommended: yes. File rewind is built; the missing half is conversation
   restore plus storage that survives a process restart. A plan without undo is
   a promise; undo without a plan is a rescue.
3. **Do we make the receipt exportable before the Project Brain?**
   Recommended: yes. The receipt is the artifact that spreads; the brain is the
   moat that compounds later.
4. **Do we keep the TUI as the only surface?**
   Recommended: TUI now; export later. Do not build a desktop app.
5. **Do we let paid models appear locked in the picker?**
   Recommended: show them as locked with the reason and the opt-in command, so
   the roster is honest and the upgrade path is visible. Do not silently hide
   them.
6. **Do we commit the current 3,000+ uncommitted lines before the next phase?**
   Recommended: yes, in reviewable commits after the tests pass. Do not push
   without explicit instruction.

---

## Appendix A — What to steal, what not to copy

| Product | Steal | Do not copy |
|---|---|---|
| **Claude Code** | Plan mode, hooks, project rules, polish | Chat-first opacity, permission fatigue, opaque cost |
| **Codex CLI** | Sandbox, approvals, `exec --json`, plan | Heavy setup, technical boundary language |
| **OpenCode** | Provider breadth, sessions, server/client | Maximalism, allow-all defaults |
| **Cline** | Checkpoints, plan/act, diff review | IDE lock-in, modal overload |
| **Gemini CLI** | Rewind, open source | Consumer tone, no audit |
| **Aider** | Git-native editing, speed | No governance, no plan |
| **Goose** | Extensibility, local-first | No accountability surface |
| **Crush** | Terminal craft, charm | No cost/governance story |
| **Warp** | Agentic terminal integration | Credits opacity, closed model |
| **Devin** | Environment + handoff | Vendor-trust model, price |
| **Cursor** | Review UX, multi-file edits | Closed, opaque cost |
| **Copilot CLI** | GitHub-native flow | Vendor-side audit only |

The pattern: steal the table stakes, but do not inherit the trust model. Tamias
wins by making the trust model the product.

---

## Appendix B — The premium checklist

Use this before shipping any surface:

- [ ] Does it answer a question the user would otherwise ask?
- [ ] Is every number measured or explicitly labelled hypothetical?
- [ ] Does it distinguish success, refusal, block, failure and "checks passed"?
- [ ] Does it show what changed and what did not?
- [ ] Does it show what was not verified?
- [ ] Is the default fail-closed?
- [ ] Is there a way back?
- [ ] Is the copy specific, short and free of hype?
- [ ] Is the surface quiet when nothing needs the user?
- [ ] Does it feel like a contract, not a prompt?
- [ ] Would a staff engineer paste this into a review?
- [ ] Would a compliance reviewer accept this record?
- [ ] Would the user look good showing it to their team?
- [ ] Does it still work when the model is weak, the provider is down, or the
      turn is cancelled?

If any answer is no, it is not premium yet.
