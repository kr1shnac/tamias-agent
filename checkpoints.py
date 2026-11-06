"""File checkpoints for Time Travel v1.

A checkpoint records the bytes of every file a turn is about to create or
overwrite. It is deliberately **file-only**: a shell command marks the
checkpoint incomplete instead of pretending its changes were captured. Restore
is explicit, path-scoped, and refuses to follow a symlink outside the
workspace. Conversation state and durable storage are not part of v1.

The module is data + file mechanics only. The agent decides which paths are
safe to capture; the TUI decides when a human has confirmed a restore.
"""

from __future__ import annotations

import difflib
import os
import stat
import tempfile
import time
import uuid
from dataclasses import dataclass, field

MAX_FILE_BYTES = 2_000_000
MAX_CHECKPOINT_BYTES = 10_000_000

# Inline diffs are evidence, not a replacement for the file. Keep them bounded
# so a generated 2 MB file cannot freeze the TUI or flood the receipt.
MAX_DIFF_BYTES = 256_000
MAX_DIFF_LINES = 600
MAX_DIFF_TOTAL_LINES = 1_200


@dataclass
class FileSnapshot:
    """One path as it looked before the turn touched it."""

    path: str                  # resolved absolute path
    display: str               # workspace-relative path for the UI
    existed: bool
    is_dir: bool = False
    content: bytes | None = None
    mode: int | None = None
    error: str = ""

    @property
    def restorable(self) -> bool:
        return not self.error

    @property
    def kind(self) -> str:
        if self.error:
            return "unavailable"
        if self.is_dir:
            return "directory" if self.existed else "created directory"
        return "modified" if self.existed else "created"

    def preview_row(self) -> tuple[str, str]:
        size = "" if self.content is None else f" · {len(self.content):,} B"
        detail = f"{self.kind}{size}"
        if self.error:
            detail += f" · {self.error}"
        return (self.display, detail)


@dataclass
class FileDiff:
    """One tracked path's textual change, or the reason it cannot be shown."""

    display: str
    kind: str
    added: int = 0
    removed: int = 0
    text: str = ""
    note: str = ""
    truncated: bool = False

    @property
    def changed(self) -> bool:
        return self.kind in ("modified", "created", "deleted", "absent")

    def header(self) -> str:
        bits = [self.display, self.kind, f"+{self.added} -{self.removed}"]
        if self.truncated:
            bits.append("truncated")
        return " · ".join(bits)


@dataclass
class RestoreResult:
    """What a restore actually did; never a claim that everything worked."""

    restored: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed

    def summary(self) -> str:
        parts = []
        if self.restored:
            parts.append(f"{len(self.restored)} restored")
        if self.removed:
            parts.append(f"{len(self.removed)} removed")
        if self.failed:
            parts.append(f"{len(self.failed)} failed")
        return ", ".join(parts) or "nothing changed"


