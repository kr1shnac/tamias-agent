"""Tests for the premium accountability surfaces.

The receipt, boundary card, plan card and dossier are products, not decoration:
every row has to come from a measured event, the active policy, or the
investigation tools' own evidence lines. A refusal has to stay distinguishable
from a completed turn.
"""

import asyncio
import contextlib
import queue
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

from tui.policy_view import boundary_sections, sections_text
from tui.receipt import TurnReceipt, is_verification


@pytest.fixture(autouse=True)
def _real_rich():
    """Drop test_agent.py's process-wide rich stubs before Textual imports.

    Same rule as ``test_tui_features.py``: the core suite fakes rich, while
    Textual needs the real package. A real package has ``__path__``; the stubs
    do not.
    """
    loaded = sys.modules.get("rich")
    if loaded is not None and getattr(loaded, "__path__", None) is None:
        for name in [name for name in sys.modules
                     if name == "rich" or name.startswith("rich.")]:
            del sys.modules[name]
    yield


def _run(coro):
    return asyncio.run(coro)


@contextlib.asynccontextmanager
async def _no_screen_wait():
    from textual.pilot import Pilot

    async def ready(self, timeout=30.0):
        return True

    with mock.patch.object(Pilot, "_wait_for_screen", ready):
        yield


async def _press(pilot, key, settle=0.15):
    async with _no_screen_wait():
        await pilot.press(key)
    await asyncio.sleep(settle)


