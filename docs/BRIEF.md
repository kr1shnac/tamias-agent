# The brief compiler (D13)

A coding agent does its worst work on a one-line brief — *"fix it"*, *"clean
this up"*. The brief compiler turns that into an elaborated, retrieval-grounded
brief **before** the first model call.

It is deliberately **offline**. It does not spend a model call to ask what the
user already knows; that would burn credits to rediscover the brief. Instead it:

1. **Names what is missing** — no file/symbol, no acceptance criteria, a vague
   verb, a pronoun with no referent, work that sounds destructive.
2. **States the assumption it would otherwise make silently** — one line per
   gap, so the operator can veto it.
3. **Grounds the brief in real files** — a bounded, local filename/identifier
   scan. A citation is a path (or `path:line`) that actually matched; when
   nothing matches it cites nothing and says so. It never invents a reference.
4. **Scores the ambiguity** and bands the risk. A high score is a prompt to ask
   a question, *not* a licence to guess and spend.

## Usage

```bash
# elaborate a terse brief before it runs
.venv/bin/python agent.py --task "fix the flaky test" --brief

# or via the environment, for a shell session
AGENT_BRIEF=1 .venv/bin/python agent.py --task "fix the flaky test"
```

The compiled brief is printed as a panel (ambiguity, risk, plan of record,
grounding, open questions) and its elaborated text is what the agent is given.
Without the flag the task is passed through verbatim — the default is unchanged.

## What it is not

- **Not a model call.** No credits are spent compiling a brief.
- **Not a guess at intent.** Where the brief is unclear it records an assumption
  and an open question; it does not silently pick a meaning.
- **Not the context index (D14).** Grounding here is a crude first pass — a
  bounded filename/identifier scan, no embeddings. D14 owns the real searchable
  index; this module only needs enough to cite something real.

## API

```python
from brief import compile_brief, format_brief, retrieve_citations

brief = compile_brief("fix it")                     # -> Brief
brief.ambiguity_score   # 0.0 (clear) .. 1.0 (unclear)
brief.risk_band         # "low" | "medium" | "high"
brief.assumptions       # what it would otherwise assume
brief.questions         # what only the user can answer
brief.citations         # real paths/lines it was grounded in
brief.elaborated        # the text handed to the model

print(format_brief(brief))                          # the terminal panel

retrieve_citations("fix widget_router", root=".")   # -> ["widget_router.py", ...]
```

## Tests

`test_agent.py` covers the compiler: a terse brief scores high and lists its
assumptions and questions; a specific brief scores zero and assumes nothing;
citations are never invented; grounding finds a real file/line, cites nothing
when nothing matches, and never leaves the root for `.git`/cache directories.
