from __future__ import annotations

import shlex
from datetime import datetime
from pathlib import Path

from IPython.core.magic import Magics, line_magic, magics_class

from .logger import AuditLogger

_STATE_ATTR = "_ipy_auditlog_state"
_START_HELP = """\
Usage: %auditlog_start [NAME] [OPTIONS]

Start recording cell execution events as JSON Lines.

Arguments:
  NAME                  Log file name (default: current timestamp)

Options:
  -d, --directory PATH  Output directory (default: .ipy_audit/)
  --with-output         Record cell output
  --no-output           Do not record cell output (default)
  --error               Record execution errors (default)
  --no-error            Do not record execution errors
  -h, --help            Show this help message
"""


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
        if _help_requested(line):
            print(_START_HELP)
            return
        try:
            name, directory, record_output, record_error = _parse_start_args(line)
        except ValueError as exc:
            print(f"auditlog_start: {exc}")
            return
        output_path = _resolve_output_path(name, directory)
        state = self._state()
        logger: AuditLogger | None = state.get("logger")
        if logger and logger.active:
            print(f"auditlog already running: {logger.output_path}")
            return
        logger = AuditLogger(
            self.shell,
            output_path,
            record_output=record_output,
            record_error=record_error,
        )
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


def _help_requested(line: str) -> bool:
    try:
        return any(arg in ("-h", "--help") for arg in shlex.split(line))
    except ValueError:
        return False


def _parse_start_args(line: str) -> tuple[str | None, str | None, bool, bool]:
    try:
        args = shlex.split(line)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    name = None
    directory = None
    record_output = False
    record_error = True
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("-d", "--directory"):
            index += 1
            if index >= len(args):
                raise ValueError(f"{arg} requires a path")
            directory = args[index]
        elif arg.startswith("--directory="):
            directory = arg.split("=", 1)[1]
            if not directory:
                raise ValueError("--directory requires a path")
        elif arg == "--with-output":
            record_output = True
        elif arg == "--no-output":
            record_output = False
        elif arg == "--error":
            record_error = True
        elif arg == "--no-error":
            record_error = False
        elif arg.startswith("-"):
            raise ValueError(f"unknown option: {arg}")
        elif name is None:
            name = arg
        else:
            raise ValueError("only one log name may be specified")
        index += 1

    return name, directory, record_output, record_error


def _resolve_output_path(name: str | None, directory: str | None = None) -> Path:
    filename = name or datetime.now().strftime("%Y%m%d-%H%M%S")
    if not filename.endswith(".jsonl"):
        filename = f"{filename}.jsonl"
    output_directory = Path(directory).expanduser() if directory else Path.cwd() / ".ipy_audit"
    return output_directory / filename
