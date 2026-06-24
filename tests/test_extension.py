from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ipy_runlog.extension import RunLogMagics, _parse_start_args, _resolve_output_path


def test_parse_start_args_defaults() -> None:
    assert _parse_start_args("") == (None, None, False)


def test_parse_start_args_with_name() -> None:
    assert _parse_start_args("analysis") == ("analysis", None, False)


def test_parse_start_args_with_directory() -> None:
    assert _parse_start_args("analysis -d './run logs'") == (
        "analysis",
        "./run logs",
        False,
    )


def test_parse_start_args_with_directory_only() -> None:
    assert _parse_start_args("-d ~/runlogs") == (None, "~/runlogs", False)


def test_parse_start_args_with_output() -> None:
    assert _parse_start_args("analysis --output") == ("analysis", None, True)


def test_parse_start_args_output_and_directory() -> None:
    assert _parse_start_args("analysis -d ./logs --output") == (
        "analysis",
        "./logs",
        True,
    )


def test_parse_start_args_rejects_unknown_option() -> None:
    with pytest.raises(ValueError, match="unknown option: --only-input"):
        _parse_start_args("--only-input")


def test_parse_start_args_rejects_duplicate_name() -> None:
    with pytest.raises(ValueError, match="only one log name may be specified"):
        _parse_start_args("foo bar")


def test_runlog_start_help_lists_options(capsys) -> None:
    magics = RunLogMagics(shell=SimpleNamespace())

    magics.runlog("start --help")

    output = capsys.readouterr().out
    assert "Usage: %runlog start [NAME] [OPTIONS]" in output
    assert "-d PATH" in output
    assert "--output" in output


def test_runlog_help_lists_commands(capsys) -> None:
    magics = RunLogMagics(shell=SimpleNamespace())

    magics.runlog("help")

    output = capsys.readouterr().out
    assert "Usage: %runlog <command>" in output
    assert "start" in output
    assert "stop" in output
    assert "status" in output


def test_runlog_unknown_command(capsys) -> None:
    magics = RunLogMagics(shell=SimpleNamespace())

    magics.runlog("unknown")

    output = capsys.readouterr().out
    assert "unknown command 'unknown'" in output


def test_resolve_output_path_uses_default_directory() -> None:
    with patch("ipy_runlog.extension.Path.cwd", return_value=Path("/work")):
        output_path = _resolve_output_path("analysis", None)

    assert output_path == Path("/work/.ipy_runlog/analysis.jsonl")


def test_resolve_output_path_uses_specified_directory() -> None:
    output_path = _resolve_output_path("analysis.jsonl", "./logs")

    assert output_path == Path("logs/analysis.jsonl")
