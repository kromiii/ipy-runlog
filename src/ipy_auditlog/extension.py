from __future__ import annotations

from datetime import datetime
from pathlib import Path

from IPython.core.magic import Magics, line_magic, magics_class

from .logger import AuditLogger

_STATE_ATTR = "_ipy_auditlog_state"


@magics_class
class AuditLogMagics(Magics):
    def _state(self) -> dict:
        state = getattr(self.shell, _STATE_ATTR, None)
        if state is None:
            state = {"logger": None, "magics_registered": True}
            setattr(self.shell, _STATE_ATTR, state)
        return state

    @line_magic
    def auditlog_start(self, line: str = "") -> None:
        name = line.strip() or None
        output_path = _resolve_output_path(name)
        state = self._state()
        logger: AuditLogger | None = state.get("logger")
        if logger and logger.active:
            print(f"auditlog already running: {logger.output_path}")
            return
        logger = AuditLogger(self.shell, output_path)
        logger.start()
        state["logger"] = logger
        print(f"auditlog started: {output_path}")

    @line_magic
    def auditlog_stop(self, line: str = "") -> None:
        state = self._state()
        logger: AuditLogger | None = state.get("logger")
        if not logger or not logger.active:
            print("auditlog is not running")
            return
        logger.stop()
        print("auditlog stopped")

    @line_magic
    def auditlog_status(self, line: str = "") -> None:
        state = self._state()
        logger: AuditLogger | None = state.get("logger")
        if logger and logger.active:
            print(f"running: {logger.output_path}")
            return
        print("stopped")


def load_ipython_extension(ipython) -> None:
    state = getattr(ipython, _STATE_ATTR, None)
    if state and state.get("magics_registered"):
        return
    ipython.register_magics(AuditLogMagics)
    setattr(ipython, _STATE_ATTR, {"logger": None, "magics_registered": True})


def unload_ipython_extension(ipython) -> None:
    state = getattr(ipython, _STATE_ATTR, None)
    if not state:
        return
    logger = state.get("logger")
    if logger and logger.active:
        logger.stop()
    for name in ("auditlog_start", "auditlog_stop", "auditlog_status"):
        ipython.magics_manager.magics["line"].pop(name, None)
    delattr(ipython, _STATE_ATTR)


def _resolve_output_path(name: str | None) -> Path:
    filename = name or datetime.now().strftime("%Y%m%d-%H%M%S")
    if not filename.endswith(".jsonl"):
        filename = f"{filename}.jsonl"
    return Path.cwd() / ".jupyter_audit" / filename
