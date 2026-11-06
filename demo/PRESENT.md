# Presenting TAMIAS to faculty — 7-minute runbook

One claim, shown five ways: **a company can hand this agent one product and a
budget of models, and prove — not claim — that it stayed inside both, and that
you can see exactly what it did.**

Everything below is a command you type, and the result is produced by the real
code. Nothing is a mock unless the slide says so.

---

## 0. Pre-flight (do this 10 minutes before, not on stage)

```bash
cd /home/krish/Desktop/tamias-agent
./demo/check_all.sh --live
```

You want the last three lines to read:

```
  14 passed   0 failed   0 skipped
  READY (offline + live) - live model, tool call and visible switch all passed.
```

If it says `live: 0/2 passed - rate-limited`, the network or the free tier is
having a bad day. Use the **offline fallback** in §6 and say so — do not claim a
live run you did not get.

Optional: back up the product file so a write demo can be undone.

```bash
cp company/work/todoinc/apps/todo/src/todo.py /tmp/todo.py.bak
```

---

## 1. The opening (20 seconds)

> "This agent is given ONE product — a to-do app — and a roster of models. The
> demo shows three things: it refuses anything outside the product, it switches
> models visibly, and every dollar figure is either provider-billed or labelled
> hypothetical. It also shows its work: a boundary card before the task, a
> receipt after it, and a decision card whenever it needs me."

Start it:

```bash
./demo/live_show.sh
```

The header prints the policy, the project path, the rotation pool and
`paid models: off`. The banner prints `18 tools · 54 models (16 free)`.

Before the first task, press **Esc**, then **B**. The boundary card appears:
the product root, the tools that need approval, the shell allowlist, the denied
reads, the refused topics and the audit path. This is the same policy the
dispatcher checks, rendered for a human.

> "This is the contract. If it is not on this card, the agent cannot touch it.
> With no policy loaded, the card says 'unbounded development mode' — it never
> pretends a fence exists."

---

## 2. The fence (2 minutes)

Type an in-scope request:

```
build a todo app with add() and complete()
```

If the model's first tool call is `"."`, it is using the repository root, not
the product. It gets a plain retry hint naming the product root — send the
prompt again with the path pinned:

```
Use company/work/todoinc/apps/todo as the project root. Build the todo app
there with full paths; do not use ".".
```

It runs, and the per-step line shows the model, tokens and `$0.0000`. When the
turn ends, a measured receipt line appears (the status and counts depend on what
the model actually did):

```
receipt · NEEDS REVIEW · 1 file changed · 0/0 checks passed · $0.0000 (provider-billed) · R to open
```

Press **R** later to open it. The receipt is the second half of the pitch; §3
shows the full record.

Now type an off-topic request:

```
write a chatbot for support
```

Expected, immediately (no model call, no tokens):

```
╭──────────────────────── boundary ────────────────────────╮
│ Error: boundary - 'chatbot' is outside use case 'todo-app'│
╰──────────────────────────────────────────────────────────╯
```

Now an off-project **path**:

```
read company/work/todoinc/hr/salaries.csv
```

Expected: a policy denial for an off-limits path. (If the model phrases the
tool call differently, the path still never resolves — it fails closed.)

What to say:

> "The scope gate runs on the request text before a token is spent. The path
> gate runs on every tool call. Deny wins over allow: a request that mentions
> both 'todo' and 'chatbot' is refused on 'chatbot'."

Optional, to show the human gate: ask for a change.

```
add a priority field to the todo item
```

The TUI opens a **decision card**: the action (`write_file`), the reason the
policy asks, the arguments, `scope: this one call only`, and what yes/no mean in
the audit. The hint is `[Y] allow once · [N] deny · [esc] deny (fail closed)`.
Press **N** to show it fails closed with no human consent. If you approve with
**Y**, the receipt records the approval and the changed file; restore afterwards:

```bash
cp /tmp/todo.py.bak company/work/todoinc/apps/todo/src/todo.py
```

---

## 3. The receipt (1 minute)

