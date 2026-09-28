"""Task board model for the TAMIAS TUI (docs/FRONTEND_REFERENCE.md §6, §9).

The task board is a view concern: it tracks the task the agent is currently
working on and how far along it is. Progress is driven by the same events the
transcript already receives (turn start, tool cards, turn end) rather than by
any new agent-channel message, so the agent core stays untouched.

Pure Python, no Textual, so the lifecycle can be unit-tested.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

# progress is allowed to fill while a turn is in flight, but only a confirmed
# completion may ever show 100% (§6: completion goes through the modal)
IN_FLIGHT_CAP = 95

BAR_FULL = "█"
BAR_EMPTY = "░"

# the demo's first task id follows the reference's PROJ-1457 example
FIRST_TASK_NUMBER = 1457


def progress_bar(percent: int, width: int = 20) -> str:
    percent = max(0, min(100, int(percent)))
    filled = int(round(width * percent / 100))
    return f"{BAR_FULL * filled}{BAR_EMPTY * (width - filled)}"


def is_boundary_violation(result: str) -> bool:
    """A blocked tool result is any path that resolved outside its boundary."""
    if not result:
        return False
    lowered = result.lower()
    return (
        "outside company work area" in lowered
        or "outside the workspace" in lowered
    )


@dataclass
class Task:
    id: str
    project: str
    assignee: str
    title: str
    start: float = field(default_factory=time.monotonic)
    progress: int = 0
    status: str = "active"          # active | complete
    steps: int = 0
    tool_calls: int = 0
    saved_credits: float = 0.0
    pass_rate: float = 57.9
    completed_at: Optional[float] = None

    @property
    def bar(self) -> str:
        return progress_bar(self.progress)

    def elapsed(self) -> float:
        end = self.completed_at if self.completed_at is not None else time.monotonic()
        return max(0.0, end - self.start)

    def elapsed_hms(self) -> str:
        total = int(self.elapsed())
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def board_line(self) -> str:
        mark = "✓" if self.status == "complete" else "•"
        return (f"[{mark}] {self.id} "
                f"{'completed' if self.status == 'complete' else 'in progress'}  "
                f"{self.bar} {self.progress:>3}%")


class TaskBoard:
    """Tracks the current task and the completed ones for this session."""

    def __init__(self, project: str = "acme", assignee: str = "tamias",
                 first_number: int = FIRST_TASK_NUMBER) -> None:
        self.project = project
        self.assignee = assignee
        self._next = first_number
        self.current: Optional[Task] = None
        self.history: list[Task] = []

    # --- lifecycle ---------------------------------------------------------
    def begin(self, title: str) -> Task:
        """Start a new task, closing any in-flight one as superseded."""
        if self.current is not None and self.current.status == "active":
            # an unfinished task that gets replaced is kept in history so the
            # board never silently drops work
            self.history.append(self.current)

        self.current = Task(
            id=f"PROJ-{self._next}",
            project=self.project,
            assignee=self.assignee,
            title=title.strip() or "(untitled task)",
        )
        self._next += 1
        return self.current

    def note_step(self) -> None:
        if self.current is None or self.current.status != "active":
            return
        self.current.steps += 1
        self._bump()

    def note_tool(self) -> None:
        if self.current is None or self.current.status != "active":
            return
        self.current.tool_calls += 1
        self._bump()

    def _bump(self) -> None:
        task = self.current
        # each step/tool nudges progress; capped below 100 until the turn ends
        task.progress = min(IN_FLIGHT_CAP, task.progress + 9)

    def finish_turn(self) -> None:
        """The agent finished its reply: the task is ready to be confirmed."""
        if self.current is not None and self.current.status == "active":
            self.current.progress = 100

    def complete(self, saved_credits: float = 0.0) -> Optional[Task]:
        """Confirm completion. Only ever called from the confirmation modal."""
        if self.current is None:
            return None
        self.current.progress = 100
        self.current.status = "complete"
        self.current.saved_credits = saved_credits
        self.current.completed_at = time.monotonic()
        done = self.current
        self.history.append(done)
        self.current = None
        return done

    # --- presentation ------------------------------------------------------
    def board_lines(self) -> list[str]:
        lines: list[str] = []
        if self.current is not None:
            lines.append(self.current.board_line())
            lines.append(f"    project: {self.current.project}  "
                         f"assignee: {self.current.assignee}  "
                         f"elapsed: {self.current.elapsed_hms()}")
        else:
            lines.append("[ ] no active task")
        if self.history:
            lines.append("")
            for task in self.history[-8:]:
                lines.append(task.board_line())
        return lines
