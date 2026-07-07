from __future__ import annotations

import re
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
  new [TITLE] [OPTIONS]  Close current log and start a new one.
  title TITLE            Update the title and rename the log file.
  stop                   Stop recording manually.
  status                 Show current recording status.
  help                   Show this help message.

Options for 'new':
  TITLE      Human-readable title; also used to derive the file name.
             (default: current timestamp)
  -d PATH    Output directory (default: .ipy_runlog/)
  -h, --help Show this help message
"""

_NEW_HELP = """\
Usage: %runlog new [TITLE] [OPTIONS]

Close the current log and start recording to a new file.
Cell input and errors are recorded.

Arguments:
  TITLE      Human-readable title written into the QMD frontmatter.
             Also used to derive the file name (e.g. "My Analysis" → my-analysis.qmd).
             Defaults to a timestamp-based name when omitted.

Options:
  -d PATH    Output directory (default: .ipy_runlog/)
  -h, --help Show this help message"""


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
            title, directory = _parse_new_args(line)
        except ValueError as exc:
            print(f"runlog new: {exc}")
            return

        state = self._state()
        logger: RunLogger | None = state.get("logger")
        if logger and logger.active:
            logger.stop()

        config = load_config(Path.cwd())
        output_path = _resolve_output_path(
            title,
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

        old_path = logger.output_path
        new_name = _title_to_filename(title)
        logger.rename(new_name)
        logger.set_title(title)
        print(
            f"runlog title set: {title} (renamed: {old_path.name} -> {logger.output_path.name})"
        )

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
        None,
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


def _parse_new_args(line: str) -> tuple[str | None, str | None]:
    try:
        args = shlex.split(line)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    title_parts: list[str] = []
    directory = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "-d":
            index += 1
            if index >= len(args):
                raise ValueError("-d requires a path")
            directory = args[index]
        elif arg.startswith("-"):
            raise ValueError(f"unknown option: {arg}")
        else:
            title_parts.append(arg)
        index += 1

    title = " ".join(title_parts) or None
    return title, directory


def _title_to_filename(title: str) -> str:
    """Derive a filesystem-safe stem from a human-readable title."""
    slug = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).strip().lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or datetime.now().strftime("%Y%m%d-%H%M%S")


def _resolve_output_path(title: str | None, directory: str | None = None) -> Path:
    if title:
        filename = _title_to_filename(title) + ".qmd"
    else:
        filename = datetime.now().strftime("%Y%m%d-%H%M%S") + ".qmd"
    output_directory = (
        Path(directory).expanduser() if directory else Path.cwd() / ".ipy_runlog"
    )
    return output_directory / filename