def _policy(**overrides):
    values = dict(
        name="todo-app",
        company="todoinc",
        root="company/work/todoinc/apps/todo",
        read_only=False,
        tool_allow=["read_file", "write_file", "run_shell"],
        tool_deny=[],
        tool_ask=["write_file"],
        shell_allow=["python3 -m pytest"],
        shell_deny=["rm "],
        allow_write=["company/work/todoinc/apps/todo/**"],
        deny_read=["**/*.pem"],
        model_allow=[],
        domain_allow=["todo"],
        domain_deny=["chatbot"],
        audit_path="policies/todoinc-todo.audit.jsonl",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


# --------------------------------------------------------------- receipt facts


def test_receipt_counts_only_successful_work_as_a_change():
    receipt = TurnReceipt(number=1, prompt="add a todo")
    receipt.note_tool_start("1", "read_file", '{"file_path": "a.py"}')
    receipt.note_tool_end("1", "read_file", "ok", True, 0.1)

    # a failed write is a failure, not a change
    receipt.note_tool_start(
        "2", "write_file", '{"file_path": "b.py", "content": "x"}')
    receipt.note_tool_end("2", "write_file", "Error: denied", False, 0.1)

    assert receipt.files_read == ["a.py"]
    assert receipt.files_written == []
    assert receipt.changed_files == []
    assert receipt.failures == [("write_file", "Error: denied")]
    assert receipt.tools == {"read_file": 1, "write_file": 1}


def test_receipt_separates_a_policy_boundary_from_a_user_denial():
    receipt = TurnReceipt(number=2, prompt="read secrets")
    receipt.note_tool_start("1", "read_file", '{"file_path": "/etc/passwd"}')
    receipt.note_tool_end(
        "1", "read_file",
        "Error: policy deny - path '/etc/passwd' is off-limits",
        False, 0.0,
    )
    assert receipt.boundary
    assert receipt.policy_denials == 1
    assert receipt.ask_denials == 0
    assert receipt.files_read == []
    assert receipt.status == "blocked"

    receipt.note_ask("write_file", "policy asks")
    receipt.note_tool_start("2", "write_file", '{"file_path": "a.py"}')
    receipt.note_tool_end(
        "2", "write_file", "Error: policy ask denied - policy asks",
        False, 0.0,
    )
    assert receipt.asks == 1
    assert receipt.ask_denials == 1
    assert receipt.policy_denials == 1


def test_receipt_marks_a_plan_drift_as_a_contract_block():
    receipt = TurnReceipt(number=8, prompt="write outside the plan")
    receipt.note_plan_block(
        "Error: plan contract - path 'other.py' is not in the signed plan")
    receipt.finish(prompt_tokens=10, completion_tokens=2, cost_usd=0.0)

    assert receipt.plan_blocked is True
    assert receipt.status == "plan blocked"
    assert "path 'other.py'" in receipt.to_text()
    assert "plan contract: blocked" in receipt.to_text()


def test_receipt_does_not_count_a_plan_held_shell_as_a_failed_check():
    receipt = TurnReceipt(number=9, prompt="run before signing")
    receipt.note_tool_start("1", "run_shell", '{"command": "pytest -q"}')
    receipt.note_tool_end(
        "1", "run_shell",
        "Error: plan contract - the published plan is not signed", False, 0.0)

    assert receipt.plan_blocked is True
    assert receipt.failures == []
    assert receipt.shell_runs == []
    assert receipt.status == "plan blocked"


def test_receipt_records_a_dossier_hold_without_calling_it_a_failure():
    receipt = TurnReceipt(number=7, prompt="write before investigating")
    receipt.note_tool_start(
        "1", "write_file", '{"file_path": "a.py", "content": "x"}')
    receipt.note_tool_end(
        "1", "write_file",
        "Error: dossier gate - no investigation evidence yet", False, 0.0)

    assert receipt.dossier_blocks == 1
    assert receipt.failures == []
    assert receipt.files_written == []
    assert "dossier holds" in receipt.to_text()
    assert "held until investigation evidence existed" in receipt.to_text()


def test_receipt_marks_a_refusal_before_any_model_call():
    receipt = TurnReceipt(number=3, prompt="build a chatbot")
    receipt.note_boundary(
        "Error: boundary - 'chatbot' is outside use case 'todo-app'")
    receipt.finish(prompt_tokens=0, completion_tokens=0, cost_usd=0.0)
    assert receipt.refused
    assert receipt.status == "refused"
    assert receipt.cost_text() == "$0.0000 (no model call)"
    assert "no model call" in receipt.summary_line()


def test_receipt_never_turns_an_unknown_cost_into_a_free_turn():
    receipt = TurnReceipt(number=4, prompt="do work")
    receipt.finish(prompt_tokens=10, completion_tokens=2, cost_usd=None,
                   unpriced_steps=1)
    assert receipt.cost_text().startswith("cost unknown")
    assert "$0.0000" not in receipt.cost_text()
    assert "provider-billed" not in receipt.cost_text()


def test_verification_detection_is_explicit_not_a_word_match():
    assert is_verification("python3 -m pytest -q")
    assert is_verification("npm test")
    assert is_verification("ruff check .")
    assert is_verification("bash demo/check_all.sh")
    assert is_verification("cd src && python -m pytest -q")
    assert is_verification("FOO=1 pytest")
    # a test runner's name as an argument is not a check
    assert not is_verification("pip install pytest")
    assert not is_verification("echo pytest")
    assert not is_verification("grep pytest README.md")
    # "test" in a filename is not a test run
    assert not is_verification("cat test.txt")
    assert not is_verification("git status")


def test_receipt_text_never_claims_a_saving_or_a_verification_it_lacks():
    receipt = TurnReceipt(number=5, prompt="change a file")
    receipt.note_tool_start(
        "1", "write_file", '{"file_path": "a.py", "content": "x"}')
    receipt.note_tool_end("1", "write_file", "ok", True, 0.1)
    receipt.finish(100, 20, 0.0, 0, "free/model", "free")
    text = receipt.to_text().lower()
    assert "saved" not in text
    assert "baseline" not in text
    assert "verified" not in text
    assert "no verification command was run" in text


def test_receipt_summary_uses_measured_counts():
    receipt = TurnReceipt(number=6, prompt="fix it")
    receipt.note_tool_start("1", "run_shell", '{"command": "pytest -q"}')
    receipt.note_tool_end("1", "run_shell", "1 passed", True, 1.2)
    receipt.finish(100, 20, 0.0042, 0, "paid/model", "mid")
    line = receipt.summary_line()
    assert "1/1 checks passed" in line
    assert "$0.0042 (provider-billed)" in line
    assert "R to open" in line


# --------------------------------------------------------- boundary card facts


def test_boundary_card_reads_the_real_policy_fields():
    text = sections_text(boundary_sections(_policy()))
    assert "todo-app" in text
    assert "company/work/todoinc/apps/todo" in text
    assert "write_file" in text
    assert "company/work/todoinc/apps/todo/**" in text
    assert "chatbot" in text
    assert "no answer = no (fail closed)" in text
    assert "policies/todoinc-todo.audit.jsonl" in text


def test_boundary_card_is_honest_when_no_policy_is_loaded():
    text = sections_text(boundary_sections(None, company_id="todoinc"))
    assert "none loaded" in text
    assert "unbounded development mode" in text
    assert "not policy-restricted" in text
    assert "todoinc" in text


def test_read_only_policy_says_writes_are_blocked():
    text = sections_text(boundary_sections(_policy(read_only=True)))
    assert "read-only" in text
    assert "blocked (read-only use case)" in text


# ---------------------------------------------------------------- TUI surfaces


def test_b_opens_the_boundary_card():
    from textual.widgets import Static

    from tui.app import TAMIASApp
    from tui.modals import BoundaryCard

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("escape")       # nav mode
            await pilot.press("b")
            await pilot.pause()
            assert isinstance(app.screen, BoundaryCard)
            text = " ".join(str(widget.render())
                            for widget in app.screen.query(Static))
            assert "BOUNDARY CARD" in text
            assert "deployment policy" in text
            assert "none loaded" in text
            await _press(pilot, "escape")

    _run(drive())


def test_boundary_card_renders_an_active_policy():
    from textual.widgets import Static

    from tui.app import TAMIASApp
    from tui.modals import BoundaryCard

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue(), company_id="todoinc")
        app._active_policy = lambda: _policy()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.show_boundary_card()
            await pilot.pause()
            assert isinstance(app.screen, BoundaryCard)
            text = " ".join(str(widget.render())
                            for widget in app.screen.query(Static))
            assert "todo-app" in text
            assert "company/work/todoinc/apps/todo" in text
            assert "write_file" in text
            await _press(pilot, "escape")

    _run(drive())


