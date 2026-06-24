from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ipy_runlog.extension import RunLogMagics, _parse_new_args, _resolve_output_path


# ---------------------------------------------------------------------------
# _parse_new_args
# ---------------------------------------------------------------------------


def test_parse_new_args_defaults() -> None:
    assert _parse_new_args("") == (None, None, False)


def test_parse_new_args_with_name() -> None:
    assert _parse_new_args("analysis") == ("analysis", None, False)


def test_parse_new_args_with_directory() -> None:
    assert _parse_new_args("analysis -d './run logs'") == (
        "analysis",
        "./run logs",
        False,
    )


def test_parse_new_args_with_directory_only() -> None:
    assert _parse_new_args("-d ~/runlogs") == (None, "~/runlogs", False)


def test_parse_new_args_with_output() -> None:
    assert _parse_new_args("analysis --output") == ("analysis", None, True)


def test_parse_new_args_output_and_directory() -> None:
    assert _parse_new_args("analysis -d ./logs --output") == (
        "analysis",
        "./logs",
        True,
    )


def test_parse_new_args_rejects_unknown_option() -> None:
    with pytest.raises(ValueError, match="unknown option: --only-input"):
        _parse_new_args("--only-input")


def test_parse_new_args_rejects_duplicate_name() -> None:
    with pytest.raises(ValueError, match="only one log name may be specified"):
        _parse_new_args("foo bar")


# ---------------------------------------------------------------------------
# %runlog new --help
# ---------------------------------------------------------------------------


def test_runlog_new_help_lists_options(capsys) -> None:
    magics = RunLogMagics(shell=SimpleNamespace())

    magics.runlog("new --help")

    output = capsys.readouterr().out
    assert "Usage: %runlog new [NAME] [OPTIONS]" in output
    assert "-d PATH" in output
    assert "--output" in output


# ---------------------------------------------------------------------------
# %runlog help / unknown command
# ---------------------------------------------------------------------------


def test_runlog_help_lists_commands(capsys) -> None:
    magics = RunLogMagics(shell=SimpleNamespace())

    magics.runlog("help")

    output = capsys.readouterr().out
    assert "Usage: %runlog <command>" in output
    assert "new" in output
    assert "rename" in output
    assert "stop" in output
    assert "status" in output


def test_runlog_unknown_command(capsys) -> None:
    magics = RunLogMagics(shell=SimpleNamespace())

    magics.runlog("unknown")

    output = capsys.readouterr().out
    assert "unknown command 'unknown'" in output


def test_runlog_stop_when_not_running(capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)

    from ipy_runlog.extension import _STATE_ATTR

    setattr(shell, _STATE_ATTR, {"logger": None, "magics_registered": True})

    magics.runlog("stop")

    output = capsys.readouterr().out
    assert "runlog is not running" in output


# ---------------------------------------------------------------------------
# %runlog rename
# ---------------------------------------------------------------------------


def test_runlog_rename_updates_path(tmp_path, capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)

    from ipy_runlog.logger import RunLogger
    from ipy_runlog.extension import _STATE_ATTR

    log_file = tmp_path / "old.jsonl"
    log_file.write_text("", encoding="utf-8")
    logger = RunLogger(None, log_file)
    logger._active = True

    setattr(shell, _STATE_ATTR, {"logger": logger, "magics_registered": True})

    with patch.object(logger, "rename") as mock_rename:
        magics.runlog("rename newname")
        mock_rename.assert_called_once_with("newname")


def test_runlog_rename_requires_name(capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)

    from ipy_runlog.extension import _STATE_ATTR

    setattr(shell, _STATE_ATTR, {"logger": None, "magics_registered": True})

    magics.runlog("rename")

    output = capsys.readouterr().out
    assert "a name is required" in output


# ---------------------------------------------------------------------------
# _resolve_output_path
# ---------------------------------------------------------------------------


def test_resolve_output_path_uses_default_directory() -> None:
    with patch("ipy_runlog.extension.Path.cwd", return_value=Path("/work")):
        output_path = _resolve_output_path("analysis", None)

    assert output_path == Path("/work/.ipy_runlog/analysis.jsonl")


def test_resolve_output_path_uses_specified_directory() -> None:
    output_path = _resolve_output_path("analysis.jsonl", "./logs")

    assert output_path == Path("logs/analysis.jsonl")
