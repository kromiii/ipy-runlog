from __future__ import annotations

import shlex
from datetime import datetime
from pathlib import Path

from IPython.core.magic import Magics, line_magic, magics_class

from .config import load_config
from .logger import RunLogger

_STATE_ATTR = "_ipy_runlog_state"

_HELP = """\
Usage: %runlog <command> [ARGS]

Commands:
  new [NAME] [OPTIONS]  Close current log and start a new one.
  rename NAME           Rename the current log file (recording continues).
  title TITLE           Update the title in the current log's frontmatter.
  stop                  Stop recording manually.
  status                Show current recording status.
  help                  Show this help message.

Options for 'new':
  NAME           Log file name (default: current timestamp)
  --title TITLE  Title written into the QMD frontmatter (default: "ipy-runlog")
  -d PATH        Output directory (default: .ipy_runlog/)
  -h, --help     Show this help message
"""

_NEW_HELP = """\
Usage: %runlog new [NAME] [OPTIONS]

Close the current log and start recording to a new file.
Cell input and errors are recorded.

Arguments:
  NAME           Log file name (default: current timestamp)

Options:
  --title TITLE  Title written into the QMD frontmatter (default: "ipy-runlog")
  -d PATH        Output directory (default: .ipy_runlog/)
  -h, --help     Show this help message"""


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

        if command == "new":
            self._runlog_new(rest)
        elif command == "rename":
            self._runlog_rename(rest)
        elif command == "title":
            self._runlog_title(rest)
        elif command == "stop":
            self._runlog_stop()
        elif command == "status":
            self._runlog_status()
        else:
            print(f"runlog: unknown command '{command}'. Run '%runlog help' for usage.")

    def _runlog_new(self, line: str = "") -> None:
        if _help_requested(line):
            print(_NEW_HELP)
            return
        try:
            name, directory, title = _parse_new_args(line)
        except ValueError as exc:
            print(f"runlog new: {exc}")
            return

        state = self._state()
        logger: RunLogger | None = state.get("logger")
        if logger and logger.active:
            logger.stop()

        config = load_config(Path.cwd())
        output_path = _resolve_output_path(
            name or config.get("name"),
            directory or config.get("directory"),
        )
        logger = RunLogger(
            self.shell,
            output_path,
            record_error=True,
            title=title,
            author=config.get("author"),
        )
        logger.start()
        state["logger"] = logger
        print(f"runlog started: {output_path}")

    def _runlog_rename(self, line: str = "") -> None:
        try:
            args = shlex.split(line)
        except ValueError as exc:
            print(f"runlog rename: {exc}")
            return

        if not args:
            print("runlog rename: a name is required")
            return
        if len(args) > 1:
            print("runlog rename: only one name may be specified")
            return

        state = self._state()
        logger: RunLogger | None = state.get("logger")
        if not logger or not logger.active:
            print("runlog is not running")
            return

        old_path = logger.output_path
        logger.rename(args[0])
        print(f"runlog renamed: {old_path.name} -> {logger.output_path.name}")

    def _runlog_title(self, line: str = "") -> None:
        try:
            args = shlex.split(line)
        except ValueError as exc:
            print(f"runlog title: {exc}")
            return

        if not args:
            print("runlog title: a title is required")
            return

        title = " ".join(args)
        state = self._state()
        logger: RunLogger | None = state.get("logger")
        if not logger or not logger.active:
            print("runlog is not running")
            return

        logger.set_title(title)
        print(f"runlog title set: {title}")

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
    state = {"logger": None, "magics_registered": True}
    setattr(ipython, _STATE_ATTR, state)

    config = load_config(Path.cwd())
    output_path = _resolve_output_path(
        config.get("name"),
        config.get("directory"),
    )
    logger = RunLogger(
        ipython,
        output_path,
        record_error=True,
        author=config.get("author"),
    )
    logger.start()
    state["logger"] = logger


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


def _parse_new_args(line: str) -> tuple[str | None, str | None, str | None]:
    try:
        args = shlex.split(line)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    name = None
    directory = None
    title = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "-d":
            index += 1
            if index >= len(args):
                raise ValueError("-d requires a path")
            directory = args[index]
        elif arg == "--title":
            index += 1
            if index >= len(args):
                raise ValueError("--title requires a value")
            title = args[index]
        elif arg.startswith("-"):
            raise ValueError(f"unknown option: {arg}")
        elif name is None:
            name = arg
        else:
            raise ValueError("only one log name may be specified")
        index += 1

    return name, directory, title


def _resolve_output_path(name: str | None, directory: str | None = None) -> Path:
    filename = name or datetime.now().strftime("%Y%m%d-%H%M%S")
    if not filename.endswith(".qmd"):
        filename = f"{filename}.qmd"
    output_directory = Path(directory).expanduser() if directory else Path.cwd() / ".ipy_runlog"
    return output_directory / filename