def test_slash_receipt_opens_the_last_measured_receipt():
    from textual.widgets import Static

    from tui.app import TAMIASApp
    from tui.modals import ReceiptModal

    receipt = TurnReceipt(number=1, prompt="add a todo")
    receipt.note_tool_start("1", "run_shell", '{"command": "pytest -q"}')
    receipt.note_tool_end("1", "run_shell", "1 passed", True, 1.0)
    receipt.finish(100, 20, 0.0, 0, "free/model", "free")

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        app.last_receipt = receipt
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.query_one("#user-input").value = "/receipt"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ReceiptModal)
            text = " ".join(str(widget.render())
                            for widget in app.screen.query(Static))
            assert "RECEIPT" in text
            assert "add a todo" in text
            assert "pytest -q" in text
            assert "1 passed" in text or "passed" in text
            await _press(pilot, "escape")

    _run(drive())


def test_turn_end_builds_a_receipt_and_a_transcript_line():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.start_agent_turn("add a todo")
            app.start_tool("t1", "read_file", '{"file_path": "a.py"}')
            app.end_tool("t1", "ok", True, 0.1)
            app.end_agent_turn(12, 3, 0.0, 0, "model", "free", {})
            await pilot.pause()

            receipt = app.last_receipt
            assert receipt is not None
            assert receipt.prompt == "add a todo"
            assert receipt.files_read == ["a.py"]
            assert receipt.cost_text() == "$0.0000 (provider-billed)"
            assert receipt in app.receipts

            line = " ".join(str(node.render())
                            for node in app.query(".receipt-line"))
            assert "receipt" in line.lower()
            assert "R to open" in line

    _run(drive())


def test_a_refused_turn_still_gets_an_honest_receipt():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            app._pending_prompt = "build a chatbot"
            app.handle_status_update(
                "Error: boundary - 'chatbot' is outside use case 'todo-app'",
                False,
            )
            app.end_agent_turn(0, 0, 0.0, 0, "", "", {})
            await pilot.pause()

            receipt = app.last_receipt
            assert receipt is not None
            assert receipt.refused
            assert "no model call" in receipt.summary_line()
            assert "REFUSED" in receipt.summary_line()
            assert "saved" not in receipt.to_text().lower()

    _run(drive())


def test_a_plan_denial_without_a_tool_card_is_still_counted():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.start_agent_turn("change a todo")
            # the core emits ToolEnd for a plan-level denial without ToolStart
            app.end_tool(
                "missing-card",
                "Error: boundary - the plan was refused because another "
                "call in this step left the project",
                False,
            )
            app.end_agent_turn(10, 0, 0.0, 0, "model", "free", {})
            await pilot.pause()

            receipt = app.last_receipt
            assert receipt is not None
            assert receipt.boundary
            assert receipt.policy_denials == 1
            assert "1 policy denial" in receipt.summary_line()
            assert "no files changed" in receipt.summary_line()

    _run(drive())


