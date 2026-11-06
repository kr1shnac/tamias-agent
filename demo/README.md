# demo: bounding the agent to ONE project

Two themed demos. Both run offline; `check_all.sh --live` and `live_show.sh`
add a real model on the same fence.

- **TODOINC — a to-do app company** (the headline demo): the agent works on the
  to-do app and refuses anything else, *before* it spends a token.
- **acme / codefix-bot**: the same idea, shown at the filesystem level.

---

## 0. Check everything in one command

```bash
./demo/check_all.sh            # full offline sweep, ~25s
./demo/check_all.sh --fast     # registry + tests + gate only, ~13s
./demo/check_all.sh --live     # also rehearse the real model (needs key + network)
```

Prints PASS/FAIL per check and exits non-zero if anything fails, so it doubles
as a pre-demo gate and a CI step. It never reads or prints `.env`; the key is
only ever resolved to yes/no.

### The two commands to actually demo

```bash
./demo/live_show.sh            # live: TUI, to-do fence, a different free model
                               # each turn, switch card when it changes
./demo/showcase.py             # offline: 18/18 boundary probes + the roster
```

`live_show.sh` exports `AGENT_MODEL_ROTATE=turn` and a pool of eight free
models from `models/catalog.json`, so every pick bills **$0.00**. Pass
`--allow-paid` to also offer paid models, or `--task "..."` for the headless
path. Headless writes are ask-gated and fail closed (no human to confirm), so
demo writes in the TUI, where a confirmation modal answers the gate.

`showcase.py` is the deterministic version: it runs the real
`domain_check` / `policy_check` / `policy_ask` / `rotate_model` code and prints
which requests are allowed and which are refused. The rotation section is
labelled "selection only" - it makes no API calls and claims no spend.

### The model roster

`models/catalog.json` is generated from the provider's public `/models`
endpoint and carries real ids, context sizes and list prices:

```bash
.venv/bin/python demo/fetch_models.py            # regenerate (needs network)
.venv/bin/python demo/fetch_models.py --dry-run  # see counts, write nothing
```

Only models that advertise **tool calling** are kept (the agent's loop is tool
calls); routers, batch endpoints, `~` aliases and anything above $20/1M prompt
tokens are filtered out. Free models are always offered. Paid models appear
only with `--allow-paid` or a direct key for the endpoint actually in use - see
`providers.py`. A picker that offers a model the run cannot call would be a
lie, so it does not.

---

## 1. TODOINC: "the to-do app, and nothing else"

```bash
cd /home/krish/Desktop/tamias-agent
./demo/todo_show.sh
```

The company's one product is a to-do application. The fence is
`policies/todoinc-todo.toml`:

```
company/work/todoinc/
  apps/todo/         <- the product: the ONE project the agent may work on
  apps/chatbot/      <- a different project: off-limits
  hr/                <- off-limits
```

### How the company sets the task

```bash
.venv/bin/python agent.py \
  --company-id todoinc \
  --policy policies/todoinc-todo.toml \
  --task-id TODO-42 --assignee todo-bot \
  --task "add a due date to each item"
```

The **fence** (`--company-id` + `--policy`) and the **task** (`--task` +
`--task-id`) are passed in separately. The task is a string; the fence is a
file the admin owns. That is what makes the fence hold even when the task is
adversarial.

### The layers that block, and when

| Layer | Reads | Blocks | Cost of a block |
|---|---|---|---|
| **1. Scope gate** `domain_check()` in `run_turn` | the *request text* (the task, and every interactive turn) | a request that is not about the to-do app | **0 tokens** — the model is never called |
| **2. Plan check** `verify_plan()` in `run_turn` | the model's **whole planned batch**, before any of it runs | a plan where *any* call leaves the product — **all-or-nothing**, none of it executes | the calls never run |
| **3. Action gate** `dispatch_tool` → `policy_check` | each individual tool **call** as it runs | a call that leaves the product (path / tool / command) | the call never runs; every step re-checks |

