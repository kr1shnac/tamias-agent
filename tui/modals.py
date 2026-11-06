"""Modal screens for the TAMIAS TUI.

Kept together so the dialog styling follows the same single theme as the main
screen (docs/FRONTEND_REFERENCE.md §1). Every screen uses only palette colours:
cyan ``#00b8ff`` for neutral dialogs, red ``#fca5a5`` for boundary violations.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static
from rich.text import Text

from tui.credits import CreditsLedger
from tui.dossier import TurnDossier
from tui.plan import Plan
from tui.policy_view import BoundarySection, sections_text
from tui.receipt import TurnReceipt

DIALOG_CSS = """
ConfirmModal, BoundaryModal, HelpScreen, CreditsDashboard,
BoundaryCard, ReceiptModal, PlanCard, DossierCard, PlanContractModal,
DiffModal {
    align: center middle;
    background: rgba(0, 0, 0, 0.7);
}
#confirm-dialog, #boundary-dialog, #help-dialog, #credits-dialog {
    width: 62;
    height: auto;
    max-height: 80%;
    padding: 1 2;
    background: #1a1a1a;
    border: round #00b8ff;
    color: #e2e8f0;
}
#boundary-dialog { border: round #fca5a5; }
#credits-dialog { border: round #00b8ff; width: 64; }
#confirm-title, #boundary-title, #help-title, #credits-title {
    text-style: bold;
    color: #00ff9f;
    margin-bottom: 1;
    content-align: center middle;
}
#boundary-title { color: #fca5a5; }
#credits-title { color: #00b8ff; }

