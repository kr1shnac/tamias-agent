# The context index (D14)

The agent should answer from things it can point at. `context_index.py` builds a
local, offline index of the workspace so that retrieval returns **citations**,
not vibes.

## What it indexes

Ranked, most specific first:

1. **Symbols** — definition sites (`class`/`def`/`function`/`const f =`/`func`/
   `fn`), matched exactly and then by prefix.
2. **File names** — files whose basename contains the term.
3. **Content lines** — the first matching line in each file.

Every result is a `Hit` with a non-empty `citation` (`path` or `path:line`). A
query with no real match returns **nothing** — the index never invents a
reference. That is the "mandatory citations" rule: no source, no result.

## ripgrep, then a fallback

The content pass shells out to `rg` when it is on `PATH` (fast, bounded with
`-m 1`), and otherwise falls back to a bounded pure-Python walk. Both are
offline; neither touches the network.

## No embeddings (yet)

A semantic index is only worth its cost if a measurement says so. None is
recorded here, so none is used. The symbol/name index is the cheap pass that
answers most queries, and it cites exactly. Embeddings are a later, *measured*
decision — not a default.

## API

```python
from context_index import ContextIndex, citations_for

index = ContextIndex(".").build()

index.find_symbol("select_model")   # -> [Hit(agent.py:1790, function, ...)]
index.find_files("brief")           # -> [Hit(brief.py), ...]
index.search("select_model escalation")   # ranked + cited
index.grep("cached_tokens")         # content pass (rg or walk)

citations_for("select_model", ".")  # -> ["agent.py:1790", ...]
```

The brief compiler (D13) uses `citations_for` for its GROUNDING section, so a
compiled brief cites the same real locations this index does.

## Known limitation

Grounding is a **crude first pass**. A large vendored corpus in the tree (e.g. a
directory of third-party prompts) can match common terms and add noise. The
citations are still real — they are just not always *relevant*. Tightening
relevance (per-directory clustering, weighted terms) is future work, to be
driven by a measurement rather than a guess.

## Tests

`test_agent.py` covers the index: symbol extraction across languages; exact
symbol ranked first with its definition line; prefix matching; the content pass
citing a real line; every hit carrying a non-empty citation; no-match returning
nothing; VCS/cache directories skipped; and the ripgrep path parsed correctly
when `rg` is present.
