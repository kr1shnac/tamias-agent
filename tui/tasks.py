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
    """A blocked result is any path/move that resolved outside its boundary.

    Covers the filesystem fence ("outside the company work area"), the policy
    gate's own refusals ("policy deny - ...") and a use-case scope refusal
    ("Error: boundary - ..."), so every kind of block surfaces as one thing.
    """
    if not result:
        return False
    lowered = result.lower()
    return (
        "outside company work area" in lowered
        or "outside the workspace" in lowered
        or "policy deny" in lowered
        or lowered.startswith("error: boundary")
    )


@dataclass
class Task:
    id: str
    project: str
    assignee: str
    title: str
    start: float = field(default_factory=time.monotonic)
    progress: int = 0
    status: str = "active"          # active | complete | blocked
    steps: int = 0
    tool_calls: int = 0
    spent_usd: float = 0.0          # provider-billed USD over the task
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
        if self.status == "complete":
            return (f"[✓] {self.id} completed  "
                    f"{self.bar} 100%")
        if self.status == "blocked":
            return (f"[✗] {self.id} blocked  "
                    f"(not completed · {self.steps} steps · "
                    f"{self.tool_calls} tools)")
        if self.status == "ready":
            return (f"[◆] {self.id} ready to review  "
                    f"· {self.steps} steps · {self.tool_calls} tools")
        # A turn has no known denominator while it is running, so there is no
        # honest percentage to show. Counts are facts; a bar would be theatre.
        return (f"[•] {self.id} working  "
                f"· {self.steps} steps · {self.tool_calls} tools")


class TaskBoard:
    """Tracks the current task and the completed ones for this session."""

    def __init__(self, project: str = "unassigned",
                 assignee: str = "unassigned",
                 first_number: int = FIRST_TASK_NUMBER,
                 task_id: Optional[str] = None) -> None:
        self.project = project
        self.assignee = assignee
        self._next = first_number
        # --task-id names the first task explicitly; later tasks auto-number,
        # so the board never invents an id when one was supplied
        self._task_id = task_id
        self.current: Optional[Task] = None
        self.history: list[Task] = []

    # --- lifecycle ---------------------------------------------------------
    def begin(self, title: str) -> Task:
        """Start a new task, closing any in-flight one as superseded."""
        if self.current is not None:
            # an unfinished task that gets replaced is kept in history so the
            # board never silently drops work (a blocked one is kept too)
            self.history.append(self.current)

        if self._task_id:
            task_id = self._task_id
            self._task_id = None            # only the first task is named
        else:
            task_id = f"PROJ-{self._next}"
            self._next += 1

        self.current = Task(
            id=task_id,
            project=self.project,
            assignee=self.assignee,
            title=title.strip() or "(untitled task)",
        )
        return self.current

    def note_step(self) -> None:
        if self.current is None or self.current.status not in ("active", "ready"):
            return
        self.current.steps += 1

    def note_tool(self) -> None:
        if self.current is None or self.current.status not in ("active", "ready"):
            return
        self.current.tool_calls += 1

    def finish_turn(self) -> None:
        """The agent finished its reply: the task is ready for human review.

        It is not complete. Only :meth:`complete` (the confirmation modal) may
        set 100%, because a reply is not evidence that the work was accepted.
        """
        if self.current is not None and self.current.status == "active":
            self.current.status = "ready"

    def block(self) -> None:
        """The turn hit the boundary: it is neither completed nor progressing.

        A blocked task must never read as 100%/"ready" - the fix for a turn
        that was stopped by the fence but still looked finished.
        """
        if self.current is not None and self.current.status == "active":
            self.current.status = "blocked"

    def complete(self, spent_usd: float = 0.0) -> Optional[Task]:
        """Confirm completion. Only ever called from the confirmation modal."""
        if self.current is None:
            return None
        self.current.progress = 100
        self.current.status = "complete"
        self.current.spent_usd = spent_usd
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
