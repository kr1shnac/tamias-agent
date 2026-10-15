"""Brief compiler: turn a terse ask into an elaborated, grounded brief (D13).

A coding agent does its worst work on a one-line brief - "fix the failing
test", "clean this up". The compiler deliberately does **not** call a model to
ask what the user already knows; that would spend credits to rediscover the
brief. It reads the brief, names what is missing, states the assumption it
would otherwise make silently, cites whatever context it was grounded in, and
scores how ambiguous the ask is. A high score is a prompt to ask a question,
not a licence to guess and spend.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

# A verb that says what to do but not what *done* means.
VAGUE_VERBS = (
    "fix", "improve", "clean up", "cleanup", "refactor", "optimize",
    "optimise", "make it better", "make better", "update", "polish", "tidy",
)

# Anything that reads like a checkable definition of done.
ACCEPTANCE_HINTS = (
    "test", "pass", "green", "assert", "expect", "should", "acceptance",
    "reproduce", "repro", "fails", "failure", "coverage", "lint", "type-check",
)

# Anything that points at a concrete target.
TARGET_HINTS = (
    ".py", ".js", ".ts", ".tsx", ".go", ".rs", ".rb", ".java", ".md",
    ".toml", ".json", ".yaml", ".yml", "/", "\\", "def ", "class ", "function",
    "module", "file", "endpoint", "route",
)

# Words that sound risky when paired with an ambiguous brief.
RISK_HINTS = ("delete", "drop", "remove", "refactor", "migrate", "rename",
              "rewrite", "production", "prod", "migration", "schema", "auth",
              "credential", "secret", "payment", "billing")

QUESTION_FOR_TARGET = "Which file, module or symbol is this about?"
QUESTION_FOR_DONE = "What does 'done' look like - is there a test or check that must pass?"


@dataclass
class Brief:
    """The compiled form of one raw brief."""
    raw: str
    elaborated: str = ""
    assumptions: list = field(default_factory=list)   # what we would assume
    questions: list = field(default_factory=list)     # what only the user knows
    citations: list = field(default_factory=list)     # grounding, e.g. files
    signals: list = field(default_factory=list)       # why the score is what it is
    ambiguity_score: float = 0.0                      # 0.0 clear .. 1.0 unclear
    risk_band: str = "low"                            # low | medium | high

    @property
    def needs_clarification(self) -> bool:
        """High ambiguity means ask before spending, not guess."""
        return self.ambiguity_score >= 0.6


def _mentions(text: str, needles) -> bool:
    low = text.lower()
    return any(needle in low for needle in needles)


def _dedupe(items):
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def compile_brief(raw, citations=None) -> Brief:
    """Compile ``raw`` into a :class:`Brief`.

    ``citations`` are grounding references the caller already retrieved (paths,
    symbols, line references) - the compiler never invents one (D14). The score
    is a weighted tally of the ambiguities found, capped at 1.0.
    """
    text = (raw or "").strip()
    citations = _dedupe([str(c) for c in (citations or []) if str(c).strip()])

    assumptions: list = []
    questions: list = []
    signals: list = []
    score = 0.0

    def add(weight, signal, assumption=None, question=None):
        nonlocal score
        score += weight
        signals.append(signal)
        if assumption:
            assumptions.append(assumption)
        if question:
            questions.append(question)

    if len(text) < 40:
        add(0.4, "the brief is very short",
            "Treat the brief as the whole ask and keep the change minimal.",
            QUESTION_FOR_DONE)

    if not _mentions(text, TARGET_HINTS):
        add(0.25, "no file, symbol or module is named",
            "Locate the relevant code before changing anything.",
            QUESTION_FOR_TARGET)

    if _mentions(text, VAGUE_VERBS) and not _mentions(text, ACCEPTANCE_HINTS):
        add(0.2, "a vague verb with no stated acceptance check",
            "Make the smallest change that satisfies the stated symptom.")

    if not _mentions(text, ACCEPTANCE_HINTS):
        add(0.2, "no acceptance criteria",
            "Use the project's tests as the definition of done.",
            QUESTION_FOR_DONE)

    if _mentions(text, (" it", "this", "that")) and len(text) < 60:
        add(0.1, "a pronoun with no referent in the brief",
            "Bind the pronoun to the most recent item in context.")

    if _mentions(text, RISK_HINTS):
        add(0.1, "the work sounds destructive or wide-reaching",
            "Prefer the smallest reversible change and show the diff before applying.")

    score = min(1.0, round(score, 2))
    band = "high" if score >= 0.6 else "medium" if score >= 0.3 else "low"

    brief = Brief(
        raw=text,
        assumptions=_dedupe(assumptions),
        questions=_dedupe(questions),
        citations=citations,
        signals=signals,
        ambiguity_score=score,
        risk_band=band,
    )
    brief.elaborated = render_brief(brief)
    return brief


def render_brief(brief: Brief) -> str:
    """The elaborated brief plus the assumptions it rests on.

    Only grounded citations are shown; if there are none, the compiler says so
    rather than inventing a reference.
    """
    lines = ["TASK (verbatim):", brief.raw or "(empty brief)", "", "PLAN OF RECORD:"]

    if brief.assumptions:
        lines += [f"- {item}" for item in brief.assumptions]
    else:
        lines.append("- The brief is specific enough to act on as written.")

    if brief.citations:
        lines += ["", "GROUNDING (cited):"]
        lines += [f"- {item}" for item in brief.citations]
    else:
        lines += ["", "GROUNDING (cited): none retrieved yet."]

    return "\n".join(lines)


def format_brief(brief: Brief) -> str:
    """A one-panel rendering for the terminal."""
    head = (f"brief · ambiguity {brief.ambiguity_score:.2f} · "
            f"risk {brief.risk_band}")
    body = [head, "", brief.elaborated]

    if brief.needs_clarification and brief.questions:
        body += ["", "OPEN QUESTIONS (ask before spending):"]
        body += [f"  ? {q}" for q in brief.questions]

    return "\n".join(body)


# --- grounding (D13 -> D14) ---------------------------------------------------
# A brief is only "retrieval-grounded" if every citation points at something that
# really exists. This first pass is deliberately crude and offline - a bounded
# filename/identifier scan, no embeddings - and it never invents a reference: a
# citation is a path that matched, full stop. When nothing matches it cites
# nothing, and the brief says so.

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", "dist", "build", ".tox"}
MAX_SCANNED_FILES = 4000
MAX_FILE_BYTES = 400_000
MAX_CITATIONS = 5

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{4,}")
# Words too common to make a useful citation.
_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "when", "then",
    "make", "made", "should", "must", "have", "has", "are", "was", "were", "will",
    "test", "tests", "file", "files", "code", "please", "fix", "add", "update",
    "change", "make", "better", "clean", "issue", "error", "bug", "failing",
}


def key_terms(text, limit=8):
    """The identifier-ish words worth searching for, most specific first."""
    terms = []
    seen = set()
    for match in _IDENT.findall(text or ""):
        low = match.lower()
        if low in _STOPWORDS or low in seen:
            continue
        seen.add(low)
        terms.append(match)
    # prefer the longer (more specific) terms, keep the original spelling
    terms.sort(key=len, reverse=True)
    return terms[:limit]


def retrieve_citations(text, root=".", max_citations=MAX_CITATIONS):
    """Cite real files a brief's terms appear in - names first, then contents.

    Offline and bounded: no network, no model, a hard cap on files and size. The
    return value is a list of ``path`` (file name matched) or ``path:line``
    (first content match) strings, and it is empty when nothing matches.
    """
    terms = key_terms(text)
    if not terms:
        return []

    lowered = [t.lower() for t in terms]
    name_hits = []
    content_hits = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if scanned >= MAX_SCANNED_FILES:
                break
            scanned += 1
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)

            if any(term in name.lower() for term in lowered):
                name_hits.append(rel)
                continue

            if not name.endswith((".py", ".js", ".ts", ".tsx", ".go", ".rs",
                                  ".rb", ".java", ".md", ".toml", ".json",
                                  ".yaml", ".yml", ".txt", ".cfg", ".ini")):
                continue

            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    for number, line in enumerate(handle, start=1):
                        if any(term in line.lower() for term in lowered):
                            content_hits.append(f"{rel}:{number}")
                            break
            except OSError:
                continue

        if len(name_hits) + len(content_hits) >= max_citations:
            break

    return (name_hits + content_hits)[:max_citations]
