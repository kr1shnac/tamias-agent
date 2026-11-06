"""The agent's published plan, rendered from its own ``update_plan`` result.

A plan is a working plan until the core reports that a human signed it. When
the interactive Plan Contract is active, the core holds mutating tools until
the plan is approved; the card and receipt report the measured state rather
than assuming approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


_STATUS_BY_MARK = {
    "x": "completed",
    "~": "in_progress",
    " ": "pending",
}
_MARK_BY_STATUS = {status: mark for mark, status in _STATUS_BY_MARK.items()}
_PLAN_LINE = re.compile(r"^\s*\[(x|~| )\]\s+(.+?)\s*$")
_CONTRACT_LINE = re.compile(r"^\s*contract:\s*(.+?)\s*$", re.IGNORECASE)
_FILES_LINE = re.compile(r"^\s*files:\s*(.+?)\s*$", re.IGNORECASE)
_VERIFY_LINE = re.compile(r"^\s*verification:\s*(.+?)\s*$", re.IGNORECASE)
_RISK_LINE = re.compile(r"^\s*risk:\s*(.+?)\s*$", re.IGNORECASE)
_COST_LINE = re.compile(
    r"^\s*cost range:\s*([0-9.]+)\s*[-–]\s*([0-9.]+)", re.IGNORECASE)


@dataclass(frozen=True)
class PlanStep:
    content: str
    status: str

    @property
    def mark(self) -> str:
        return f"[{_MARK_BY_STATUS.get(self.status, ' ')}]"


@dataclass
class Plan:
    steps: list[PlanStep] = field(default_factory=list)
    signed: bool = False
    gate_active: bool = False
    files: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    cost_low: Optional[float] = None
    cost_high: Optional[float] = None

    @property
    def total(self) -> int:
        return len(self.steps)

    @property
    def done(self) -> int:
        return sum(1 for step in self.steps if step.status == "completed")

    @property
    def in_progress(self) -> int:
        return sum(1 for step in self.steps if step.status == "in_progress")

    @property
    def pending(self) -> int:
        return sum(1 for step in self.steps if step.status == "pending")

    def card_line(self) -> str:
        """The status line inside the open card (no 'P to open' hint)."""
        progress = f"{self.done}/{self.total} done"
        if self.in_progress == 1:
            state = "1 in progress"
        elif self.in_progress:
            state = f"{self.in_progress} in progress"
        else:
            state = "none in progress"
        contract = " · signed" if self.signed else ""
        files = f" · {len(self.files)} files" if self.files else ""
        return f"plan · {progress} · {state}{files}{contract}"

    def summary_line(self) -> str:
        return self.card_line() + " · P to open"

    def cost_text(self) -> str:
        if self.cost_low is None or self.cost_high is None:
            return "not estimated"
        return f"${self.cost_low:.4f}–${self.cost_high:.4f} (hypothetical)"

    def receipt_rows(self) -> list[tuple[str, str]]:
        rows = [
            ("progress", f"{self.done}/{self.total} done"),
            ("contract", "signed by user" if self.signed
             else ("not signed (writes held)" if self.gate_active
                   else "not signed (working plan)")),
            ("files", ", ".join(self.files) or "not declared"),
            ("verify", "; ".join(self.verification) or "not declared"),
            ("cost range", self.cost_text()),
        ]
        if self.risks:
            rows.append(("risks", "; ".join(self.risks)))
        for number, step in enumerate(self.steps[:10], 1):
            rows.append((f"{number} {step.mark}", step.content))
        if self.total > 10:
            rows.append(("more", f"+{self.total - 10} steps"))
        return rows

    def sections(self) -> list[tuple[str, list[tuple[str, str]]]]:
        rows = [
            ("progress", f"{self.done}/{self.total} done"),
            ("in progress", str(self.in_progress)),
            ("pending", str(self.pending)),
        ]
        plan_rows = []
        for number, step in enumerate(self.steps, 1):
            plan_rows.append((f"{number} {step.mark}", step.content))
        contract_rows = [
            ("status", "signed by user — writes are allowed"
             if self.signed else (
                 "not signed — writes are held" if self.gate_active
                 else "not signed — working plan")),
            ("files", ", ".join(self.files) or "not declared"),
            ("verify", "; ".join(self.verification) or "not declared"),
            ("cost range", self.cost_text()),
            ("risks", "; ".join(self.risks) or "not declared"),
        ]
        if not self.signed:
            contract_rows.append(
                ("next", "the agent must ask for approval before writing")
                if self.gate_active else
                ("limit", "no plan gate is active in this view"))
        elif not self.files:
            contract_rows.append(
                ("limit", "no files declared — path drift is not enforced"))
        return [
            ("PLAN", rows),
            ("STEPS", plan_rows),
            ("CONTRACT", contract_rows),
        ]

    def to_text(self) -> str:
        lines = ["TAMIAS PLAN", f"progress: {self.done}/{self.total} done", ""]
        for step in self.steps:
            lines.append(f"{step.mark} {step.content}")
        files_text = ", ".join(self.files) or "not declared"
        verify_text = "; ".join(self.verification) or "not declared"
        risks_text = "; ".join(self.risks) or "not declared"
        lines.extend([
            "",
            f"files: {files_text}",
            f"verification: {verify_text}",
            f"cost range: {self.cost_text()}",
            f"risks: {risks_text}",
            "",
            "contract: signed by user" if self.signed
            else ("contract: not signed (writes held)" if self.gate_active
                  else "contract: not signed (working plan)"),
        ])
        return "\n".join(lines).rstrip() + "\n"


def parse_plan(result: object) -> Optional[Plan]:
    """Parse the deterministic output of ``agent.update_plan``.

    Returns ``None`` for errors, empty output, or anything that does not carry
    the plan header + at least one status-marked step.
    """
    text = str(result or "")
    lines = text.splitlines()
    if not any("plan updated" in line.lower() for line in lines[:2]):
        return None

    steps: list[PlanStep] = []
    signed = False
    files: list[str] = []
    verification: list[str] = []
    risks: list[str] = []
    cost_low = cost_high = None

    for line in lines:
        contract = _CONTRACT_LINE.match(line)
        if contract and contract.group(1).lower().startswith("signed"):
            signed = True

        match = _PLAN_LINE.match(line)
        if match:
            mark, content = match.groups()
            content = content.strip()
            if content:
                steps.append(PlanStep(content=content,
                                      status=_STATUS_BY_MARK[mark]))
            continue

        files_match = _FILES_LINE.match(line)
        if files_match:
            value = files_match.group(1).strip()
            if value.lower() != "none":
                files.append(value)
            continue

        verify_match = _VERIFY_LINE.match(line)
        if verify_match:
            value = verify_match.group(1).strip()
            if value.lower() != "none":
                verification.append(value)
            continue

        risk_match = _RISK_LINE.match(line)
        if risk_match:
            risks.append(risk_match.group(1).strip())
            continue

        cost_match = _COST_LINE.match(line)
        if cost_match:
            try:
                cost_low = float(cost_match.group(1))
                cost_high = float(cost_match.group(2))
            except ValueError:
                cost_low = cost_high = None

    if not steps:
        return None
    return Plan(steps=steps, signed=signed, files=files,
                verification=verification, risks=risks,
                cost_low=cost_low, cost_high=cost_high)
