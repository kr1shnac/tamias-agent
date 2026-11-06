"""Human-readable view of the active deployment policy (docs/PREMIUM-AGENT.md).

The boundary card is not a settings page and not a permission prompt. It is the
same fence the dispatcher checks, rendered in the operator's language, so a
reviewer can answer "what may this agent touch?" without reading TOML.

Pure Python; no Textual and no agent import, so it can be tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass(frozen=True)
class BoundaryRow:
    label: str
    value: str
    tone: str = "normal"      # normal | good | warn | danger | muted


@dataclass(frozen=True)
class BoundarySection:
    title: str
    rows: list[BoundaryRow] = field(default_factory=list)


def _values(items: Optional[Iterable], empty: str) -> list[str]:
    values = [str(item) for item in (items or []) if str(item).strip()]
    return values if values else [empty]


def _fmt(items: Optional[Iterable], empty: str, limit: int = 6) -> str:
    values = _values(items, empty)
    if len(values) <= limit:
        return ", ".join(values)
    shown = ", ".join(values[:limit])
    return f"{shown} (+{len(values) - limit} more)"


def _tools(items: Optional[Iterable], empty: str) -> str:
    values = [str(item) for item in (items or []) if str(item).strip()]
    if not values:
        return empty
    label = f"{len(values)} tool{'s' if len(values) != 1 else ''} · "
    shown = ", ".join(values[:5])
    suffix = f" (+{len(values) - 5} more)" if len(values) > 5 else ""
    return label + shown + suffix


def boundary_sections(policy, company_id: str | None = None
                      ) -> list[BoundarySection]:
    """Turn a ``PolicyProfile`` (or ``None``) into renderable sections.

    ``None`` is reported honestly as unbounded development mode. It is never
    painted as "all clear" or as if a deployment policy were active.
    """
    if policy is None:
        company = company_id or "not assigned"
        return [
            BoundarySection("STATUS", [
                BoundaryRow("deployment policy", "none loaded", "warn"),
                BoundaryRow("company fence", company, "normal"),
                BoundaryRow("tool gate", "not policy-restricted", "warn"),
                BoundaryRow("path gate", "workspace + company fence only",
                            "warn"),
                BoundaryRow("audit", "not configured", "warn"),
            ]),
            BoundarySection("WHAT THIS MEANS", [
                BoundaryRow(
                    "note",
                    "This process has no deployment policy. That is unbounded "
                    "development mode, not a bounded demo.",
                    "danger",
                ),
                BoundaryRow(
                    "next",
                    "Start with --policy or TAMIAS_POLICY to load a company "
                    "boundary.",
                    "muted",
                ),
            ]),
        ]

    name = getattr(policy, "name", "") or "(unnamed use case)"
    company = getattr(policy, "company", "") or company_id or "unassigned"
    root = getattr(policy, "root", "") or "(not named)"
    read_only = bool(getattr(policy, "read_only", False))
    tool_allow = getattr(policy, "tool_allow", []) or []
    tool_deny = getattr(policy, "tool_deny", []) or []
    tool_ask = getattr(policy, "tool_ask", []) or []
    shell_allow = getattr(policy, "shell_allow", []) or []
    shell_deny = getattr(policy, "shell_deny", []) or []
    allow_write = getattr(policy, "allow_write", []) or []
    deny_read = getattr(policy, "deny_read", []) or []
    model_allow = getattr(policy, "model_allow", []) or []
    domain_allow = getattr(policy, "domain_allow", []) or []
    domain_deny = getattr(policy, "domain_deny", []) or []
    audit_path = getattr(policy, "audit_path", "") or ""

    mode = "read-only (no writes, no shell)" if read_only else "read / write"
    write_scope = (
        "blocked (read-only use case)" if read_only
        else _fmt(allow_write, "company work area only (no extra policy scope)")
    )

    sections = [
        BoundarySection("STATUS", [
            BoundaryRow("use case", name, "good"),
            BoundaryRow("company", company, "normal"),
            BoundaryRow("product root", root, "normal"),
            BoundaryRow("mode", mode, "warn" if read_only else "normal"),
            BoundaryRow("enforcement", "checked before every tool call",
                        "good"),
        ]),
        BoundarySection("WHAT I MAY REACH", [
            BoundaryRow("tools", _tools(tool_allow, "all tools")),
            BoundaryRow("tools denied", _fmt(tool_deny, "none"), "muted"),
            BoundaryRow("approval needed", _fmt(tool_ask, "none")),
            BoundaryRow("shell allowed", _fmt(shell_allow, "unrestricted")),
            BoundaryRow("shell denied", _fmt(shell_deny, "none"), "muted"),
            BoundaryRow("writes", write_scope,
                        "warn" if read_only else "good"),
            BoundaryRow("reads denied", _fmt(deny_read, "none"), "muted"),
            BoundaryRow("models", _fmt(
                model_allow,
                "all runnable models (free unless paid is enabled)")),
        ]),
        BoundarySection("WHAT I WILL WORK ON", [
            BoundaryRow("must mention", _fmt(domain_allow, "domain gate off")),
            BoundaryRow("refused", _fmt(domain_deny, "none"), "muted"),
            BoundaryRow(
                "request gate",
                "refused before any model call" if domain_allow
                else "no request scope gate",
                "good" if domain_allow else "warn",
            ),
        ]),
        BoundarySection("RECORD", [
            BoundaryRow("audit", audit_path or "in-memory only (not persisted)",
                        "good" if audit_path else "warn"),
            BoundaryRow("receipt", "every turn, from measured events"),
            BoundaryRow("ask policy", "no answer = no (fail closed)"),
        ]),
        BoundarySection("WHY THIS CARD EXISTS", [
            BoundaryRow(
                "note",
                "This is the same policy the dispatcher checks. It is a "
                "contract, not a permission prompt.",
                "muted",
            ),
        ]),
    ]
    return sections


def sections_text(sections: Iterable[BoundarySection]) -> str:
    """Plain text for copying or attaching to a review."""
    lines: list[str] = []
    for section in sections:
        lines.append(section.title)
        for row in section.rows:
            lines.append(f"  {row.label}: {row.value}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
