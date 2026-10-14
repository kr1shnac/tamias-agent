"""Frontend feature tests for the TAMIAS TUI (docs/FRONTEND_REFERENCE.md §5-§9).

Kept apart from test_agent.py, which stubs the rich package for offline core
tests; these exercise the real Textual widgets headlessly.
"""

import asyncio
import queue
import sys

import pytest

from tui.credits import NEUTRAL, CYAN, CreditsLedger
from tui.tasks import TaskBoard, is_boundary_violation, progress_bar


@pytest.fixture(autouse=True)
def _real_rich():
    """test_agent.py stubs the rich package process-wide for offline core tests.

    When both files run in one pytest process those fakes would break Textual's
    rendering. Temporarily drop the stubs so the real package loads, then put
    them back for any later core tests.
    """
    saved = {name: sys.modules.pop(name)
             for name in list(sys.modules)
             if name == "rich" or name.startswith("rich.")}
    try:
        yield
    finally:
        sys.modules.update(saved)

# ------------------------------------------------------- spend / USD (§5, D7)


def test_ledger_is_neutral_and_empty_until_the_first_turn():
    ledger = CreditsLedger()
    assert not ledger.has_data
    assert ledger.color() == NEUTRAL
    assert ledger.readout() == "$0.0000 · no usage yet"
    assert not ledger.fully_priced


def test_ledger_records_provider_billed_usd_not_a_token_formula():
    ledger = CreditsLedger()
    ledger.record(prompt_tokens=12_000, completion_tokens=800, cost_usd=0.0123)
    # the spend is exactly what the provider said, whatever the token counts
    assert ledger.spent_usd == 0.0123
    assert ledger.readout() == "$0.0123"
    assert ledger.color() == CYAN
    assert ledger.fully_priced


def test_a_zero_cost_is_a_price_not_a_missing_one():
    ledger = CreditsLedger()
    ledger.record(prompt_tokens=10, completion_tokens=2, cost_usd=0.0)
    assert ledger.spent_usd == 0.0
    assert ledger.fully_priced
    assert "unpriced" not in ledger.readout()


def test_an_unpriced_step_flags_the_total_as_partial():
    ledger = CreditsLedger()
    ledger.record(prompt_tokens=10, completion_tokens=2, cost_usd=0.0042)
    ledger.record(prompt_tokens=10, completion_tokens=2, cost_usd=None,
                  unpriced_steps=1)
    assert ledger.spent_usd == 0.0042
    assert not ledger.fully_priced
    assert ledger.readout() == "$0.0042 + 1 unpriced"
    assert "1 steps unpriced" in " ".join(
        v for _, v in ledger.dashboard_lines())


def test_a_malformed_cost_is_treated_as_unpriced():
    for bad in (True, "0.01", -0.01, float("nan"), float("inf"), object()):
        ledger = CreditsLedger()
        ledger.record(prompt_tokens=1, completion_tokens=1, cost_usd=bad)
        assert ledger.spent_usd == 0.0, bad
        assert not ledger.fully_priced, bad
        assert ledger.unpriced_steps == 1, bad


def test_ledger_accumulates_and_snapshots_a_copy():
    ledger = CreditsLedger()
    ledger.record(1000, 100, cost_usd=0.001)
    ledger.record(1000, 100, cost_usd=0.002)
    assert ledger.turns == 2
    assert ledger.spent_usd == pytest.approx(0.003)
    copy = ledger.snapshot()
    assert copy.turns == 2 and copy.spent_usd == ledger.spent_usd
    copy.record(0, 0, cost_usd=99.0)
    assert ledger.spent_usd == pytest.approx(0.003)   # snapshot is a copy


# D16: the UI may only show metrics it measured.  This test renders the
# dashboard rows against a ledger with known figures and fails on any literal
# the figures do not produce.
def test_dashboard_rows_are_all_derived_from_recorded_usage():
    ledger = CreditsLedger()
    ledger.record(prompt_tokens=1200, completion_tokens=340, cost_usd=0.0789)

    text = " ".join(f"{label} {value}"
                    for label, value in ledger.dashboard_lines())

    # every value is the recorded figure, rendered
    assert "$0.0789" in text
    assert "1,540" in text          # tokens = 1200 + 340
    assert "1,200" in text
    assert "340" in text
    assert "provider-billed USD" in text

    # and no invented metric can sneak back in
    for fabricated in ("Codex", "codex", "57.9", "off-task", "async",
                       "savings", "SAVINGS", "80%", "PASS RATE"):
        assert fabricated not in text, fabricated


