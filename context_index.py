"""Searchable context index with mandatory citations (D14).

The agent should answer from things it can point at. This module builds a local
index of the workspace - symbols first, then file names, then content lines -
and every result it returns carries a citation (``path`` or ``path:line``); a
query with no match returns nothing rather than a guess.

Two deliberate constraints:

* **ripgrep first.** When ``rg`` is on PATH the content pass uses it; otherwise a
  bounded pure-Python walk stands in. Either way the index is offline.
* **No embeddings.** A semantic index is only worth its cost if a measurement
  says so; none is recorded here, so none is used. The symbol/name index is the
  cheap thing that works first, and it cites exactly.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", "dist", "build", ".tox", ".idea"}

TEXT_SUFFIXES = (".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".rb",
                 ".java", ".kt", ".c", ".h", ".cpp", ".cs", ".php", ".swift",
                 ".md", ".toml", ".json", ".yaml", ".yml", ".txt", ".cfg",
                 ".ini", ".sh", ".sql", ".html", ".css")

MAX_SCANNED_FILES = 4000
MAX_FILE_BYTES = 400_000
MAX_CITATIONS = 5

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{4,}")

_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "when", "then",
    "make", "made", "should", "must", "have", "has", "are", "was", "were",
    "will", "test", "tests", "file", "files", "code", "please", "change",
    "better", "clean", "issue", "error", "they", "them", "their", "there",
}

# One tolerant rule per family. A symbol is a name on a definition line; the
# exact language matters less than pointing at a real line.
_SYMBOL_RULES = (
    ("class", re.compile(r"^\s*class\s+([A-Za-z_]\w*)")),
    ("function", re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)")),
    ("function", re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)")),
    ("function", re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*"
        r"(?:async\s*)?(?:\(|function)")),
    ("function", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)")),
    ("function", re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)")),
)


def key_terms(text, limit=8):
    """Identifier-ish words worth searching for, most specific (longest) first."""
    terms = []
    seen = set()

    for match in _IDENT.findall(text or ""):
        low = match.lower()
        if low in _STOPWORDS or low in seen:
            continue
        seen.add(low)
        terms.append(match)

    terms.sort(key=len, reverse=True)
    return terms[:limit]


def extract_symbol(line):
    """``(kind, name)`` for a definition line, else None."""
    for kind, pattern in _SYMBOL_RULES:
        found = pattern.match(line)
        if found:
            return kind, found.group(1)

    return None


def ripgrep_available():
    return shutil.which("rg") is not None


@dataclass(frozen=True)
class Hit:
    """One indexed location. ``citation`` is never empty - that is the point."""
    path: str
    line: int = 1
    symbol: str = ""
    kind: str = ""
    snippet: str = ""

    @property
    def citation(self) -> str:
        return f"{self.path}:{self.line}"


class ContextIndex:
    """A symbol/name/content index over one root directory.

    Built once with :meth:`build` (or lazily on the first search). The index is
    a plain in-memory structure - no daemon, no database, no network.
    """

    def __init__(self, root="."):
        self.root = root
        self.symbols = {}      # lower name -> [Hit]
        self.files = []        # relative paths
        self._built = False

    # --- build ---------------------------------------------------------------
    def build(self):
        self.symbols = {}
        self.files = []

        for path, rel in self._walk():
            self.files.append(rel)

            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    for number, line in enumerate(handle, start=1):
                        found = extract_symbol(line)
                        if not found:
                            continue
                        kind, name = found
                        self.symbols.setdefault(name.lower(), []).append(
                            Hit(path=rel, line=number, symbol=name, kind=kind,
                                snippet=line.strip()[:120])
                        )
            except OSError:
                continue

        self._built = True
        return self

    def _walk(self):
        scanned = 0

        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

            for name in filenames:
                if scanned >= MAX_SCANNED_FILES:
                    return
                scanned += 1
                yield os.path.join(dirpath, name), os.path.relpath(
                    os.path.join(dirpath, name), self.root)

    def _ensure(self):
        if not self._built:
            self.build()

    # --- queries -------------------------------------------------------------
    def find_symbol(self, name, limit=MAX_CITATIONS):
        """Definition sites for a symbol name, exact first then prefix."""
        self._ensure()
        low = (name or "").strip().lower()
        if not low:
            return []

        exact = list(self.symbols.get(low, []))
        if exact:
            return exact[:limit]

        extra = []
        for symbol, hits in self.symbols.items():
            if low in symbol:
                extra.extend(hits)

        return extra[:limit]

    def find_files(self, term, limit=MAX_CITATIONS):
        """Files whose *name* contains the term."""
        self._ensure()
        low = (term or "").strip().lower()
        if not low:
            return []

        return [Hit(path=rel, line=1)
                for rel in self.files if low in os.path.basename(rel).lower()][:limit]

    def search(self, query, limit=MAX_CITATIONS):
        """Ranked, cited hits: exact symbol, prefix symbol, file name, content."""
        self._ensure()
        ranked = []
        seen = set()

        def add(hits):
            for hit in hits:
                key = (hit.path, hit.line)
                if key in seen:
                    continue
                seen.add(key)
                ranked.append(hit)

        for term in key_terms(query):
            add(self.find_symbol(term, limit))
            add(self.find_files(term, limit))
            if len(ranked) >= limit:
                break

        if len(ranked) < limit:
            add(self.grep(query, limit - len(ranked)))

        return ranked[:limit]

    # --- content pass --------------------------------------------------------
    def grep(self, query, limit=MAX_CITATIONS):
        """Content matches as cited hits; ripgrep when present, else a walk."""
        terms = key_terms(query)
        if not terms:
            return []

        if ripgrep_available():
            return self._rg(terms, limit)

        return self._py_grep(terms, limit)

    def _rg(self, terms, limit):
        pattern = "|".join(re.escape(term) for term in terms)
        command = ["rg", "--line-number", "--no-heading", "--color", "never",
                   "-i", "-m", "1", pattern, "."]

        try:
            result = subprocess.run(command, cwd=self.root, capture_output=True,
                                    text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return self._py_grep(terms, limit)

        hits = []
        for line in result.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            path, number, text = parts
            rel = path[2:] if path.startswith("./") else path
            try:
                number = int(number)
            except ValueError:
                continue
            hits.append(Hit(path=rel, line=number, snippet=text.strip()[:120]))
            if len(hits) >= limit:
                break

        return hits

    def _py_grep(self, terms, limit):
        lowered = [term.lower() for term in terms]
        hits = []

        for path, rel in self._walk():
            if len(hits) >= limit:
                break
            if not rel.endswith(TEXT_SUFFIXES):
                continue
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    for number, line in enumerate(handle, start=1):
                        if any(term in line.lower() for term in lowered):
                            hits.append(Hit(path=rel, line=number,
                                            snippet=line.strip()[:120]))
                            break
            except OSError:
                continue

        return hits


def citations_for(query, root=".", limit=MAX_CITATIONS):
    """The citation strings for a query - ``[]`` when nothing matched.

    A thin convenience over :class:`ContextIndex` for callers (like the brief
    compiler) that only need the references, not the snippets.
    """
    if not key_terms(query):
        return []

    return [hit.citation for hit in ContextIndex(root).search(query, limit)]