After the in-scope turn, press **Esc**, then **R** (or type `/receipt`). The
receipt is generated from turn events, never written by the model:

```
TAMIAS RECEIPT · turn 1
status: NEEDS REVIEW

REQUEST
  prompt: build a todo app with add() and complete()

MODEL
  model: nvidia/...:free
  tier: free

WORK
  tools: read_file ×2, write_file ×1, run_shell ×1
  read / listed: src/todo.py
  written: src/todo.py
  edited: none

CHECKS
  python3 -m pytest -q: ✓ passed · 0.4s

POLICY
  approvals: 1
  policy denials: 0
  boundary: clear

COST
  spent: $0.0000 (provider-billed)
  tokens: 1,240 (1,100 prompt · 140 completion)
  duration: 00:00:12 (12.3s)

RISKS
  none recorded
```

The values above are illustrative; the card in front of you contains the real
counts. Press **C** to copy the receipt as plain text.

If this turn used `update_plan`, the **Plan Contract** modal appears when the
agent publishes its plan, before the planned writes. It shows the exact steps,
the files the plan may touch, the verification commands, the risks and a
hypothetical cost range. Press **Y** to sign. The
transcript then has a quiet line such as
`plan · 1/3 done · 1 in progress · 2 files · signed · P to open`. Press **Esc**,
then **P**:

```
◆ PLAN
progress: 1/3 done
in progress: 1
pending: 1

STEPS
  1 [x] Read the todo model
  2 [~] Add priority field
  3 [ ] Run the tests

CONTRACT
  status: signed by user — writes are allowed
  files: company/work/todoinc/apps/todo/src/todo.py
  verify: .venv/bin/python -m pytest -q
  cost range: $0.0000–$0.0200 (hypothetical)
  risks: the schema is unchanged
```

Then demonstrate the two enforcement moments if time allows:

1. **Deny** a plan with **N**. The transcript says `PLAN DENIED`; no write runs.
2. **Drift**: if the model tries to write a path outside the signed `files`
   list, the turn stops with `Error: plan contract - path ... is not in the
   signed plan`, and the receipt says `PLAN BLOCKED`.

Say the limits before anyone asks: the human signs or denies the agent's plan,
but does not edit the steps yet; a contract is per turn; shell commands are
signature-gated but not path-scoped; and if the plan declares no files, path
drift is not enforced. The card states that last one explicitly.

If the turn used `investigate_target`, `trace_feature` or
`analyze_structure`, the transcript also has a
`dossier · 4 evidence lines · 1 unknown · D to open` line. Press **Esc**, then
**D**. The card shows the targets, the evidence as `file:line`, the limitations
the tools reported, and the unknowns they did not resolve. It is static
evidence, not a runtime proof, and the card does not claim otherwise.

The TUI also enables the **pre-write dossier gate** by default. If the agent
tries to write or run a shell command before investigating, the call is held
with `Error: dossier gate ...`; the model can investigate and retry in the same
turn. The receipt counts `dossier holds` separately from failures. For a quick
demo, `AGENT_DOSSIER_GATE=0 python agent.py` disables the gate; do not disable it
while claiming the gate is enforced.

**The checkpoint (1 minute, optional).** After a turn that wrote a file, press
**Esc**, then **Z** (or type `/checkpoint`). The modal previews the turn's
checkpoint: id, prompt, tracked paths and `modified` / `created` /
`created directory`. Press **N** first: nothing is touched. Press **Z** again
and **Y**: the tracked files return to their state before the turn, and the
receipt gets a `RESTORE` row. The checkpoint is file-only; if the turn ran a
shell command, the modal says `shell: ran — not captured`, and you must not
claim a full undo. Conversation restore and durable checkpoints are not built
yet.

**The diff (30 seconds).** Press **V** (or type `/diff`). The card shows the
turn's **frozen** tracked diff: path, `modified` / `created` / `deleted`, and
the `+added -removed` lines. It is read-only; `C` copies it, `V`/`Esc` closes
it. If the file is binary, too large, or the diff was truncated, the card says
so instead of pretending it reviewed the whole file. The receipt carries the
same summary and the `V / /diff` hint. This is the answer to "what exactly
changed?" without opening `git diff`.