def test_dashboard_and_readout_carry_no_baseline_anywhere():
    ledger = CreditsLedger()
    ledger.record(10, 2, cost_usd=0.001)
    blob = ledger.readout() + " " + " ".join(
        f"{k} {v}" for k, v in ledger.dashboard_lines())
    lowered = blob.lower()
    assert "codex" not in lowered
    assert "baseline" not in lowered
    assert "saved" not in lowered
    assert "credits" not in lowered


# ----------------------------------------------------------------- tasks (§6)


def test_progress_bar_shape():
    assert progress_bar(0, 10) == "░" * 10
    assert progress_bar(100, 10) == "█" * 10
    assert progress_bar(50, 10) == "█" * 5 + "░" * 5


def test_boundary_detection():
    assert is_boundary_violation(
        "Error: '/etc/passwd' is outside company work area (company_id=acme)")
    assert is_boundary_violation("Error: '/etc/passwd' is outside the workspace")
    assert not is_boundary_violation("success")
    assert not is_boundary_violation("")


def test_taskboard_lifecycle():
    board = TaskBoard(project="acme", assignee="alex")
    task = board.begin("build the thing")
    assert task.id.startswith("PROJ-")

    board.note_tool()
    assert task.progress > 0

    for _ in range(50):  # in-flight progress must never reach 100
        board.note_tool()
    assert task.progress == 95

    board.finish_turn()
    assert task.progress == 100

    done = board.complete(spent_usd=12.5)
    assert done.status == "complete"
    assert done.spent_usd == 12.5
    assert board.current is None
    assert done in board.history


def test_task_not_completed_without_complete():
    board = TaskBoard()
    board.begin("x")
    board.finish_turn()
    assert board.current.status == "active"
    assert board.history == []


# ---------------------------------------------------- task board honesty (§10)


def test_board_invents_no_project_or_assignee():
    # with nothing supplied, the board says so -- it must not fall back to a
    # fake company name the way it used to ("acme" / "tamias")
    board = TaskBoard()
    task = board.begin("do the thing")
    assert task.project == "unassigned"
    assert task.assignee == "unassigned"


def test_board_uses_the_supplied_task_id_for_the_first_task_only():
    board = TaskBoard(project="acme", assignee="alex", task_id="TASK-9")

    first = board.begin("first")
    assert first.id == "TASK-9"             # the id the run was given

    board.complete()
    second = board.begin("second")
    assert second.id != "TASK-9"            # later work auto-numbers
    assert second.id == "PROJ-1457"


def test_app_wires_the_cli_identity_into_the_board():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue(), company_id="acme",
                        task_id="PROJ-1457", assignee="alex")
        async with app.run_test(size=(120, 32)):
            assert app.board.project == "acme"
            assert app.board.assignee == "alex"
            app.board.begin("ship it")
            assert app.board.current.id == "PROJ-1457"
            # and the panel renders both, distinctly -- no echoed company id
            app.refresh_task_board()
            text = str(app.query_one("#task-board").render())
            assert "acme" in text and "alex" in text

    _run(drive())


# ----------------------------------------------------------- headless UI (app)


def _run(coro):
    return asyncio.run(coro)


def test_credits_header_is_always_visible_and_f3_opens_dashboard():
    from tui.app import TAMIASApp
    from tui.modals import CreditsDashboard

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 32)) as pilot:
            header = str(app.query_one("#credits-readout").render())
            assert "$0.0000" in header
            await pilot.press("f3")
            assert isinstance(app.screen, CreditsDashboard)

    _run(drive())


