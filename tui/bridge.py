"""Bridge between the TAMIAS agent core and the Textual UI.

The TUI (``tui/app.py``) is a pure view: it reads user turns from ``ui_queue``
and renders ``tui.events`` dataclasses coming back on ``agent_queue``. This
module is the missing producer. It runs the same agent core the CLI uses
(``agent.py``) and translates that core's ``on_event`` milestones into the
dataclasses the view already knows how to draw.

Run it with::

    python -m tui.bridge                 # standalone
    python agent.py --tui                # same thing, via the CLI flag
    python agent.py --tui --company-id acme

No Textual import happens at module load, so this module stays cheap to import
(and unit-testable) even where Textual is not installed.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import uuid

import agent as core
from tui.events import (
    MessageDelta,
    StatusUpdate,
    ToolAsk,
    ToolEnd,
    ToolStart,
    TurnEnd,
    TurnStart,
)

# commands the view may forward that the bridge answers itself, never the model
COMMANDS = ("/clear", "/compact", "/help", "/quit")


class AskGate:
    """A one-at-a-time yes/no bridge from the agent worker to the view.

    The worker thread blocks in :meth:`ask` until the view calls
    :meth:`resolve` (or the timeout fires). With no answer the result is
    ``False``: an ask can never wedge a run open, it only ever fails closed.
    """

    TIMEOUT_SEC = 300.0

    def __init__(self, agent_queue):
        self.agent_queue = agent_queue
        self._event = threading.Event()
        self._answer = False

    def ask(self, tool_name, args, reason):
        """Called from the agent worker thread; blocks for the view's answer."""
        self._answer = False
        self._event.clear()
        self.agent_queue.put(ToolAsk(
            tool_name=tool_name,
            arguments=json.dumps(args, default=str),
            reason=reason,
        ))

        answered = self._event.wait(timeout=self.TIMEOUT_SEC)
        return bool(answered and self._answer)

    def resolve(self, allowed):
        """Called from the view thread with the human's answer."""
        self._answer = bool(allowed)
        self._event.set()


def make_translator(agent_queue, session_id):
    """Return an ``on_event`` callback that pushes ``tui.events`` onto a queue.

    Kept free of Textual and of any live model so it can be tested on its own:
    feed it ``(name, **fields)`` and read the dataclasses back off the queue.
    """

    def on_event(name, **fields):
        if name == "turn_start":
            agent_queue.put(TurnStart(
                user_prompt=fields.get("user_prompt", ""),
                session_id=session_id,
            ))
        elif name == "status":
            agent_queue.put(StatusUpdate(
                message=fields.get("message", ""),
                is_busy=bool(fields.get("is_busy", False)),
            ))
        elif name == "message":
            agent_queue.put(MessageDelta(
                content=fields.get("content", ""),
                model=fields.get("model", ""),
            ))
        elif name == "tool_start":
            agent_queue.put(ToolStart(
                tool_call_id=fields.get("tool_call_id", ""),
                tool_name=fields.get("tool_name", ""),
                arguments=fields.get("arguments") or "",
            ))
        elif name == "tool_end":
            agent_queue.put(ToolEnd(
                tool_call_id=fields.get("tool_call_id", ""),
                result=fields.get("result") or "",
                success=bool(fields.get("success", True)),
                duration_sec=float(fields.get("duration_sec", 0.0)),
            ))
        elif name == "turn_end":
            raw_cost = fields.get("cost_usd")
            agent_queue.put(TurnEnd(
                prompt_tokens=int(fields.get("prompt_tokens", 0) or 0),
                completion_tokens=int(fields.get("completion_tokens", 0) or 0),
                total_duration_sec=float(fields.get("total_duration_sec", 0.0)),
                cost_usd=None if raw_cost is None else float(raw_cost),
                unpriced_steps=int(fields.get("unpriced_steps", 0) or 0),
            ))

    return on_event


#one devnull handle kept for the process lifetime; the console keeps writing to
#it, so it must not be closed after the swap
_NULL_STREAM = open(os.devnull, "w")  # noqa: SIM115


def _silence_console():
    """Point the CLI's Rich console at nothing so it cannot corrupt the TUI.

    The agent core prints through a module-level ``console``; swapping it here
    leaves ``agent.py`` untouched and keeps the screen owned by Textual.
    """
    from rich.console import Console
    core.console = Console(file=_NULL_STREAM, force_terminal=False)


def agent_worker(ui_queue, agent_queue, max_steps=25, company_id=None,
                 ask_gate=None):
    """Consume user turns from ``ui_queue`` and drive the agent core.

    Emits ``tui.events`` onto ``agent_queue``. Runs until it sees ``None``
    (a shutdown sentinel) or a ``/quit``.
    """
    if company_id:
        core.COMPANY_ID = company_id
    _silence_console()

    # ask-gated policy calls block on the gate; with no gate the core keeps its
    # own default (no one to ask), which denies fail-closed
    if ask_gate is not None:
        core.ASK_HANDLER = ask_gate.ask

    session_id = uuid.uuid4().hex[:12]
    emit = make_translator(agent_queue, session_id)

    agent_queue.put({"type": "init", "model": core.MODEL})

    while True:
        item = ui_queue.get()

        if item is None:
            break

        text = str(item).strip()
        if not text:
            continue

        if text == "/quit":
            break

        if text == "/clear":
            core.history.clear()
            agent_queue.put({"type": "clear"})
            continue

        if text == "/compact":
            if len(core.history) >= 2:
                core.compact_history(core.client, core.new_stats())
            continue

        if text == "/help":
            agent_queue.put(StatusUpdate(
                message="commands: /model /clear /compact /help /quit",
                is_busy=False,
            ))
            continue

        if text.startswith("/model"):
            parts = text.split(None, 1)

            if len(parts) == 2 and parts[1].strip():
                requested = parts[1].strip()

                if not core.model_allowed(requested):
                    agent_queue.put(StatusUpdate(
                        message=(f"Error: model '{requested}' is outside this "
                                 "policy's model allowlist"),
                        is_busy=False,
                    ))
                    continue

                core.MODEL = requested
                agent_queue.put({"type": "model_update", "model": core.MODEL})
            continue

        try:
            core.run_turn(text, max_steps, core.new_stats(), on_event=emit)
        except Exception as error:  # one bad turn must not kill the UI thread
            agent_queue.put(StatusUpdate(
                message=f"Error: {error}", is_busy=False
            ))
            agent_queue.put(TurnEnd(
                prompt_tokens=0, completion_tokens=0, total_duration_sec=0.0
            ))


def run_tui(max_steps=25, company_id=None, task_id=None, assignee=None):
    """Start the agent worker on a thread, then run the Textual app."""
    from tui.app import TAMIASApp  # imported late: Textual is only needed here

    ui_queue = queue.Queue()
    agent_queue = queue.Queue()
    ask_gate = AskGate(agent_queue)

    worker = threading.Thread(
        target=agent_worker,
        args=(ui_queue, agent_queue, max_steps, company_id, ask_gate),
        daemon=True,
    )
    worker.start()

    try:
        TAMIASApp(ui_queue, agent_queue, company_id=company_id,
                  task_id=task_id, assignee=assignee,
                  ask_gate=ask_gate).run()
    finally:
        ui_queue.put(None)          # stop the worker once the view is gone
        worker.join(timeout=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(run_tui())