def test_an_early_error_still_gets_a_receipt():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            app._pending_prompt = "answer this"
            app.handle_status_update("Error: provider unavailable", False)
            app.end_agent_turn(0, 0, None, 1, "", "", {})
            await pilot.pause()

            receipt = app.last_receipt
            assert receipt is not None
            assert receipt.error == "provider unavailable"
            assert receipt.status == "error"
            assert receipt.cost_text().startswith("cost unknown")
            assert "provider unavailable" in receipt.to_text()

    _run(drive())


def test_tool_ask_is_a_decision_card_not_a_bare_prompt():
    from tui.app import TAMIASApp
    from tui.modals import ConfirmModal

    class Gate:
        def __init__(self):
            self.answer = None

        def resolve(self, allowed):
            self.answer = allowed

    gate = Gate()

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue(), ask_gate=gate)
        async with app.run_test(size=(120, 40)) as pilot:
            app.start_agent_turn("add a todo")
            app.confirm_tool_ask(
                "write_file",
                '{"file_path": "company/work/todoinc/apps/todo/a.py"}',
                "policy asks for writes",
            )
            await pilot.pause()
            assert isinstance(app.screen, ConfirmModal)
            assert any("this one call only" in value
                       for _, value in app.screen._details)
            assert any("policy asks for writes" in value
                       for _, value in app.screen._details)
            assert app.current_receipt.asks == 1

            await _press(pilot, "n")
            assert gate.answer is False

    _run(drive())


# ------------------------------------------------------- plan & dossier facts

PLAN_TEXT = """plan updated - 1/3 done
[x] Read the todo model
[~] Add priority field
[ ] Run pytest
Keep exactly one in_progress and move it on as you finish.
"""

INVESTIGATION_TEXT = """INVESTIGATION: add priority
Target: company/work/todoinc/apps/todo
Evidence-based findings (REA-style):
============================================================

Directory: company/work/todoinc/apps/todo

Structure (top level):
  [FILE] README.md
  [DIR] src
  [DIR] tests

Feature traces for 'add priority':
  [evidence] src/todo.py:4  def add(items, title):
  [evidence] src/todo.py:5  items.append({"title": title, "done": False})

Limitations:
  - static analysis only - runtime behavior not observed
Unknowns:
  - whether a migration is required
Confidence: medium (evidence-based, static analysis only)
"""

TRACE_TEXT = """TRACE: complete a todo
Entry point: company/work/todoinc/apps/todo/src/todo.py
Max depth: 5
============================================================

Trace chain (2 steps):
  Step 1 | company/work/todoinc/apps/todo/src/todo.py:9 | def complete(items, title):
  Step 2 | company/work/todoinc/apps/todo/src/todo.py:10 | for item in items:

Limitations: static trace only - dynamic behavior not observed
Confidence: medium (based on static code analysis)
"""

STRUCTURE_TEXT = """STRUCTURE ANALYSIS: company/work/todoinc/apps/todo
Focus: structure
============================================================

Files found: 2
  [FILE] src/todo.py
  [FILE] tests/test_todo.py

Limitations: static structure only - runtime behavior not observed
Confidence: medium (based on static file analysis)
"""


def test_z_previews_and_restores_the_last_checkpoint():
    import checkpoints
    import tempfile
    from pathlib import Path

    from textual.widgets import Static

    from tui.app import TAMIASApp
    from tui.modals import ConfirmModal

    async def drive():
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "note.txt")
            target.write_text("original")
            checkpoint = checkpoints.Checkpoint.start("change the note", tmp)
            checkpoint.capture(str(target))
            target.write_text("changed")

            app = TAMIASApp(
                queue.Queue(), queue.Queue(),
                checkpoint_lookup=lambda cp_id: checkpoint
                if cp_id == checkpoint.id else None,
            )
            async with app.run_test(size=(120, 32)) as pilot:
                app.last_checkpoint_id = checkpoint.id
                app.action_checkpoint()
                await pilot.pause()

                assert isinstance(app.screen, ConfirmModal)
                text = " ".join(str(widget.render())
                                for widget in app.screen.query(Static))
                assert "note.txt" in text and "modified" in text

                await _press(pilot, "y")
                assert target.read_text() == "original"
                assert app.last_checkpoint_id == ""
                assert checkpoint.restored_at is not None

    _run(drive())


