"""Deterministic investigation dossier built from the agent's evidence tools.

The dossier does not summarise with a model and does not invent a finding. It
parses the evidence lines the investigation tools already produced
(``file:line`` for ``investigate_target`` / ``trace_feature``) and keeps the
limitations and unknowns the tools reported. If a tool errors, nothing is
added. The card is a view of measured static evidence; it is not a runtime
proof.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional


_EVIDENCE = re.compile(r"^\s*\[evidence\]\s+(.+?):(\d+)\s+(.*)$")
_TRACE_STEP = re.compile(
    r"^\s*Step\s+\d+\s+\|\s+(.+?):(\d+)\s+\|\s+(.*)$")
_FILE_ENTRY = re.compile(r"^\s*\[(FILE|DIR)\]\s+(.+?)\s*$")
_NONE_VALUES = {"", "none", "none identified", "none found"}
INVESTIGATION_TOOLS = (
    "investigate_target",
    "trace_feature",
    "analyze_structure",
    "finish_investigation",
)


@dataclass(frozen=True)
class Evidence:
    path: str
    line: int
    text: str

    @property
    def label(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass
class Investigation:
    tool: str
    target: str = ""
    feature: str = ""
    kind: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    entries: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    confidence: str = ""


@dataclass
class TurnDossier:
    investigations: list[Investigation] = field(default_factory=list)

    # ---------------------------------------------------------------- ingest
    def add(self, tool_name: str, result: object) -> bool:
        """Parse one investigation tool result. Returns True if it was used."""
        text = str(result or "")
        if not text.strip() or text.lstrip().lower().startswith("error"):
            return False

        parser = _PARSERS.get(tool_name)
        if parser is None:
            return False
        investigation = parser(tool_name, text)
        if investigation is None:
            return False
        self.investigations.append(investigation)
        return True

    # -------------------------------------------------------------- derived
    @property
    def evidence(self) -> list[Evidence]:
        values: list[Evidence] = []
        seen: set[tuple[str, int, str]] = set()
        for investigation in self.investigations:
            for item in investigation.evidence:
                key = (item.path, item.line, item.text)
                if key in seen:
                    continue
                seen.add(key)
                values.append(item)
        return values

    @property
    def targets(self) -> list[str]:
        return _unique(item.target for item in self.investigations
                       if item.target and item.target != "session")

    @property
    def methods(self) -> list[str]:
        return _unique(item.tool for item in self.investigations if item.tool)

    @property
    def limitations(self) -> list[str]:
        return _unique(value for item in self.investigations
                       for value in item.limitations)

    @property
    def unknowns(self) -> list[str]:
        return _unique(value for item in self.investigations
                       for value in item.unknowns)

    @property
    def has_content(self) -> bool:
        return bool(self.investigations)

    def card_line(self) -> str:
        """The status line inside the open card (no 'D to open' hint)."""
        parts = [f"{_plural(len(self.investigations), 'investigation')}"]
        parts.append(f"{_plural(len(self.evidence), 'evidence line')}")
        if self.unknowns:
            parts.append(f"{_plural(len(self.unknowns), 'unknown')}")
        return "dossier · " + " · ".join(parts)

    def summary_line(self) -> str:
        return self.card_line() + " · D to open"

    def receipt_rows(self) -> list[tuple[str, str]]:
        rows = [
            ("targets", _join(self.targets)),
            ("evidence", str(len(self.evidence))),
            ("unknowns", str(len(self.unknowns))),
            ("methods", _join(self.methods)),
        ]
        if self.limitations:
            rows.append(("limits", _join(self.limitations)))
        return rows

    def sections(self) -> list[tuple[str, list[tuple[str, str]]]]:
        sections: list[tuple[str, list[tuple[str, str]]]] = [
            ("SUMMARY", [
                ("targets", _join(self.targets)),
                ("evidence", str(len(self.evidence))),
                ("unknowns", str(len(self.unknowns))),
                ("methods", _join(self.methods)),
            ]),
        ]

        for number, investigation in enumerate(self.investigations, 1):
            title = "INVESTIGATION" if len(self.investigations) == 1 \
                else f"INVESTIGATION {number}"
            rows = [
                ("target", investigation.target or "(not named)"),
                ("feature", investigation.feature or "(not named)"),
                ("method", investigation.tool),
                ("kind", investigation.kind or "static"),
            ]
            if investigation.entries:
                rows.append(("entries", _join(investigation.entries[:12])))
            if investigation.confidence:
                rows.append(("confidence", investigation.confidence))
            sections.append((title, rows))

        evidence = self.evidence
        if evidence:
            rows = [(item.label, item.text) for item in evidence[:40]]
            if len(evidence) > 40:
                rows.append(("more", f"+{len(evidence) - 40} evidence lines"))
            sections.append(("EVIDENCE", rows))

        if self.limitations:
            sections.append((
                "LIMITATIONS",
                [("limit", value) for value in self.limitations],
            ))
        if self.unknowns:
            sections.append((
                "UNKNOWNS",
                [("unknown", value) for value in self.unknowns],
            ))
        return sections

    def to_text(self) -> str:
        lines = ["TAMIAS INVESTIGATION DOSSIER", ""]
        for title, rows in self.sections():
            lines.append(title)
            for label, value in rows:
                lines.append(f"  {label}: {value}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


# ------------------------------------------------------------------ parsing
def _parse_investigate(tool: str, text: str) -> Optional[Investigation]:
    lines = text.splitlines()
    feature = _after(lines, "INVESTIGATION:")
    if not feature:
        return None
    target = _after(lines, "Target:")
    kind = "directory" if any(
        line.strip().startswith("Directory:") for line in lines) else "file"
    return Investigation(
        tool=tool,
        target=target,
        feature=feature,
        kind=kind,
        evidence=_evidence_lines(lines),
        entries=_entry_lines(lines),
        limitations=_list_block(lines, "Limitations:"),
        unknowns=_list_block(lines, "Unknowns:"),
        confidence=_after(lines, "Confidence:"),
    )


def _parse_trace(tool: str, text: str) -> Optional[Investigation]:
    lines = text.splitlines()
    feature = _after(lines, "TRACE:")
    if not feature:
        return None
    return Investigation(
        tool=tool,
        target=_after(lines, "Entry point:"),
        feature=feature,
        kind="trace",
        evidence=_trace_lines(lines),
        limitations=_list_block(lines, "Limitations:"),
        unknowns=_list_block(lines, "Unknowns:"),
        confidence=_after(lines, "Confidence:"),
    )


def _parse_structure(tool: str, text: str) -> Optional[Investigation]:
    lines = text.splitlines()
    target = _after(lines, "STRUCTURE ANALYSIS:")
    if not target:
        return None
    return Investigation(
        tool=tool,
        target=target,
        feature=_after(lines, "Focus:") or "structure",
        kind="structure",
        entries=_entry_lines(lines),
        limitations=_list_block(lines, "Limitations:"),
        unknowns=_list_block(lines, "Unknowns:"),
        confidence=_after(lines, "Confidence:"),
    )


def _parse_finish(tool: str, text: str) -> Optional[Investigation]:
    lines = text.splitlines()
    if not any("INVESTIGATION FINISHED" in line.upper() for line in lines[:2]):
        return None
    unknowns = _list_block(lines, "Unresolved questions:")
    if not unknowns:
        # the per-target cards already carry the targets and evidence
        return None
    return Investigation(
        tool=tool,
        target="session",
        feature="investigation summary",
        kind="session",
        unknowns=unknowns,
    )


_PARSERS = {
    "investigate_target": _parse_investigate,
    "trace_feature": _parse_trace,
    "analyze_structure": _parse_structure,
    "finish_investigation": _parse_finish,
}


# ------------------------------------------------------------------ helpers
def _after(lines: Iterable[str], prefix: str) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix):].strip()
    return ""


def _list_block(lines: Iterable[str], heading: str) -> list[str]:
    values: list[str] = []
    collecting = False
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith(heading):
            collecting = True
            rest = stripped[len(heading):].strip()
            if rest.lower() not in _NONE_VALUES:
                values.append(rest)
            continue
        if not collecting:
            continue
        if not stripped:
            break
        if stripped.startswith("- "):
            values.append(stripped[2:].strip())
        elif stripped.startswith("-"):
            values.append(stripped[1:].strip())
        else:
            break
    return [value for value in values
            if value and value.lower() not in _NONE_VALUES]


def _evidence_lines(lines: Iterable[str]) -> list[Evidence]:
    values: list[Evidence] = []
    seen: set[tuple[str, int, str]] = set()
    for line in lines:
        match = _EVIDENCE.match(line)
        if not match:
            continue
        path, number, text = match.groups()
        key = (path.strip(), int(number), text.strip())
        if key in seen:
            continue
        seen.add(key)
        values.append(Evidence(path=key[0], line=key[1], text=key[2]))
    return values


def _trace_lines(lines: Iterable[str]) -> list[Evidence]:
    values: list[Evidence] = []
    seen: set[tuple[str, int, str]] = set()
    for line in lines:
        match = _TRACE_STEP.match(line)
        if not match:
            continue
        path, number, text = match.groups()
        key = (path.strip(), int(number), text.strip())
        if key in seen:
            continue
        seen.add(key)
        values.append(Evidence(path=key[0], line=key[1], text=key[2]))
    return values


def _entry_lines(lines: Iterable[str]) -> list[str]:
    values: list[str] = []
    for line in lines:
        for kind, path in _FILE_ENTRY.findall(line):
            values.append(f"{kind.lower()} {path.strip()}")
    return values


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _join(values: Iterable[str], empty: str = "none") -> str:
    items = [value for value in values if value]
    return ", ".join(items) if items else empty


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"