Layer 1 is a **scope guard, not a security boundary** — it is a deterministic,
offline word check (`[domain] allow` must match, `[domain] deny` wins, empty
allow = off). Words are easy to evade, so it must never be the only fence.
Layer 2 is the "look at the whole plan first" pass: the model proposes several
calls, the agent verifies all of them against the project, and only then
executes. If one call is out of scope, **the whole plan is refused** and the
turn **stops** — the model is not allowed to re-propose the same boundary again
and again. Layer 3 is the **enforced** boundary, and it fires on *every* call
regardless of what the plan said.

> Why three? Layer 1 stops an off-topic task before it costs anything. Layer 2
> stops a *partial* escape (a plan that smuggles one bad call among good ones).
> Layer 3 is the fence that actually holds even if the first two are fooled.

**A blocked turn stops — and never reports success.** The first deliberate block
(a scope refusal, a policy denial, a secret read) ends the turn immediately, so
the agent cannot hammer the fence step after step. The task board then shows
`✗ blocked` (never `ready · 100%`), and the model's "the task is complete" text
is not trusted: the transcript carries an authoritative `⛔ Blocked` line, and
the task is recorded as blocked, not complete.

### What you see

```
You ▸ add a due date to each todo item and run the tests
  ✓ in scope - working
    [RAN]    read_file / edit_file / run_shell (the product's own tests)
You ▸ build me a ChatGPT clone
  ⛔ BOUNDARY (scope)  Error: boundary - 'chatgpt' is outside use case 'todo-app'
You ▸ add a task, and also build a chatbot
  ⛔ BOUNDARY (scope)  Error: boundary - 'chatbot' is outside use case 'todo-app'
You ▸ add a to-do export feature          # in scope, but reaches for chatbot/
    [DENIED] read_file  ... apps/chatbot/src/bot.py is off-limits ...
    [DENIED] write_file ... apps/chatbot/src/bot.py is outside the write scope ...
```

Every refusal **returns control** — the session keeps running, the next request
is handled normally, and each off-topic request is refused again. Nothing
crashes, nothing reaches the model.

### The real CLI, offline

```bash
# off-topic task: refused at the scope gate, exit 1, steps 0, $0 spent
.venv/bin/python agent.py --company-id todoinc \
  --policy policies/todoinc-todo.toml --task "build me a ChatGPT clone"
```

---

## 2. acme / codefix-bot: the filesystem-level view

This part demonstrates the same two fences, focused on the paths the agent may
touch, with **no API key and no network**:

| Fence | Flag | Effect |
|---|---|---|
| Company | `--company-id acme` | the agent may only touch `company/work/acme/` |
| Use case | `--policy policies/acme-codefix.toml` | inside that company, only `bots/codefix/` |

The pretend company lives in `company/work/acme/`:

```
company/work/acme/
  bots/codefix/      <- the ONE project the boundary allows (read + write)
  bots/payments/     <- another project in the same company: off-limits
  hr/salaries.csv    <- off-limits
```

## Present it in one command

```bash
cd /home/krish/Desktop/tamias-agent
./demo/show.sh
```

Runs five acts: the policy file, the areas the agent can reach, an in-scope
task vs an out-of-scope one, the full 17-probe gate check, and the exact
command the company uses for a real run.

## How a company sets this up (the two halves)

The boundary is **not** derived from the task text. It is deliberately two
separate things, owned by two different people:

| Half | Who owns it | What it is | How it enters a run |
|---|---|---|---|
| **The fence** | the company admin | `policies/acme-codefix.toml` - the use case | `--policy <file>` (or a gateway token in managed mode) |
| **The task** | the operator / ticket | a string + a ticket id | `--task "…" --task-id PROJ-1457 --assignee codefix-bot` |

1. The admin writes the policy once, per use case, and keeps it **outside the
   agent's fence** (e.g. `~/.config/tamias/policies/acme-codefix.toml`). The
   agent reads it and can never edit it (`protect_path`).