def test_z_cancel_leaves_the_checkpoint_files_untouched():
    import checkpoints
    import tempfile
    from pathlib import Path

    from tui.app import TAMIASApp
    from tui.modals import ConfirmModal

    async def drive():
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "note.txt")
            target.write_text("original")
            checkpoint = checkpoints.Checkpoint.start("change the note", tmp)
            checkpoint.capture(str(target))
            target.write_text("changed")

            app = TAMIASApp(
                queue.Queue(), queue.Queue(),
                checkpoint_lookup=lambda cp_id: checkpoint
                if cp_id == checkpoint.id else None,
            )
            async with app.run_test(size=(120, 32)) as pilot:
                app.last_checkpoint_id = checkpoint.id
                app.action_checkpoint()
                await pilot.pause()

                assert isinstance(app.screen, ConfirmModal)
                await _press(pilot, "n")

                assert target.read_text() == "changed"
                assert app.last_checkpoint_id == checkpoint.id
                assert checkpoint.restored_at is None

    _run(drive())


def test_z_keeps_a_failed_checkpoint_available_for_retry():
    import checkpoints
    import tempfile
    from pathlib import Path

    from tui.app import TAMIASApp
    from tui.modals import ConfirmModal

    async def drive():
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "newdir")
            checkpoint = checkpoints.Checkpoint.start("make a directory", tmp)
            checkpoint.capture(str(target), is_dir=True)
            target.mkdir()
            (target / "user-file.txt").write_text("keep me")

            app = TAMIASApp(
                queue.Queue(), queue.Queue(),
                checkpoint_lookup=lambda cp_id: checkpoint
                if cp_id == checkpoint.id else None,
            )
            async with app.run_test(size=(120, 32)) as pilot:
                app.last_checkpoint_id = checkpoint.id
                app.action_checkpoint()
                await pilot.pause()

                assert isinstance(app.screen, ConfirmModal)
                await _press(pilot, "y")

                assert app.last_checkpoint_id == checkpoint.id
                assert checkpoint.restored_at is None
                assert target.is_dir()

    _run(drive())


def test_v_shows_the_frozen_checkpoint_diff():
    import checkpoints
    import tempfile
    from pathlib import Path

    from textual.widgets import Static

    from tui.app import TAMIASApp
    from tui.modals import DiffModal

    async def drive():
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, "note.txt")
            target.write_text("original\n")
            checkpoint = checkpoints.Checkpoint.start("change the note", tmp)
            checkpoint.capture(str(target))
            target.write_text("changed\nsecond\n")
            checkpoint.freeze_diff()

            app = TAMIASApp(
                queue.Queue(), queue.Queue(),
                checkpoint_lookup=lambda cp_id: checkpoint
                if cp_id == checkpoint.id else None,
            )
            async with app.run_test(size=(120, 32)) as pilot:
                app.last_checkpoint_id = checkpoint.id
                await _press(pilot, "escape")
                await _press(pilot, "v")

                assert isinstance(app.screen, DiffModal)
                text = " ".join(str(widget.render())
                                for widget in app.screen.query(Static))
                assert "DIFF" in text
                assert "frozen at turn end" in text
                assert "-original" in text and "+changed" in text
                assert "note.txt" in text and "modified" in text

                await _press(pilot, "escape")
                await _press(pilot, "i")
                app.query_one("#user-input").value = "/diff"
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, DiffModal)
                await _press(pilot, "escape")

    _run(drive())


def test_receipt_records_the_checkpoint_diff_summary():
    receipt = TurnReceipt(number=4, prompt="change the note")
    receipt.note_checkpoint("cp-abcd1234", 1, added=2, removed=1,
                            diff_paths=1)

    text = receipt.to_text()

    assert "diff: +2 -1 across 1 path" in text
    assert "view: V / /diff" in text
    assert "truncated" not in text


def test_turn_end_carries_diff_summary_to_the_receipt():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.start_agent_turn("change the note")
            app.end_agent_turn(
                12, 3, 0.0, 0, "model", "free", {},
                checkpoint_id="cp-abcd1234", checkpoint_files=1,
                checkpoint_added=2, checkpoint_removed=1,
                checkpoint_diff_paths=1, checkpoint_diff_truncated=True)
            await pilot.pause()

            assert app.last_checkpoint_id == "cp-abcd1234"
            receipt = app.last_receipt
            assert receipt is not None
            text = receipt.to_text()
            assert "cp-abcd1234" in text
            assert "+2 -1 across 1 path" in text
            assert "V / /diff" in text
            assert "truncated" in text.lower()

    _run(drive())


