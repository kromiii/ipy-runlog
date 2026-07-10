from __future__ import annotations

import atexit
from datetime import datetime
from pathlib import Path
from typing import Any


class RunLogger:
    def __init__(
        self,
        ipython: Any,
        output_path: Path,
        *,
        record_error: bool = True,
        title: str | None = None,
        author: str | None = None,
    ) -> None:
        self._ipython = ipython
        self.output_path = output_path
        self._record_error = record_error
        self._active = False
        self._last_started_at: str | None = None
        self._last_code: str = ""
        self._last_started_dt: datetime | None = None
        self._title: str = title or "ipy-runlog"
        self._author: str | None = author
        self._cell_count: int = 0

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._cell_count = 0
        started_at = _now_iso()
        self._last_started_at = started_at
        self._write_header(started_at)
        self._ipython.events.register("pre_run_cell", self._on_pre_run_cell)
        self._ipython.events.register("post_run_cell", self._on_post_run_cell)
        self._active = True
        atexit.register(self._on_exit)

    def stop(self) -> None:
        if not self._active:
            return
        atexit.unregister(self._on_exit)
        self._ipython.events.unregister("pre_run_cell", self._on_pre_run_cell)
        self._ipython.events.unregister("post_run_cell", self._on_post_run_cell)
        self._active = False

    def rename(self, new_name: str) -> None:
        """Rename the current log file. Recording continues uninterrupted."""
        if not new_name.endswith(".qmd"):
            new_name = f"{new_name}.qmd"
        new_path = self.output_path.parent / new_name
        self.output_path.rename(new_path)
        self.output_path = new_path

    def set_title(self, title: str) -> None:
        """Update the title in the QMD frontmatter. Can be called while recording."""
        self._title = title
        _update_frontmatter(self.output_path, "title", f'"{title}"')

    def set_author(self, author: str) -> None:
        """Update the author in the QMD frontmatter. Can be called while recording."""
        self._author = author
        _update_frontmatter(self.output_path, "author", f'"{author}"')

    def write_comment(self, comment: str) -> None:
        """Write a comment directly to the QMD file."""
        if not self._active:
            return
        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(comment + "\n\n")

    def _on_exit(self) -> None:
        """Called by atexit when the Python process exits normally."""
        if not self._active:
            return
        self._ipython.events.unregister("pre_run_cell", self._on_pre_run_cell)
        self._ipython.events.unregister("post_run_cell", self._on_post_run_cell)
        self._active = False

    def _on_pre_run_cell(self, info: Any) -> None:
        self._last_code = getattr(info, "raw_cell", "") or ""
        self._last_started_dt = datetime.now()
        self._last_started_at = self._last_started_dt.isoformat(timespec="microseconds")

    def _on_post_run_cell(self, result: Any) -> None:
        if self._last_started_dt is None:
            return
        if _is_runlog_command(self._last_code):
            self._last_started_dt = None
            return
        self._cell_count += 1
        started_dt = self._last_started_dt
        started_at = self._last_started_at or started_dt.isoformat(
            timespec="microseconds"
        )
        ended_dt = datetime.now()
        error = getattr(result, "error_in_exec", None) or getattr(
            result, "error_before_exec", None
        )
        status = "failed" if error else "success"
        elapsed = (ended_dt - started_dt).total_seconds()

        parts: list[str] = []
        parts.append(
            f"<!-- cell: started={started_at},"
            f" ended={ended_dt.isoformat(timespec='microseconds')},"
            f" status={status}, elapsed={elapsed:.3f}s -->"
        )
        if self._record_error and error is not None:
            parts.append(f"```{{python}}\n#| error: true\n{self._last_code}\n```")
        else:
            parts.append(f"```{{python}}\n{self._last_code}\n```")

        with self.output_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(parts) + "\n\n")

        self._last_started_dt = None

    def _write_header(self, started_at: str) -> None:
        lines = ["---"]
        lines.append(f'title: "{self._title}"')
        if self._author:
            lines.append(f'author: "{self._author}"')
        lines.append(f"date: {started_at}")
        lines.append("---")
        lines.append("")
        self.output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def _update_frontmatter(path: Path, key: str, value: str) -> None:
    """Insert or replace a key-value pair in the YAML frontmatter of a QMD file."""
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return

    if not content.startswith("---\n"):
        return

    close_idx = content.find("\n---\n", 4)
    if close_idx == -1:
        return

    frontmatter_body = content[4:close_idx]
    rest = content[close_idx + 5 :]  # skip "\n---\n"

    new_key_line = f"{key}: {value}"
    lines = frontmatter_body.split("\n")
    found = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith(f"{key}:"):
            new_lines.append(new_key_line)
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(new_key_line)

    new_content = "---\n" + "\n".join(new_lines) + "\n---\n" + rest
    path.write_text(new_content, encoding="utf-8")


def _is_runlog_command(code: str) -> bool:
    """Return True if the code contains a %runlog command line magic."""
    for line in code.splitlines():
        parts = line.split()
        if parts and parts[0] == "%runlog":
            return True
    return False
