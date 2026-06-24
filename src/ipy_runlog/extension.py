from __future__ import annotations

import shlex
from datetime import datetime
from pathlib import Path

from IPython.core.magic import Magics, line_magic, magics_class

from .logger import RunLogger

_STATE_ATTR = "_ipy_runlog_state"
_HELP = """\
Usage: %runlog <command> [ARGS]

Commands:
  start [NAME] [OPTIONS]  Start recording cell execution events as JSON Lines.
  stop                    Stop recording.
  status                  Show current recording status.
  help                    Show this help message.

Options for 'start':
  NAME        Log file name (default: current timestamp)
  -d PATH     Output directory (default: .ipy_runlog/)
  --output    Also record cell output (default: off)
  -h, --help  Show this help message
"""

_START_HELP = """\
Usage: %runlog start [NAME] [OPTIONS]

Start recording cell execution events as JSON Lines.
By default, cell input and errors are recorded.

Arguments:
  NAME        Log file name (default: current timestamp)

Options:
  -d PATH     Output directory (default: .ipy_runlog/)
  --output    Also record cell output (default: off)
  -h, --help  Show this help message"""


@magics_class
class RunLogMagics(Magics):
    def _state(self) -> dict:
        state = getattr(self.shell, _STATE_ATTR, None)
        if state is None:
            state = {"logger": None, "magics_registered": True}
            setattr(self.shell, _STATE_ATTR, state)
        return state

    @line_magic
    def runlog(self, line: str = "") -> None:
        try:
            args = shlex.split(line)
        except ValueError as exc:
            print(f"runlog: {exc}")
            return

        if not args or args[0] in ("-h", "--help", "help"):
            print(_HELP)
            return

        command, rest = args[0], " ".join(args[1:])

        if command == "start":
            self._runlog_start(rest)
        elif command == "stop":
            self._runlog_stop()
        elif command == "status":
            self._runlog_status()
        else:
            print(f"runlog: unknown command '{command}'. Run '%runlog help' for usage.")

    def _runlog_start(self, line: str = "") -> None:
        if _help_requested(line):
            print(_START_HELP)
            return
        try:
            name, directory, record_output = _parse_start_args(line)
        except ValueError as exc:
            print(f"runlog start: {exc}")
            return
        output_path = _resolve_output_path(name, directory)
        state = self._state()
        logger: RunLogger | None = state.get("logger")
        if logger and logger.active:
            print(f"runlog already running: {logger.output_path}")
            return
        logger = RunLogger(
            self.shell,
            output_path,
            record_output=record_output,
            record_error=True,
        )
        logger.start()
        state["logger"] = logger
        print(f"runlog started: {output_path}")

    def _runlog_stop(self) -> None:
        state = self._state()
        logger: RunLogger | None = state.get("logger")
        if not logger or not logger.active:
            print("runlog is not running")
            return
        logger.stop()
        print("runlog stopped")

    def _runlog_status(self) -> None:
        state = self._state()
        logger: RunLogger | None = state.get("logger")
        if logger and logger.active:
            print(f"running: {logger.output_path}")
            return
        print("stopped")


def load_ipython_extension(ipython) -> None:
    state = getattr(ipython, _STATE_ATTR, None)
    if state and state.get("magics_registered"):
        return
    ipython.register_magics(RunLogMagics)
    setattr(ipython, _STATE_ATTR, {"logger": None, "magics_registered": True})


def unload_ipython_extension(ipython) -> None:
    state = getattr(ipython, _STATE_ATTR, None)
    if not state:
        return
    logger = state.get("logger")
    if logger and logger.active:
        logger.stop()
    ipython.magics_manager.magics["line"].pop("runlog", None)
    delattr(ipython, _STATE_ATTR)


def _help_requested(line: str) -> bool:
    try:
        return any(arg in ("-h", "--help") for arg in shlex.split(line))
    except ValueError:
        return False


def _parse_start_args(line: str) -> tuple[str | None, str | None, bool]:
    try:
        args = shlex.split(line)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    name = None
    directory = None
    record_output = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "-d":
            index += 1
            if index >= len(args):
                raise ValueError("-d requires a path")
            directory = args[index]
        elif arg == "--output":
            record_output = True
        elif arg.startswith("-"):
            raise ValueError(f"unknown option: {arg}")
        elif name is None:
            name = arg
        else:
            raise ValueError("only one log name may be specified")
        index += 1

    return name, directory, record_output


def _resolve_output_path(name: str | None, directory: str | None = None) -> Path:
    filename = name or datetime.now().strftime("%Y%m%d-%H%M%S")
    if not filename.endswith(".jsonl"):
        filename = f"{filename}.jsonl"
    output_directory = Path(directory).expanduser() if directory else Path.cwd() / ".ipy_runlog"
    return output_directory / filename