2. Work arrives as a ticket. The operator runs the agent with **both**: the
   fence (`--policy`, `--company-id`) and the ticket (`--task`, `--task-id`).
3. The task text goes into the *prompt* (the model is asked to stay inside);
   the policy goes into the *runtime gate* (the model is not trusted to).
   `assignment_line()` says this exactly: the assignment is "provenance plus
   the reason the boundary exists, **not a second boundary of its own**."

So a task like *"copy the Stripe key from payments into codefix"* cannot widen
the fence - `demo/task_scope_demo.py` proves it, with a human who approves
everything.

## Check it

```bash
cd /home/krish/Desktop/tamias-agent
.venv/bin/python demo/check_boundary.py
```

It wires the same two fences `agent.py` wires, dispatches real tool calls, and
asserts each gate decision. Exit code is 0 when everything matches, non-zero
otherwise, so it doubles as a CI gate. Expected tail:

```
17/17 probes matched the boundary
```

Each probe asserts one of: the call **ran** (inside the project), was **denied**
by the policy tables, was **ask-denied** because a write needs a human yes, or
was **refused below the policy** (secret protection / company fence / the
policy's own path is not editable).

## Run the real agent against the same boundary

```bash
cd /home/krish/Desktop/tamias-agent
.venv/bin/python agent.py \
  --company-id acme \
  --policy policies/acme-codefix.toml \
  --task "add a discount() helper to src/cart.py and run its tests"
```

A live run needs a model; route it through the Tamias gateway on port 8000
(`TAMIAS_BASE_URL` / `TAMIAS_API_KEY`). Offline, `check_boundary.py` already
proves the fence: the same `dispatch_tool` gate every model tool call goes
through.

## When the model is unavailable (a 429, no credits)

Free models hit a daily quota (`free-models-per-day`). The boundary that this
demo is about is checked **before any model call**, so it still shows:

```bash
# off-topic: refused with 0 tokens, $0.0000, exit 1 - no model needed
.venv/bin/python agent.py --company-id todoinc \
  --policy policies/todoinc-todo.toml --task "build me a LinkedIn clone"
```

An *in-scope* ask does need a model, and the agent now says so plainly instead
of dumping the provider's JSON:

> `provider limit: The model provider rate-limited this run (free-tier daily
> model limit). This is a provider limit, not a use-case boundary block - the
> fence is unaffected, and nothing was completed.`

To still show the **whole loop** (model proposes a call -> the path fence blocks
it -> the turn stops) with no network, run the agent against a local **mock
model**:

```bash
./demo/mock_act.sh --company-id todoinc \
  --policy policies/todoinc-todo.toml --task "create todo in desktop"
# -> write_file /home/krish/Desktop/todo.txt
# -> "outside the write scope" -> "blocked" -> "⛔ REFUSED" -> exit 1

# with no --task, on a terminal, this opens the TUI against the same mock:
./demo/mock_act.sh
```

`demo/mock_provider.py` is a **mock, not a model and not a live run**: it returns
a fixed `write_file` tool call (to `~/Desktop/todo.txt` when the ask says
"desktop", else inside the product). Say so out loud when you demo it. It exists
so the agent's own loop can be shown when the provider is down.

## The audit trail

Every gate decision is appended to `policies/acme-codefix.audit.jsonl` (one JSON
object per line: `ts, use_case, tool, decision, reason, args`) and kept in
memory in `agent.POLICY_AUDIT`. `check_boundary.py` prints both.

## Editing the boundary

`policies/acme-codefix.toml` is the boundary. To fence a different project,
copy it and change `[use_case] name`, the `[paths] allow_write` / `deny_read`
globs (relative to the repo root), and the `[run_shell]` command families.

> Gotcha the checker caught: `deny_read = ["dir/**"]` covers files *under*
> `dir` but not `dir` itself, so `list_directory` / `search_in_files` on the
> bare directory pass. List the directory **and** `dir/**`.