Then run the refusal probe from §2 again and open `/receipt`. It says
**REFUSED**, `no model call`, `$0.0000 (no model call)` — a refusal is not a
completed turn, and the receipt says so.

What to say:

> "This is not a model-written summary. It is the event log rendered for a
> human. A failed write is not a change. A denied call is not a change. A
> missing provider cost is 'cost unknown', not zero. 'Checks passed' means the
> command exited 0; it does not mean the work is correct. There is no 'saved'
> number in here because we did not measure one."

If asked "why not just a log?": because the receipt joins the tool decision, the
policy decision, the model that ran and the metered cost into one artifact you
can paste into a PR or an audit. A log is raw material; the receipt is the
product.

---

## 4. The switching (2 minutes)

Ask a second in-scope question:

```
what does complete() do in the todo app?
```

Before the answer, the switch card appears:

```
╭─ Model switched ─────────────────────────────╮
│   ◀ nvidia/nemotron-3.5-lightning:free       │
│           Free ($0.00)                       │
│                   ↓                          │
│   ▶ nvidia/nemotron-3-ultra-550b-a55b:free   │
│           Free ($0.00)                       │
│       ·  reason: rotation (pooled demo run)  │
╰──────────────────────────────────────────────╯
```

Then show manual control:

- press **m** — steps to the next model, card again
- type `/model gemma` — search the roster, pick one, card again

What to say:

> "The switch is an event, not a caption: the core emits it, the TUI draws the
> card, and the header chip follows the model that actually answered the step.
> The same event feeds the credits ledger."

If asked "how many models?": the picker lists **16 free** right now; the
catalog holds **54** (16 free, 24 mid, 14 premium). `./demo/live_show.sh --wide`
rotates all 16 free. Paid models appear only with `--allow-paid`.

---

## 5. The evidence (1 minute, optional on stage)

Offline, deterministic, 10 seconds:

```bash
.venv/bin/python demo/showcase.py
```

Last lines:

```
  boundary probes: 18/18 matched expectation
  models in catalog: 54 (16 free)
  PASS: the to-do fence holds and the roster is loaded
```

And the test/gate numbers:

```
374 passed                      # full suite
351 passed                      # the gate's pytest check
13 passed   0 failed   1 skipped  # the offline gate
14 passed   0 failed   0 skipped  # live gate, earlier today (34s / 36s)
# latest retry after the "." path-hint fix: 0/2, rate-limited
```

What to say:

> "18 boundary probes and 374 tests run without a network or a key, including 40
> premium-surface tests for the boundary card, receipt, signed plan contract,
> dossier, decision card, file checkpoint and frozen diff. The live gate passed
> twice consecutively earlier today; the latest retry after the "." path-hint
> fix was rate-limited, so I am not claiming a fresh live pass."

---

## 6. Fallback if the network or free tier fails

The offline path proves the fence, the loop and the costs without a provider:

```bash
./demo/check_all.sh                 # the offline gate, includes the mock agent loop
.venv/bin/python demo/showcase.py   # 18/18 boundary table + roster
./demo/todo_show.sh                 # the to-do story, offline
```

Say plainly:

> "The live model is rate-limited right now; this is the offline run. The live
> path passed in rehearsal, and I will not claim a live result I cannot show."

Do **not** present the mock loop as live. `demo/check_all.sh` itself prints
"say the model is a mock whenever you demo section 5".

---

## 7. Feature matrix (if asked "what else does it do?")

