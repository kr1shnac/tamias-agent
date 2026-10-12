"""Frontend feature tests for the TAMIAS TUI (docs/FRONTEND_REFERENCE.md §5-§9).

Kept apart from test_agent.py, which stubs the rich package for offline core
tests; these exercise the real Textual widgets headlessly.
"""

import asyncio
import queue
import sys

import pytest

from tui.credits import (
    AMBER, GREEN, NEUTRAL, RED, CreditsLedger, savings_color,
)
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

# --------------------------------------------------------------- credits (§5)


def test_savings_color_thresholds():
    assert savings_color(100) == GREEN
    assert savings_color(39) == GREEN
    assert savings_color(38.9) == AMBER
    assert savings_color(20) == AMBER
    assert savings_color(19.9) == RED
    assert savings_color(0) == RED


def test_ledger_is_neutral_until_the_first_turn():
    ledger = CreditsLedger()
    assert not ledger.has_data
    assert ledger.color() == NEUTRAL
    assert ledger.readout() == "SCR 0/150 (0% saved)"


def test_long_agentic_turn_lands_green():
    ledger = CreditsLedger()
    ledger.record(12000, 800)
    assert ledger.savings_pct >= 39
    assert ledger.color() == GREEN


def test_short_exchange_lands_amber():
    ledger = CreditsLedger()
    ledger.record(500, 50)
    assert 20 <= ledger.savings_pct < 39
    assert ledger.color() == AMBER


def test_tiny_turn_can_warn_red():
    ledger = CreditsLedger()
    ledger.record(0, 0)
    assert ledger.savings_pct < 20
    assert ledger.color() == RED


def test_red_readout_carries_the_warning_suffix():
    ledger = CreditsLedger()
    ledger.record(0, 0)
    assert ledger.color() == RED
    assert ledger.readout().endswith("WARNING: low savings")


def test_green_readout_stays_terse():
    ledger = CreditsLedger()
    ledger.record(12000, 800)
    assert ledger.color() == GREEN
    assert "WARNING" not in ledger.readout()


def test_ledger_accumulates_and_tracks_remaining():
    ledger = CreditsLedger()
    ledger.record(1000, 100)
    ledger.record(1000, 100)
    assert ledger.turns == 2
    assert ledger.remaining == 150 - ledger.spent
    assert ledger.snapshot().turns == 2  # snapshot is a copy


def test_dashboard_covers_the_required_signals():
    ledger = CreditsLedger()
    ledger.record(6000, 600)
    text = " ".join(f"{k} {v}" for k, v in ledger.dashboard_lines())
    for needle in ("BALANCE", "SAVINGS", "TREND", "PASS RATE", "MODEL",
                   "BOUNDARY"):
        assert needle in text


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
    board = TaskBoard(project="acme", assignee="acme")
    task = board.begin("build the thing")
    assert task.id.startswith("PROJ-")

    board.note_tool()
    assert task.progress > 0

    for _ in range(50):  # in-flight progress must never reach 100
        board.note_tool()
    assert task.progress == 95

    board.finish_turn()
    assert task.progress == 100

    done = board.complete(saved_credits=12)
    assert done.status == "complete"
    assert done.saved_credits == 12
    assert board.current is None
    assert done in board.history


def test_task_not_completed_without_complete():
    board = TaskBoard()
    board.begin("x")
    board.finish_turn()
    assert board.current.status == "active"
    assert board.history == []


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
            assert "SCR 0/150" in header
            await pilot.press("f3")
            assert isinstance(app.screen, CreditsDashboard)

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
        lambda max_steps=25, company_id=None: (
            called.update(max_steps=max_steps, company_id=company_id) or 0),
    )

    assert agent.main([]) == 0
    assert called == {"max_steps": 25, "company_id": None}


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