def test_f3_dashboard_renders_only_measured_figures():
    # D16: render the real screen against a ledger with known figures and fail
    # on any literal metric the figures do not produce.
    from textual.widgets import Static

    from tui.app import TAMIASApp
    from tui.credits import CreditsLedger
    from tui.modals import CreditsDashboard

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 40)) as pilot:
            ledger = CreditsLedger()
            ledger.record(prompt_tokens=1200, completion_tokens=340,
                          cost_usd=0.0789)
            app.push_screen(CreditsDashboard(ledger))
            await pilot.pause()

            text = " ".join(str(widget.render())
                            for widget in app.screen.query(Static))

            # the recorded figures are what is shown
            assert "$0.0789" in text
            assert "1,540" in text            # 1200 + 340 tokens
            assert "provider-billed USD" in text

            # and none of the retired placeholder metrics can come back
            for fabricated in ("Codex", "57.9", "off-task", "async", "80%",
                               "PASS RATE", "MODEL USAGE", "savings",
                               "remaining", "baseline"):
                assert fabricated not in text, fabricated

    _run(drive())


def test_nav_mode_makes_plain_t_toggle_the_task_board():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 32)) as pilot:
            board = app.query_one("#task-board")
            assert not board.display
            await pilot.press("escape")   # leave the composer -> nav mode
            await pilot.press("t")
            assert board.display
            await pilot.press("t")
            assert not board.display

    _run(drive())


def test_completion_requires_the_confirmation_modal():
    from tui.app import TAMIASApp
    from tui.modals import ConfirmModal

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 32)) as pilot:
            app.board.begin("ship it")
            app.action_complete_task()
            await pilot.pause()
            assert isinstance(app.screen, ConfirmModal)

            await pilot.press("n")            # decline -> task continues
            await pilot.pause()
            assert app.board.current is not None

            app.action_complete_task()
            await pilot.pause()
            await pilot.press("y")            # confirm -> task completes
            await pilot.pause()
            assert app.board.current is None
            assert app.board.history[-1].status == "complete"

    _run(drive())


def test_task_board_reports_the_boundary_status():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue(), company_id="acme")
        async with app.run_test(size=(120, 32)) as pilot:
            board = app.query_one("#task-board")
            assert board.boundary_state == "enforced"
            assert "boundary: enforced" in str(board.render())
            assert "company/work/acme/" in str(board.render())

            # a violation is reflected in the panel, not only in the modal
            app.start_agent_turn("read /etc/passwd")
            app.start_tool("t1", "read_file", '{"file_path": "/etc/passwd"}')
            app.end_tool(
                "t1",
                "Error: '/etc/passwd' is outside company work area "
                "(company_id=acme)",
                True, 0.1,
            )
            await pilot.pause()
            assert board.boundary_state == "violation"

    _run(drive())


def test_boundary_violation_opens_the_blocked_modal():
    from tui.app import TAMIASApp
    from tui.modals import BoundaryModal

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue(), company_id="acme")
        async with app.run_test(size=(120, 32)) as pilot:
            app.start_agent_turn("read /etc/passwd")
            app.start_tool("t1", "read_file", '{"file_path": "/etc/passwd"}')
            app.end_tool(
                "t1",
                "Error: '/etc/passwd' is outside company work area "
                "(company_id=acme)",
                True, 0.1,
            )
            await pilot.pause()
            assert isinstance(app.screen, BoundaryModal)
            assert app.screen._attempted == "/etc/passwd"

    _run(drive())


def test_m_cycles_through_the_model_tiers():
    from tui.app import MODEL_TIERS, TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 32)):
            app.action_cycle_model()
            assert app.current_model == MODEL_TIERS[1][1]
            app.action_cycle_model()
            assert app.current_model == MODEL_TIERS[2][1]
            app.action_cycle_model()
            assert app.current_model == MODEL_TIERS[0][1]

    _run(drive())


# ----------------------------------------------------- landing & palette (§4)

def test_landing_shows_the_wordmark_then_hands_over_to_the_chat():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 34)) as pilot:
            await pilot.pause()
            await pilot.pause()
            assert app.screen.has_class("landing")
            assert len(app.query("#hero")) == 1

            app.query_one("#user-input").value = "read hello.py"
            await pilot.press("enter")
            await pilot.pause()
            assert not app.screen.has_class("landing")
            assert len(app.query("#hero")) == 0
            assert app.ui_queue.get_nowait() == "read hello.py"

    _run(drive())