| Feature | Where it shows | Evidence |
|---|---|---|
| Request scope gate | off-topic refused before spend | `showcase.py` 18/18 |
| Path / tool / shell fence | `hr/`, `chatbot/`, `*.pem`, `rm`, `git push` blocked | `demo/check_boundary.py` 17/17 |
| Human confirmation | decision card with action, reason, scope, audit | tests + TUI |
| Boundary card | `B` / `/boundary`; says "unbounded" with no policy | `tui/policy_view.py` + tests |
| Per-turn receipt | `R` / `/receipt`; measured files, checks, cost, risks | `tui/receipt.py` + 40 premium tests |
| Plan contract | `P` / `/plan`; signed steps, files, verification, risks, hypothetical cost | `tui/plan.py`, `PlanContractModal`, core gate + tests |
| File-drift enforcement | write outside signed `files` stops the turn | `plan_write_block` + tests |
| Investigation dossier | `D` / `/dossier`; `file:line` evidence, limits, unknowns | `tui/dossier.py` + tests |
| Pre-write dossier gate | first mutating call held until evidence; counted as `dossier holds` | `dossier_write_block` + tests |
| Time Travel checkpoint | `Z` / `/checkpoint`; preview, confirm, restore tracked files; shell marked not captured | `checkpoints.py` + core/TUI tests |
| Frozen diff review | `V` / `/diff`; read-only tracked diff, binary/large/truncated called out | `checkpoints.py` + `DiffModal` + tests |
| Refusal receipt | refused turn says `REFUSED`, `no model call` | tests + TUI |
| Company/office boundary | `company/work/{id}/` resolution | `resolve_in_company_workspace` |
| Secret protection | `.env`, `*.pem` never read or printed | `refuse_secret`, `is_sensitive_path` |
| Model roster | 54 models, real prices, fetch script | `models/catalog.json` |
| Visible switching | card + chip + ledger event | live gate attempt 2 |
| Cost per step/turn | model, tokens, `$0.0000`, premium-equivalent | `_show_turn_cost_analysis` |
| Free-first / paid opt-in | provider report line, picker gating | `providers.py` + tests |
| Investigation before build | 7 REA tools, evidence `file:line` | `demo/rea_style_workflow.py` |
| Reasoning chain | model choice + evidence per step | reporting tools, live turn |
| Audit trail | JSONL policy decisions | `policies/todoinc-todo.audit.jsonl` |
| No hidden spend | `--max-task-cost`, unpriced steps flagged | tests + CLI |

---

## 8. Likely questions

**"Is the boundary secure or just a prompt?"**
Three independent layers: the request gate (words), the policy gate on every
tool call (paths/tools/shell), and path resolution with `realpath` (symlinks
cannot escape). The prompt is the weakest layer and is not what enforces it.

**"Why free models?"**
They bill $0.00, so the demo cannot cost the faculty anything. The catalog also
lists paid tiers with real prices; they are hidden unless someone opts in with
`--allow-paid`.

**"How do you know the model actually switched?"**
The card is emitted from the core at the moment the model id changes, and each
step line names the model that produced it. The live gate fails if the rotating
attempt exits 0 without the card.

**"What did it cost?"**
`$0.0000` provider-billed. The premium-equivalent figure is hypothetical retail,
computed from the provider's list prices, and is labelled as such.

**"What is the receipt, and did the model write it?"**
No. It is generated from turn events: tool starts and ends, approvals, model
switches, tokens and provider cost. The model never writes its own receipt. A
failed write is not counted as a change, and a missing cost is "cost unknown",
not zero.

**"Is the receipt tamper-evident?"**
Not yet. It is a deterministic view of the current process, not a signed record.
Signing and a durable Flight Recorder are Phase 4; I will not claim them now.

**"Why does this matter for adoption?"**
Because the user's real question is not "can it code?" It is "can I trust it
with work I would have to redo?" The boundary card answers "what may it touch?";
the receipt answers "what did it actually do?"; the decision card answers "why is
it asking me?"

**"What is not proven?"**
Per-model performance comparison and the reasoning-chain table populate in live
turns but are not asserted by the gate. Free-tier 429s can interrupt a live run.
The receipt lists changed files but not patches; there is no undo or
tamper-evident audit yet. All of this is stated in `check_all.sh`'s own output.

---

## 9. After the demo

If you approved a write:

```bash
cp /tmp/todo.py.bak company/work/todoinc/apps/todo/src/todo.py
```

Nothing in this repo has been committed. If the faculty wants a copy, say so
before pushing anything.
