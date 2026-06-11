from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ipy_runlog.extension import RunLogMagics, _parse_start_args, _resolve_output_path


def test_parse_start_args_with_directory() -> None:
    assert _parse_start_args("analysis --directory './run logs'") == (
        "analysis",
        "./run logs",
        False,
        True,
    )


def test_parse_start_args_with_directory_only() -> None:
    assert _parse_start_args("-d ~/runlogs") == (None, "~/runlogs", False, True)


def test_parse_start_args_with_recording_options() -> None:
    assert _parse_start_args("analysis --only-input") == (
        "analysis",
        None,
        False,
        False,
    )


@pytest.mark.parametrize(
    "line",
    (
        "--only-input --with-output",
        "--with-output --only-input",
    ),
)
def test_parse_start_args_rejects_only_input_with_output(line: str) -> None:
    with pytest.raises(
        ValueError,
        match="--only-input and --with-output cannot be used together",
    ):
        _parse_start_args(line)


def test_parse_start_args_can_explicitly_select_defaults() -> None:
    assert _parse_start_args("--no-output --error") == (None, None, False, True)


def test_runlog_start_help_lists_options(capsys) -> None:
    magics = RunLogMagics(shell=SimpleNamespace())

    magics.runlog_start("--help")

    output = capsys.readouterr().out
    assert "Usage: %runlog_start [NAME] [OPTIONS]" in output
    assert "--directory PATH" in output
    assert "--with-output" in output
    assert "--only-input" in output


def test_resolve_output_path_uses_default_directory() -> None:
    with patch("ipy_runlog.extension.Path.cwd", return_value=Path("/work")):
        output_path = _resolve_output_path("analysis", None)

    assert output_path == Path("/work/.ipy_runlog/analysis.jsonl")


def test_resolve_output_path_uses_specified_directory() -> None:
    output_path = _resolve_output_path("analysis.jsonl", "./logs")

    assert output_path == Path("logs/analysis.jsonl")