@dataclass
class Checkpoint:
    """The pre-turn state of every file the turn touched."""

    id: str
    prompt: str
    workspace: str
    created_at: float = field(default_factory=time.time)
    files: dict[str, FileSnapshot] = field(default_factory=dict)
    shell_ran: bool = False
    restored_at: float | None = None
    total_bytes: int = 0
    frozen_diffs: list[FileDiff] = field(default_factory=list, repr=False)
    diff_frozen_at: float | None = None
    diff_truncated: bool = False

    @classmethod
    def start(cls, prompt: str, workspace: str) -> Checkpoint:
        return cls(
            id="cp-" + uuid.uuid4().hex[:8],
            prompt=prompt,
            workspace=os.path.realpath(workspace),
        )

    # ------------------------------------------------------------- capture
    def capture(self, path: str, is_dir: bool = False) -> FileSnapshot | None:
        """Record ``path`` once, before the turn changes it.

        ``is_dir`` tells the checkpoint that a not-yet-existing path is about to
        be created as a directory (``create_directory``); otherwise a missing
        path is treated as a file. Returns ``None`` for a path outside the
        checkpoint workspace. The agent already resolves paths through its own
        fence; this is the second check.
        """
        resolved = os.path.realpath(path)
        if resolved in self.files:
            return self.files[resolved]
        if not self._inside(resolved):
            return None

        display = os.path.relpath(resolved, self.workspace)
        if os.path.islink(resolved):
            snapshot = FileSnapshot(
                path=resolved, display=display, existed=os.path.exists(resolved),
                error="symlink not snapshotted",
            )
            self.files[resolved] = snapshot
            return snapshot

        existed = os.path.exists(resolved)
        if not existed:
            snapshot = FileSnapshot(path=resolved, display=display,
                                    existed=False, is_dir=bool(is_dir))
        elif os.path.isdir(resolved):
            snapshot = FileSnapshot(path=resolved, display=display,
                                    existed=True, is_dir=True)
        else:
            snapshot = self._read_file(resolved, display)

        self.files[resolved] = snapshot
        return snapshot

    def _read_file(self, path: str, display: str) -> FileSnapshot:
        try:
            size = os.path.getsize(path)
            if (size > MAX_FILE_BYTES
                    or self.total_bytes + size > MAX_CHECKPOINT_BYTES):
                return FileSnapshot(
                    path=path, display=display, existed=True,
                    error="file too large to snapshot",
                )
            with open(path, "rb") as handle:
                content = handle.read()
            self.total_bytes += len(content)
            return FileSnapshot(
                path=path, display=display, existed=True,
                content=content,
                mode=stat.S_IMODE(os.stat(path).st_mode),
            )
        except OSError as error:
            return FileSnapshot(
                path=path, display=display, existed=True,
                error=f"could not read: {error}",
            )

    # ------------------------------------------------------------- preview
    def preview_rows(self) -> list[tuple[str, str]]:
        return [snapshot.preview_row()
                for snapshot in sorted(self.files.values(),
                                       key=lambda item: item.display)]

    def summary(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "files": len(self.files),
            "shell_ran": self.shell_ran,
            "restored_at": self.restored_at,
        }

    # --------------------------------------------------------------- diff
    def diff_files(self) -> list[FileDiff]:
        """The turn's textual changes, or the frozen snapshot of them.

        A checkpoint is frozen by ``freeze_diff`` at the end of the turn, so a
        later edit cannot rewrite the evidence the receipt pointed at. Before
        that point this reads the current files.
        """
        if self.diff_frozen_at is not None:
            return list(self.frozen_diffs)
        return self._current_diffs()

    def freeze_diff(self) -> list[FileDiff]:
        """Freeze the diff at turn end; later edits do not rewrite it."""
        if self.diff_frozen_at is not None:
            return list(self.frozen_diffs)
        self.frozen_diffs = self._current_diffs()
        self.diff_truncated = any(item.truncated
                                  for item in self.frozen_diffs)
        self.diff_frozen_at = time.time()
        return list(self.frozen_diffs)

    def diff_summary(self) -> dict:
        diffs = self.diff_files()
        return {
            "paths": len(diffs),
            "added": sum(item.added for item in diffs),
            "removed": sum(item.removed for item in diffs),
            "truncated": any(item.truncated for item in diffs),
            "frozen": self.diff_frozen_at is not None,
        }

    def diff_text(self) -> str:
        """A plain-text review of every tracked change, safe to paste."""
        diffs = self.diff_files()
        summary = self.diff_summary()
        lines = [
            f"TAMIAS DIFF · checkpoint {self.id}",
            f"prompt: {self.prompt or '(not recorded)'}",
            f"paths: {summary['paths']} · +{summary['added']} "
            f"-{summary['removed']}"
            + (" · truncated" if summary["truncated"] else ""),
            "",
        ]
        for item in diffs:
            lines.append(item.header())
            if item.note:
                lines.append(f"  {item.note}")
            if item.text:
                lines.append(item.text.rstrip("\n"))
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _current_diffs(self) -> list[FileDiff]:
        remaining = MAX_DIFF_TOTAL_LINES
        diffs: list[FileDiff] = []
        for snapshot in sorted(self.files.values(),
                               key=lambda item: item.display):
            item = self._diff_one(snapshot, remaining)
            if item is None:
                continue
            diffs.append(item)
            remaining = max(0, remaining - len(item.text.splitlines()))
        return diffs

    def _diff_one(self, snapshot: FileSnapshot,
                  remaining: int) -> FileDiff | None:
        display = snapshot.display
        if snapshot.error:
            return FileDiff(display, "unavailable", note=snapshot.error)

        current, error, exists, is_dir = self._read_current(snapshot)
        if error:
            return FileDiff(display, "unavailable", note=error)

        if snapshot.is_dir:
            if not exists:
                return FileDiff(display, "absent",
                                note="created directory is gone")
            if is_dir:
                return None
            return FileDiff(display, "type changed",
                            note="directory is now a file")

        if is_dir:
            return FileDiff(display, "type changed",
                            note="file is now a directory")
        if snapshot.existed and snapshot.content is None:
            return FileDiff(display, "unavailable",
                            note="original content is unavailable")

        before = snapshot.content or b""
        if not exists:
            if not snapshot.existed:
                return FileDiff(display, "absent",
                                note="created file is gone")
            after = b""
            kind = "deleted"
        else:
            after = current or b""
            if not snapshot.existed:
                kind = "created"
            elif before == after:
                return None
            else:
                kind = "modified"

        if len(before) > MAX_DIFF_BYTES or len(after) > MAX_DIFF_BYTES:
            return FileDiff(
                display, "large",
                note=(f"inline diff skipped: {len(before):,} B -> "
                      f"{len(after):,} B (limit {MAX_DIFF_BYTES:,} B)"),
            )
        if b"\x00" in before or b"\x00" in after:
            return FileDiff(
                display, "binary",
                note=(f"binary file: {len(before):,} B -> "
                      f"{len(after):,} B; no textual diff"),
            )

        before_text = before.decode("utf-8", errors="replace")
        after_text = after.decode("utf-8", errors="replace")
        from_name = f"a/{display}" if snapshot.existed else "/dev/null"
        to_name = f"b/{display}" if exists else "/dev/null"
        diff_lines = list(difflib.unified_diff(
            before_text.splitlines(keepends=True),
            after_text.splitlines(keepends=True),
            fromfile=from_name,
            tofile=to_name,
            n=3,
        ))
        if not diff_lines:
            return FileDiff(display, kind,
                            note="bytes differ but no textual diff")

        added = sum(1 for line in diff_lines
                    if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff_lines
                      if line.startswith("-") and not line.startswith("---"))
        allowed = min(MAX_DIFF_LINES, max(0, remaining))
        truncated = len(diff_lines) > allowed
        note = ""
        if truncated:
            note = (f"diff truncated to {allowed} of {len(diff_lines)} lines"
                    if allowed else
                    "diff omitted: total inline diff limit reached")
            diff_lines = diff_lines[:allowed]
        return FileDiff(
            display, kind, added=added, removed=removed,
            text="".join(diff_lines), note=note, truncated=truncated,
        )

    def _read_current(self, snapshot: FileSnapshot):
        """Read the path now, refusing symlinks and escapes. Never writes."""
        if os.path.islink(snapshot.path):
            return None, "path is now a symlink; refusing to read", True, False
        resolved = os.path.realpath(snapshot.path)
        if not self._inside(resolved):
            return None, "path is outside the workspace now", True, False
        if not os.path.exists(resolved):
            return b"", "", False, False
        if os.path.isdir(resolved):
            return None, "", True, True
        try:
            with open(resolved, "rb") as handle:
                return handle.read(), "", True, False
        except OSError as error:
            return None, f"could not read current file: {error}", True, False

    # ------------------------------------------------------------- restore
    def restore_files(self) -> RestoreResult:
        """Restore the captured files; never touch a path outside the fence."""
        result = RestoreResult()
        if self.shell_ran:
            result.warnings.append(
                "Shell commands ran this turn; changes they made outside the "
                "tracked files are not captured."
            )

        # Files first, created directories last, so an emptied directory can be
        # removed after its children are gone.
        snapshots = sorted(self.files.values(),
                           key=lambda item: (item.is_dir, item.display))
        for snapshot in snapshots:
            try:
                self._restore_one(snapshot, result)
            except OSError as error:
                result.failed.append((snapshot.display, str(error)))

        if result.ok:
            self.restored_at = time.time()
        return result

    def _restore_one(self, snapshot: FileSnapshot,
                     result: RestoreResult) -> None:
        if os.path.islink(snapshot.path):
            result.failed.append(
                (snapshot.display, "path is now a symlink; refusing to follow"))
            return
        resolved = os.path.realpath(snapshot.path)
        if not self._inside(resolved):
            result.failed.append(
                (snapshot.display, "path is outside the workspace now"))
            return
        if snapshot.error:
            result.failed.append((snapshot.display, snapshot.error))
            return

        if snapshot.is_dir:
            if snapshot.existed:
                return
            if os.path.isdir(resolved):
                try:
                    os.rmdir(resolved)
                except OSError as error:
                    result.failed.append(
                        (snapshot.display,
                         f"directory is not empty ({error})"))
                else:
                    result.removed.append(snapshot.display)
            elif os.path.exists(resolved):
                result.failed.append(
                    (snapshot.display, "created path is no longer a directory"))
            return

        if snapshot.existed:
            if snapshot.content is None:
                result.failed.append(
                    (snapshot.display, "original content is unavailable"))
                return
            self._write_atomic(resolved, snapshot.content, snapshot.mode)
            result.restored.append(snapshot.display)
            return

        if os.path.lexists(resolved):
            if os.path.isdir(resolved):
                result.failed.append(
                    (snapshot.display, "created file is now a directory"))
                return
            os.remove(resolved)
            result.removed.append(snapshot.display)

    @staticmethod
    def _write_atomic(path: str, content: bytes, mode: int | None) -> None:
        parent = os.path.dirname(path) or "."
        os.makedirs(parent, exist_ok=True)
        handle, temporary = tempfile.mkstemp(
            prefix=".tamias-restore-", dir=parent)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(content)
            if mode is not None:
                os.chmod(temporary, mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _inside(self, path: str) -> bool:
        return (path == self.workspace
                or path.startswith(self.workspace + os.sep))