def test_slash_palette_lists_commands_completes_with_tab_and_runs():
    from tui.app import TAMIASApp
    from tui.slash import SlashMenu

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 34)) as pilot:
            await pilot.pause()
            menu = app.query_one(SlashMenu)
            assert not menu.open

            await pilot.press("/")
            await pilot.pause()
            assert menu.open and menu.mode == "commands"
            assert menu.rows[menu.highlight][0] == "/model"

            await pilot.press("down")
            await pilot.pause()
            assert menu.rows[menu.highlight][0] == "/task"

            await pilot.press("tab")                 # complete, do not run
            await pilot.pause()
            assert app.query_one("#user-input").value == "/task"
            assert not app.query_one("#task-board").display

            await pilot.press("enter")               # now run the command
            await pilot.pause()
            assert not menu.open
            assert app.query_one("#task-board").display

    _run(drive())


def test_slash_palette_offers_matching_models_after_model_command():
    from tui.app import TAMIASApp
    from tui.slash import SlashMenu

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 34)) as pilot:
            await pilot.pause()
            app.query_one("#user-input").value = "/model nemotron-3-ultra"
            await pilot.pause()
            menu = app.query_one(SlashMenu)
            assert menu.open and menu.mode == "models"
            assert len(menu.rows) == 1
            assert "ultra" in menu.rows[0][0]

            await pilot.press("enter")
            await pilot.pause()
            assert app.current_model.endswith("nemotron-3-ultra-550b-a55b:free")
            assert app.ui_queue.get_nowait() == f"/model {app.current_model}"

    _run(drive())


def test_unknown_slash_command_is_reported_locally():
    from tui.app import TAMIASApp

    async def drive():
        app = TAMIASApp(queue.Queue(), queue.Queue())
        async with app.run_test(size=(120, 34)) as pilot:
            await pilot.pause()
            app.query_one("#user-input").value = "/nope"
            await pilot.press("enter")
            await pilot.pause()
            assert app.ui_queue.empty()               # never reaches the agent
            shown = " ".join(str(node.render())
                             for node in app.query(".agent-turn"))
            assert "unknown command" in shown

    _run(drive())


def test_responsive_header_drops_wide_chips_on_small_terminals():
    from tui.app import TAMIASApp

    async def drive():
        for width, narrow, tiny in ((120, False, False), (90, True, False),
                                    (60, True, True)):
            app = TAMIASApp(queue.Queue(), queue.Queue())
            async with app.run_test(size=(width, 30)) as pilot:
                await pilot.pause()
                assert app.screen.has_class("narrow") is narrow, width
                assert app.screen.has_class("tiny") is tiny, width
                assert app.query_one("#model-display").display is not narrow
                # the credits readout is the one readout that never hides
                assert app.query_one("#credits-readout").display

    _run(drive())


# ------------------------------------------------------- launch routing (agent)

def test_main_defaults_to_the_tui_on_an_interactive_terminal(monkeypatch):
    import agent
    import tui.bridge as bridge

    called = {}
    monkeypatch.setattr(agent, "is_interactive_terminal", lambda: True)
    monkeypatch.setattr(
        bridge, "run_tui",
        lambda max_steps=25, company_id=None, task_id=None, assignee=None: (
            called.update(max_steps=max_steps, company_id=company_id,
                          task_id=task_id, assignee=assignee) or 0),
    )

    assert agent.main([]) == 0
    assert called == {"max_steps": 25, "company_id": None,
                      "task_id": None, "assignee": None}


def test_main_plain_flag_keeps_the_text_repl(monkeypatch):
    import agent
    import tui.bridge as bridge

    opened = {}
    monkeypatch.setattr(agent, "is_interactive_terminal", lambda: True)
    monkeypatch.setattr(bridge, "run_tui",
                        lambda **kwargs: opened.setdefault("tui", True) or 0)
    monkeypatch.setattr(agent, "interactive_loop", lambda max_steps: 0)

    assert agent.main(["--plain"]) == 0
    assert "tui" not in opened