def test_receipt_records_the_checkpoint_and_shell_limit():
    receipt = TurnReceipt(number=4, prompt="change the note")
    receipt.note_checkpoint("cp-abcd1234", 2, shell_ran=True)

    text = receipt.to_text()

    assert "CHECKPOINT" in text
    assert "cp-abcd1234" in text
    assert "shell: ran — not captured" in text
    assert "Z / /checkpoint" in text
    assert any("does not capture" in risk for risk in receipt.risks())


def test_plan_parser_reads_steps_and_statuses():
    from tui.plan import parse_plan

    plan = parse_plan(PLAN_TEXT)
    assert plan is not None
    assert plan.total == 3
    assert plan.done == 1
    assert plan.in_progress == 1
    assert plan.pending == 1
    assert plan.steps[1].content == "Add priority field"
    assert plan.steps[1].mark == "[~]"
    assert "1/3 done" in plan.summary_line()
    assert "not signed" in plan.to_text()
    assert "not signed" in " ".join(value for _, value in plan.receipt_rows())


def test_an_unsigned_plan_only_claims_writes_are_held_with_a_gate():
    from tui.plan import parse_plan

    plan = parse_plan(PLAN_TEXT)
    assert plan is not None
    assert "working plan" in plan.to_text()
    assert "writes held" not in plan.to_text()

    plan.gate_active = True
    assert "writes held" in plan.to_text()
    assert "working plan" not in plan.to_text()
    assert "writes are held" in " ".join(
        value for _, value in plan.sections()[2][1])


def test_plan_parser_reads_the_signed_contract_state():
    from tui.plan import parse_plan

    signed = parse_plan(
        "plan updated - 1/3 done\n"
        "[x] Read the todo model\n"
        "[~] Add priority field\n"
        "[ ] Run pytest\n"
        "contract: signed by user\n"
        "Keep exactly one in_progress and move it on as you finish."
    )
    assert signed is not None and signed.signed is True
    assert "signed" in signed.summary_line()
    assert "signed by user" in signed.to_text()
    assert "writes are allowed" in " ".join(
        value for _, value in signed.sections()[2][1])


def test_plan_parser_reads_the_contract_facts():
    from tui.plan import parse_plan

    plan = parse_plan(
        "plan updated - 1/2 done\n"
        "[~] Add priority field\n"
        "[ ] Run pytest\n"
        "files: src/todo.py\n"
        "files: tests/test_todo.py\n"
        "verification: pytest -q\n"
        "risk: the schema is unchanged\n"
        "cost range: 0.0000-0.0200 (hypothetical)\n"
        "contract: signed by user\n"
    )
    assert plan is not None
    assert plan.files == ["src/todo.py", "tests/test_todo.py"]
    assert plan.verification == ["pytest -q"]
    assert plan.risks == ["the schema is unchanged"]
    assert plan.cost_text() == "$0.0000–$0.0200 (hypothetical)"
    assert "2 files" in plan.card_line()
    assert "src/todo.py" in plan.to_text()


def test_plan_parser_refuses_to_invent_a_plan():
    from tui.plan import parse_plan

    assert parse_plan("Error: update_plan failed") is None
    assert parse_plan("plan updated - 0/0 done\nKeep exactly one...") is None
    assert parse_plan("[x] a step without a header") is None


def test_dossier_parses_evidence_limitations_and_unknowns():
    from tui.dossier import TurnDossier

    dossier = TurnDossier()
    assert dossier.add("investigate_target", INVESTIGATION_TEXT) is True

    assert dossier.targets == ["company/work/todoinc/apps/todo"]
    assert [item.label for item in dossier.evidence] == [
        "src/todo.py:4", "src/todo.py:5"]
    assert "static analysis only" in dossier.limitations[0]
    assert dossier.unknowns == ["whether a migration is required"]
    assert "2 evidence lines" in dossier.summary_line()
    assert "1 unknown" in dossier.summary_line()
    assert "src/todo.py:4" in dossier.to_text()


def test_dossier_parses_a_trace_and_a_structure():
    from tui.dossier import TurnDossier

    dossier = TurnDossier()
    assert dossier.add("trace_feature", TRACE_TEXT) is True
    assert dossier.add("analyze_structure", STRUCTURE_TEXT) is True

    assert len(dossier.evidence) == 2
    assert dossier.evidence[0].label.endswith("src/todo.py:9")
    assert any("file src/todo.py" == entry for inv in dossier.investigations
               for entry in inv.entries)
    assert "trace_feature" in dossier.methods
    assert "analyze_structure" in dossier.methods


