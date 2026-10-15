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

from dataclasses import dataclass, field

from context_index import citations_for, key_terms  # noqa: F401  (key_terms re-exported)

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
# really exists. The heavy lifting lives in context_index (the symbol/name index
# of D14); this is the thin slice the compiler needs. It never invents a
# reference: a citation is a path (or path:line) that matched, and when nothing
# matches it cites nothing and the brief says so.

MAX_CITATIONS = 5


def retrieve_citations(text, root=".", max_citations=MAX_CITATIONS):
    """Cite real files a brief's terms appear in - symbols, names, then content.

    Offline and bounded; no network, no model, no embeddings. The return value
    is a list of ``path`` (name/symbol match) or ``path:line`` (content match)
    strings, and it is empty when nothing matches.
    """
    return citations_for(text, root, max_citations)