/* --- accountability surfaces ------------------------------------------ */
#boundary-card-dialog, #receipt-dialog, #plan-dialog, #dossier-dialog {
    width: 80;
    height: 82%;
    max-height: 90%;
    padding: 1 2;
    background: #1a1a1a;
    border: round #00b8ff;
    color: #e2e8f0;
}
#diff-dialog {
    width: 92;
    height: 86%;
    max-height: 92%;
    padding: 1 2;
    background: #1a1a1a;
    border: round #00b8ff;
    color: #e2e8f0;
}
#boundary-card-title, #receipt-title, #plan-title, #dossier-title,
#diff-title, #plan-contract-title {
    text-style: bold;
    color: #00b8ff;
    margin-bottom: 0;
    content-align: center middle;
}
#plan-contract-title { color: #fbbf24; }
#boundary-card-subtitle, #receipt-subtitle, #plan-subtitle,
#dossier-subtitle, #diff-subtitle, #plan-contract-subtitle {
    color: #94a3b8;
    content-align: center middle;
    margin-bottom: 1;
}
#boundary-card-body, #receipt-body, #plan-body, #dossier-body,
#diff-body, #plan-contract-body {
    height: 1fr;
    overflow-y: auto;
    padding-right: 1;
}
#diff-body {
    background: #111111;
    padding: 0 1;
}
#plan-contract-dialog {
    width: 74;
    height: 70%;
    max-height: 88%;
    padding: 1 2;
    background: #1a1a1a;
    border: round #fbbf24;
    color: #e2e8f0;
}
.plan-contract-step { height: auto; }
.plan-contract-mark { width: 5; text-style: bold; }
.plan-contract-content { width: 1fr; color: #e2e8f0; }
.plan-contract-fact { color: #94a3b8; margin-bottom: 1; }
.boundary-section-title, .receipt-section-title, .plan-section-title,
.dossier-section-title {
    text-style: bold;
    color: #00b8ff;
    margin-top: 1;
}
.boundary-row, .receipt-row, .decision-row, .plan-row, .dossier-row {
    height: auto;
}
.boundary-label, .receipt-label, .plan-label, .dossier-label {
    width: 18;
    color: #64748b;
}
.boundary-value, .receipt-value, .plan-value, .dossier-value {
    width: 1fr;
    color: #e2e8f0;
}
.plan-done { color: #00ff9f; }
.plan-active { color: #00b8ff; }
.plan-pending { color: #64748b; }
.dossier-label { width: 26; }
.dossier-evidence { color: #94a3b8; }
.dossier-evidence .dossier-label { color: #00b8ff; }
.dossier-evidence .dossier-value { color: #94a3b8; }
.boundary-good { color: #00ff9f; }
.boundary-warn { color: #fbbf24; }
.boundary-danger { color: #fca5a5; }
.boundary-muted { color: #64748b; }
.receipt-status {
    text-style: bold;
    content-align: center middle;
    margin-bottom: 1;
}
.decision-label {
    width: 12;
    color: #64748b;
}
.decision-value {
    width: 1fr;
    color: #e2e8f0;
}
#help-dialog { height: 80%; }
#help-body { height: 1fr; overflow-y: auto; }

.modal-body { color: #e2e8f0; }
.modal-hint {
    color: #64748b;
    margin-top: 1;
    content-align: center middle;
}
.modal-row { color: #94a3b8; }
.modal-key { color: #00b8ff; text-style: bold; }
.modal-section-title { text-style: bold; color: #00b8ff; }
"""


class _CopyableModal(ModalScreen[None]):
    """Small shared clipboard helper for read-only accountability screens."""

    def copy_text(self, text: str, label: str) -> None:
        self.run_worker(self._copy_text(text, label))

    async def _copy_text(self, text: str, label: str) -> None:
        try:
            await self.app.copy_to_clipboard(text)
            self.notify(f"{label} copied")
        except Exception as error:  # headless or no clipboard: never break
            self.notify(f"Copy failed: {error}", severity="error")


class ConfirmModal(ModalScreen[bool]):
    """Yes/No confirmation. Dismisses with True (yes), False (no/cancel).

    ``details`` turns a bare permission prompt into a decision card: the
    action, the reason, the effect and the scope are visible before the human
    answers. The fields are plain text (a model cannot inject dialog markup).
    """

    CSS = DIALOG_CSS

    BINDINGS = [
        ("y", "yes", "Yes"),
        ("n", "no", "No"),
        ("escape", "no", "Cancel"),
    ]

    def __init__(self, title: str, body: str,
                 details: list[tuple[str, str]] | None = None,
                 hint: str | None = None) -> None:
        super().__init__()
        self._title = title
        self._body = body
        self._details = list(details or [])
        self._hint = hint or "\\[Y] yes   \\[N] no   \\[esc] cancel"

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(self._title, id="confirm-title")
            yield Static(self._body, classes="modal-body")
            for label, value in self._details:
                with Horizontal(classes="decision-row"):
                    yield Static(label, classes="decision-label",
                                 markup=False)
                    yield Static(value, classes="decision-value",
                                 markup=False)
            yield Static(self._hint, classes="modal-hint")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class PlanContractModal(ModalScreen[bool]):
    """The Plan Contract signature: the exact steps the agent will run.

    While this screen is open the agent worker is blocked. There is no
    default-yes: ``y`` signs, while ``n``, Escape or closing the screen refuses
    and the turn stops without a write.
    """

    CSS = DIALOG_CSS

    BINDINGS = [
        ("y", "yes", "Sign"),
        ("n", "no", "Deny"),
        ("escape", "no", "Deny"),
    ]

    def __init__(self, contract: dict | list[dict]) -> None:
        super().__init__()
        if isinstance(contract, list):
            contract = {"todos": contract}
        self._contract = dict(contract or {})
        self._todos = list(self._contract.get("todos", []))

    def compose(self) -> ComposeResult:
        done = sum(1 for todo in self._todos
                   if str(todo.get("status", "")) == "completed")
        files = [str(item) for item in self._contract.get("files", [])]
        verification = [str(item)
                        for item in self._contract.get("verification", [])]
        risks = [str(item) for item in self._contract.get("risks", [])]
        cost = self._contract.get("cost_range_usd")
        cost_text = "not estimated"
        if isinstance(cost, (list, tuple)) and len(cost) == 2:
            try:
                cost_text = (f"${float(cost[0]):.4f}–${float(cost[1]):.4f} "
                             "(hypothetical)")
            except (TypeError, ValueError):
                pass

        with Vertical(id="plan-contract-dialog"):
            yield Static("◆ PLAN CONTRACT", id="plan-contract-title")
            yield Static(
                f"sign before the next write · {done}/{len(self._todos)} done"
                f" · {len(files)} files",
                id="plan-contract-subtitle",
            )
            with VerticalScroll(id="plan-contract-body"):
                yield Static("STEPS", classes="plan-section-title")
                for todo in self._todos:
                    status = str(todo.get("status", "pending"))
                    mark = {"completed": "[x]", "in_progress": "[~]"}.get(
                        status, "[ ]")
                    tone = {"completed": "plan-done",
                            "in_progress": "plan-active"}.get(
                                status, "plan-pending")
                    with Horizontal(classes="plan-contract-step"):
                        yield Static(mark, classes=f"plan-contract-mark {tone}",
                                     markup=False)
                        yield Static(str(todo.get("content", "")),
                                     classes="plan-contract-content",
                                     markup=False)

                yield Static("FILES", classes="plan-section-title")
                for path in files or ["not declared — path drift is not enforced"]:
                    yield Static(path, classes="plan-contract-fact", markup=False)

                yield Static("VERIFICATION", classes="plan-section-title")
                for command in verification or ["not declared"]:
                    yield Static(command, classes="plan-contract-fact",
                                 markup=False)

                yield Static("RISKS", classes="plan-section-title")
                for risk in risks or ["not declared"]:
                    yield Static(risk, classes="plan-contract-fact",
                                 markup=False)

                yield Static("COST RANGE", classes="plan-section-title")
                yield Static(cost_text, classes="plan-contract-fact",
                             markup=False)

            yield Static(
                "approving allows writes and shell commands for these steps",
                classes="modal-hint",
            )
            yield Static(
                "\\[Y] sign   \\[N] deny   \\[esc] deny (fail closed)",
                classes="modal-hint",
            )

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class BoundaryModal(ModalScreen[None]):
    """The red BLOCKED dialog shown when a tool leaves company work (§8)."""

    CSS = DIALOG_CSS

    BINDINGS = [
        ("enter", "ok", "OK"),
        ("space", "ok", "OK"),
        ("escape", "ok", "OK"),
    ]

    def __init__(self, assigned: str, attempted: str, result: str,
                 headline: str = "Outside company work area",
                 note: str = "") -> None:
        super().__init__()
        self._assigned = assigned
        self._attempted = attempted
        self._result = result
        self._headline = headline
        self._note = note

    def compose(self) -> ComposeResult:
        with Vertical(id="boundary-dialog"):
            yield Static("◆ BOUNDARY VIOLATION", id="boundary-title")
            yield Static(self._headline, classes="modal-body")
            yield Static(f"assigned : {self._assigned}", classes="modal-row")
            yield Static(f"attempted: {self._attempted}", classes="modal-row")
            yield Static("result   : BLOCKED", classes="modal-row")
            if self._note:
                yield Static(self._note, classes="modal-row")
            yield Static(self._result, classes="modal-hint")
            yield Static("\\[ OK ] → back to transcript", classes="modal-hint")

    def action_ok(self) -> None:
        self.dismiss(None)


class BoundaryCard(_CopyableModal):
    """The ``B`` boundary card: the active policy in human language.

    This is deliberately neutral cyan, not the red violation modal. It answers
    "what may this agent touch?" before anything goes wrong.
    """

    CSS = DIALOG_CSS

    BINDINGS = [
        ("escape", "close", "Close"),
        ("b", "close", "Close"),
        ("enter", "close", "Close"),
        ("c", "copy", "Copy"),
    ]

    def __init__(self, sections: list[BoundarySection], name: str = "",
                 company: str = "") -> None:
        super().__init__()
        self._sections = sections
        self._name = name or "active run"
        self._company = company or "unassigned"

    def compose(self) -> ComposeResult:
        with Vertical(id="boundary-card-dialog"):
            yield Static("◆ BOUNDARY CARD", id="boundary-card-title")
            yield Static(f"{self._name} · company {self._company}",
                         id="boundary-card-subtitle")
            with VerticalScroll(id="boundary-card-body"):
                for section in self._sections:
                    yield Static(section.title,
                                 classes="boundary-section-title")
                    for row in section.rows:
                        with Horizontal(classes="boundary-row"):
                            yield Static(row.label, classes="boundary-label",
                                         markup=False)
                            yield Static(
                                row.value,
                                classes=f"boundary-value boundary-{row.tone}",
                                markup=False,
                            )
            yield Static("\\[C] copy   \\[B/esc] close", classes="modal-hint")

    def action_close(self) -> None:
        self.dismiss(None)

    def action_copy(self) -> None:
        self.copy_text(sections_text(self._sections), "Boundary card")


class ReceiptModal(_CopyableModal):
    """The ``R`` receipt: what one turn actually did, measured."""

    CSS = DIALOG_CSS

    BINDINGS = [
        ("escape", "close", "Close"),
        ("r", "close", "Close"),
        ("enter", "close", "Close"),
        ("c", "copy", "Copy"),
    ]

    def __init__(self, receipt: TurnReceipt) -> None:
        super().__init__()
        self._receipt = receipt

    def compose(self) -> ComposeResult:
        receipt = self._receipt
        with Vertical(id="receipt-dialog"):
            yield Static(f"◆ RECEIPT · TURN {receipt.number}", id="receipt-title")
            yield Static(
                f"[{receipt.status_color}]{receipt.status_label}[/]  ·  "
                f"{receipt.summary_line()}",
                id="receipt-subtitle",
            )
            with VerticalScroll(id="receipt-body"):
                for section, rows in receipt.sections():
                    yield Static(section, classes="receipt-section-title")
                    for label, value in rows:
                        with Horizontal(classes="receipt-row"):
                            yield Static(label, classes="receipt-label",
                                         markup=False)
                            yield Static(value, classes="receipt-value",
                                         markup=False)
            yield Static("\\[C] copy   \\[R/esc] close", classes="modal-hint")

    def action_close(self) -> None:
        self.dismiss(None)

    def action_copy(self) -> None:
        self.copy_text(self._receipt.to_text(), "Receipt")


class DiffModal(_CopyableModal):
    """The ``V`` diff: a read-only review of the checkpoint's tracked changes.

    A checkpoint freezes this at turn end, so later edits cannot rewrite the
    evidence the receipt points at. The full text is bounded by the checkpoint
    layer; the modal never runs a command or writes a file.
    """

    CSS = DIALOG_CSS

    BINDINGS = [
        ("escape", "close", "Close"),
        ("v", "close", "Close"),
        ("enter", "close", "Close"),
        ("c", "copy", "Copy"),
    ]

    def __init__(self, checkpoint) -> None:
        super().__init__()
        self._checkpoint = checkpoint

    def compose(self) -> ComposeResult:
        checkpoint = self._checkpoint
        diffs = checkpoint.diff_files()
        summary = checkpoint.diff_summary()
        frozen = checkpoint.diff_frozen_at is not None
        path_word = "path" if summary["paths"] == 1 else "paths"
        subtitle = (
            f"{'frozen at turn end' if frozen else 'current state'} · "
            f"{summary['paths']} {path_word} · +{summary['added']} "
            f"-{summary['removed']}"
        )
        if checkpoint.shell_ran:
            subtitle += " · shell not captured"

        body = Text()
        if checkpoint.shell_ran:
            body.append(
                "Shell commands ran this turn; only tracked files are shown.\n",
                style="#fbbf24",
            )
        for index, item in enumerate(diffs):
            if index:
                body.append("\n")
            body.append(item.header() + "\n", style="bold #00b8ff")
            if item.note:
                body.append(f"  {item.note}\n", style="#fbbf24")
            for line in item.text.splitlines():
                if line.startswith(("+++", "---")):
                    style = "#64748b"
                elif line.startswith("@@"):
                    style = "#fbbf24"
                elif line.startswith("+"):
                    style = "#00ff9f"
                elif line.startswith("-"):
                    style = "#fca5a5"
                else:
                    style = "#cbd5e1"
                body.append(line + "\n", style=style)
        if not diffs:
            body.append("No tracked textual changes.\n", style="#64748b")
        self._text = body

        with Vertical(id="diff-dialog"):
            yield Static(f"◆ DIFF · {checkpoint.id}", id="diff-title")
            yield Static(subtitle, id="diff-subtitle")
            with VerticalScroll(id="diff-body"):
                yield Static(body, markup=False)
            yield Static("\\[C] copy   \\[V/esc] close", classes="modal-hint")

    def action_close(self) -> None:
        self.dismiss(None)

    def action_copy(self) -> None:
        self.copy_text(self._text.plain, "Diff")


class PlanCard(_CopyableModal):
    """The ``P`` plan card: the agent's published plan and its contract state.

    A plan is labelled ``signed`` only when the core reports that a human
    approved it; otherwise it is a working plan and the card says so.
    """

    CSS = DIALOG_CSS

    BINDINGS = [
        ("escape", "close", "Close"),
        ("p", "close", "Close"),
        ("enter", "close", "Close"),
        ("c", "copy", "Copy"),
    ]

    def __init__(self, plan: Plan) -> None:
        super().__init__()
        self._plan = plan

    def compose(self) -> ComposeResult:
        plan = self._plan
        with Vertical(id="plan-dialog"):
            yield Static("◆ PLAN", id="plan-title")
            yield Static(plan.card_line(), id="plan-subtitle")
            with VerticalScroll(id="plan-body"):
                for section, rows in plan.sections():
                    yield Static(section, classes="plan-section-title")
                    for label, value in rows:
                        tone = ""
                        if "[x]" in label:
                            tone = " plan-done"
                        elif "[~]" in label:
                            tone = " plan-active"
                        elif "[ ]" in label:
                            tone = " plan-pending"
                        with Horizontal(classes="plan-row"):
                            yield Static(label, classes=f"plan-label{tone}",
                                         markup=False)
                            yield Static(value, classes="plan-value",
                                         markup=False)
            yield Static("\\[C] copy   \\[P/esc] close", classes="modal-hint")

    def action_close(self) -> None:
        self.dismiss(None)

    def action_copy(self) -> None:
        self.copy_text(self._plan.to_text(), "Plan")


class DossierCard(_CopyableModal):
    """The ``D`` card: the evidence the investigative tools actually returned."""

    CSS = DIALOG_CSS

    BINDINGS = [
        ("escape", "close", "Close"),
        ("d", "close", "Close"),
        ("enter", "close", "Close"),
        ("c", "copy", "Copy"),
    ]

    def __init__(self, dossier: TurnDossier) -> None:
        super().__init__()
        self._dossier = dossier

    def compose(self) -> ComposeResult:
        dossier = self._dossier
        with Vertical(id="dossier-dialog"):
            yield Static("◆ INVESTIGATION DOSSIER", id="dossier-title")
            yield Static(dossier.card_line(), id="dossier-subtitle")
            with VerticalScroll(id="dossier-body"):
                for section, rows in dossier.sections():
                    yield Static(section, classes="dossier-section-title")
                    for label, value in rows:
                        classes = "dossier-row"
                        if section == "EVIDENCE":
                            classes += " dossier-evidence"
                        with Horizontal(classes=classes):
                            yield Static(label, classes="dossier-label",
                                         markup=False)
                            yield Static(value, classes="dossier-value",
                                         markup=False)
            yield Static("\\[C] copy   \\[D/esc] close", classes="modal-hint")

    def action_close(self) -> None:
        self.dismiss(None)

    def action_copy(self) -> None:
        self.copy_text(self._dossier.to_text(), "Dossier")


class HelpScreen(ModalScreen[None]):
    """The `H` help overlay (§9)."""

    CSS = DIALOG_CSS

    BINDINGS = [("escape", "dismiss_help", "Close"),
                ("h", "dismiss_help", "Close")]

    ROWS = [
        ("↑ / ↓", "move between panels / history"),
        ("← / →", "switch sections (Task / Credits / Session)"),
        ("Enter", "activate focused panel / submit"),
        ("T", "toggle task & progress view"),
        ("C", "complete current task (confirmation modal)"),
        ("M", "cycle models (free → mid → premium)"),
        ("B", "boundary card — what I may touch"),
        ("R", "receipt for the last turn"),
        ("P", "plan card — the published plan and its contract"),
        ("D", "investigation dossier — evidence it saw"),
        ("Z", "checkpoint — preview or restore the last turn's files"),
        ("V", "diff — review the last turn's tracked changes"),
        ("Y / N", "sign / deny a published plan contract"),
        ("H", "this help overlay"),
        ("Q / Ctrl+C", "quit"),
        ("F3", "spend (USD) dashboard"),
        ("/model", "open the model picker"),
        ("/task", "toggle the task board"),
        ("/complete", "complete the current task"),
        ("/boundary", "open the boundary card"),
        ("/receipt", "open the last receipt"),
        ("/plan", "open the published plan"),
        ("/dossier", "open the investigation dossier"),
        ("/checkpoint", "preview or restore the last file checkpoint"),
        ("/diff", "review the last turn's tracked changes"),
        ("/clear", "clear the transcript"),
        ("/quit", "exit"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static("TAMIAS — help", id="help-title")
            key_w = max(len(f"[{key}]") for key, _ in self.ROWS)
            with VerticalScroll(id="help-body"):
                for key, description in self.ROWS:
                    label = f"[{key}]".ljust(key_w)
                    yield Static(f"{label}  {description}", classes="modal-row",
                                 markup=False)
            yield Static("type / for the command palette · F3 spend · Ctrl+T task",
                         classes="modal-hint")

    def action_dismiss_help(self) -> None:
        self.dismiss(None)


class CreditsDashboard(ModalScreen[None]):
    """The `F3` spend dashboard (§5).

    Every row it shows is a figure the ledger recorded from the provider.
    Includes per-model breakdown and a hypothetical list-price comparison.
    """

    CSS = DIALOG_CSS

    BINDINGS = [("escape", "dismiss_dash", "Close"),
                ("f3", "dismiss_dash", "Close")]

    def __init__(self, ledger: CreditsLedger) -> None:
        super().__init__()
        self._ledger = ledger

    def compose(self) -> ComposeResult:
        with Vertical(id="credits-dialog"):
            yield Static("◆ SPEND & SAVINGS ANALYSIS", id="credits-title")

            # Session totals
            yield Static("", classes="modal-row")
            yield Static("SESSION TOTALS", classes="modal-row modal-section-title")
            for label, value in self._ledger.dashboard_lines():
                yield Static(f"{label}: {value}", classes="modal-row")

            # Per-model breakdown
            yield Static("", classes="modal-row")
            yield Static("PER-MODEL BREAKDOWN", classes="modal-row modal-section-title")
            for label, value in self._ledger.model_dashboard_lines():
                yield Static(f"{label}: {value}", classes="modal-row")

            # Hypothetical list-price comparison (never called "saved")
            yield Static("", classes="modal-row")
            yield Static("COST COMPARISON (HYPOTHETICAL)", classes="modal-row modal-section-title")
            total_spent = self._ledger.spent_usd
            yield Static(
                f"    actual spend   : ${total_spent:.4f} (provider-billed USD)",
                classes="modal-row",
            )
            yield Static(
                f"    premium equiv  : ${self._ledger.premium_equivalent_usd():.4f} "
                f"(same tokens at list premium rates)",
                classes="modal-row",
            )
            yield Static(
                f"    retail delta   : ${self._ledger.retail_delta_usd():.4f} "
                f"(hypothetical, not a measured saving)",
                classes="modal-row",
            )
            if self._ledger.model_switches:
                yield Static("", classes="modal-row")
                yield Static("MODEL SWITCHES", classes="modal-row",
                             style="bold #fca5a5")
                for sw in self._ledger.model_switches[-10:]:
                    yield Static(
                        f"    {sw['old_model']} → {sw['new_model']}  "
                        f"({sw['old_tier']} → {sw['new_tier']})  "
                        f"reason: {sw['reason']}",
                        classes="modal-row",
                    )

            yield Static("", classes="modal-row")
            yield Static("\\[esc] close", classes="modal-hint")

    def action_dismiss_dash(self) -> None:
        self.dismiss(None)