def test_dossier_ignores_errors_and_deduplicates_evidence():
    from tui.dossier import TurnDossier

    dossier = TurnDossier()
    assert dossier.add(
        "investigate_target",
        "Error investigating company/x: cannot access local variable") is False
    assert dossier.add("read_file", "plain text, not an investigation") is False
    assert dossier.add("investigate_target", INVESTIGATION_TEXT) is True
    assert dossier.add("investigate_target", INVESTIGATION_TEXT) is True
    assert len(dossier.investigations) == 2
    assert len(dossier.evidence) == 2


def test_dossier_keeps_unresolved_questions_from_the_finish_tool():
    from tui.dossier import TurnDossier

    text = """INVESTIGATION FINISHED: session summary
============================================================

Investigated targets:
  - company/work/todoinc/apps/todo

Unresolved questions:
  - does the runtime mutate the same list?
  - is there a database migration?

Comparisons: none
"""
    dossier = TurnDossier()
    assert dossier.add("finish_investigation", text) is True
    assert len(dossier.unknowns) == 2
    assert "does the runtime mutate the same list?" in dossier.unknowns
    assert dossier.add(
        "finish_investigation",
        "INVESTIGATION FINISHED: session summary\n"
        "Investigated targets:\n  - app\n\nUnresolved questions: none\n",
    ) is False


def test_p_opens_the_plan_and_the_receipt_records_it():
    from textual.widgets import Static

    from tui.app import TAMIASApp
    from tui.modals import PlanCard

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.start_agent_turn("add priority")
            app.start_tool("t1", "update_plan", '{"todos": []}')
            app.end_tool("t1", PLAN_TEXT, True, 0.1)
            app.end_agent_turn(12, 3, 0.0, 0, "model", "free", {})
            await pilot.pause()

            assert app.last_plan is not None
            line = " ".join(str(node.render())
                            for node in app.query(".plan-line"))
            assert "1/3 done" in line
            assert "P to open" in line
            assert "PLAN" in app.last_receipt.to_text()
            assert "not signed" in app.last_receipt.to_text()
            assert "did not gate any write" in app.last_receipt.to_text()

            await _press(pilot, "escape")
            await _press(pilot, "p")
            assert isinstance(app.screen, PlanCard)
            text = " ".join(str(widget.render())
                            for widget in app.screen.query(Static))
            assert "PLAN" in text
            assert "Add priority field" in text
            assert "not signed" in text
            await _press(pilot, "escape")

    _run(drive())


def test_slash_dossier_opens_the_evidence_card():
    from textual.widgets import Static

    from tui.app import TAMIASApp
    from tui.modals import DossierCard

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.start_agent_turn("investigate priority")
            app.start_tool("t1", "investigate_target",
                           '{"target": "company/work/todoinc/apps/todo"}')
            app.end_tool("t1", INVESTIGATION_TEXT, True, 0.1)
            app.end_agent_turn(12, 3, 0.0, 0, "model", "free", {})
            await pilot.pause()

            assert app.last_dossier is not None
            line = " ".join(str(node.render())
                            for node in app.query(".dossier-line"))
            assert "2 evidence lines" in line
            assert "D to open" in line
            assert "INVESTIGATION" in app.last_receipt.to_text()
            assert "static; runtime behavior" in app.last_receipt.to_text()
            assert "left 1 unknown;" in app.last_receipt.to_text()

            app.query_one("#user-input").value = "/dossier"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, DossierCard)
            text = " ".join(str(widget.render())
                            for widget in app.screen.query(Static))
            assert "INVESTIGATION DOSSIER" in text
            assert "src/todo.py:4" in text
            assert "whether a migration is required" in text
            await _press(pilot, "escape")

    _run(drive())


def test_work_surfaces_are_honest_when_there_is_nothing_to_show():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            app.show_plan()
            await pilot.pause()
            assert app.last_plan is None
            text = " ".join(str(node.render())
                            for node in app.query(".agent-turn"))
            assert "No plan recorded yet" in text

            app.show_dossier()
            await pilot.pause()
            assert app.last_dossier is None
            text = " ".join(str(node.render())
                            for node in app.query(".agent-turn"))
            assert "No investigation dossier yet" in text

    _run(drive())
