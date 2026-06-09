from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, ipython: Any, output_path: Path) -> None:
        self._ipython = ipython
        self.output_path = output_path
        self._active = False
        self._last_started_at: str | None = None
        self._last_code: str = ""
        self._last_started_dt: datetime | None = None

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._ipython.events.register("pre_run_cell", self._on_pre_run_cell)
        self._ipython.events.register("post_run_cell", self._on_post_run_cell)
        self._active = True
        started_at = _now_iso()
        self._last_started_at = started_at
        self._append_event(
            {
                "event": "audit_started",
                "started_at": started_at,
                "path": str(self.output_path),
            }
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._ipython.events.unregister("pre_run_cell", self._on_pre_run_cell)
        self._ipython.events.unregister("post_run_cell", self._on_post_run_cell)
        self._active = False
        self._append_event(
            {
                "event": "audit_stopped",
                "stopped_at": _now_iso(),
                "path": str(self.output_path),
            }
        )

    def _on_pre_run_cell(self, info: Any) -> None:
        self._last_code = getattr(info, "raw_cell", "") or ""
        self._last_started_dt = datetime.now()
        self._last_started_at = self._last_started_dt.isoformat(timespec="microseconds")

    def _on_post_run_cell(self, result: Any) -> None:
        started_dt = self._last_started_dt or datetime.now()
        started_at = self._last_started_at or started_dt.isoformat(timespec="microseconds")
        ended_dt = datetime.now()
        error = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
        status = "failed" if error else "success"
        event = {
            "event": "cell_executed",
            "started_at": started_at,
            "ended_at": ended_dt.isoformat(timespec="microseconds"),
            "elapsed_sec": (ended_dt - started_dt).total_seconds(),
            "status": status,
            "execution_count": getattr(result, "execution_count", None),
            "code": self._last_code,
            "error": _format_error(error),
        }
        self._append_event(event)

    def _append_event(self, payload: dict[str, Any]) -> None:
        with self.output_path.open("a", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            f.write("\n")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def _format_error(error: BaseException | None) -> dict[str, str] | None:
    if error is None:
        return None
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    return {
        "type": type(error).__name__,
        "message": str(error),
        "traceback": tb,
    }
