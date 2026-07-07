from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ipy_runlog.extension import RunLogMagics, _parse_new_args, _resolve_output_path, _title_to_filename


# ---------------------------------------------------------------------------
# _parse_new_args
# ---------------------------------------------------------------------------


def test_parse_new_args_defaults() -> None:
    assert _parse_new_args("") == (None, None)


def test_parse_new_args_with_title() -> None:
    assert _parse_new_args("My Analysis") == ("My Analysis", None)


def test_parse_new_args_with_directory() -> None:
    assert _parse_new_args("My Analysis -d './run logs'") == (
        "My Analysis",
        "./run logs",
    )


def test_parse_new_args_with_directory_only() -> None:
    assert _parse_new_args("-d ~/runlogs") == (None, "~/runlogs")


def test_parse_new_args_multiword_title_without_quotes() -> None:
    assert _parse_new_args("My Analysis Session") == ("My Analysis Session", None)


def test_parse_new_args_multiword_title_with_directory() -> None:
    assert _parse_new_args("My Analysis -d ./logs") == ("My Analysis", "./logs")


def test_parse_new_args_rejects_unknown_option() -> None:
    with pytest.raises(ValueError, match="unknown option: --only-input"):
        _parse_new_args("--only-input")


def test_parse_new_args_title_requires_value() -> None:
    # --title no longer exists; passing it should raise unknown option
    with pytest.raises(ValueError, match="unknown option: --title"):
        _parse_new_args("--title")


# ---------------------------------------------------------------------------
# _title_to_filename
# ---------------------------------------------------------------------------


def test_title_to_filename_basic() -> None:
    assert _title_to_filename("My Analysis Session") == "my-analysis-session"


def test_title_to_filename_strips_special_chars() -> None:
    assert _title_to_filename("Hello, World!") == "hello-world"


def test_title_to_filename_collapses_hyphens() -> None:
    assert _title_to_filename("foo  --  bar") == "foo-bar"


def test_title_to_filename_single_word() -> None:
    assert _title_to_filename("experiment") == "experiment"


# ---------------------------------------------------------------------------
# %runlog new --help
# ---------------------------------------------------------------------------


def test_runlog_new_help_lists_options(capsys) -> None:
    magics = RunLogMagics(shell=SimpleNamespace())

    magics.runlog("new --help")

    output = capsys.readouterr().out
    assert "Usage: %runlog new [TITLE] [OPTIONS]" in output
    assert "-d PATH" in output
    assert "--title" not in output


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
    assert "title" in output
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

    log_file = tmp_path / "old.qmd"
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
# %runlog title
# ---------------------------------------------------------------------------


def test_runlog_title_calls_set_title(tmp_path, capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)

    from ipy_runlog.logger import RunLogger
    from ipy_runlog.extension import _STATE_ATTR

    log_file = tmp_path / "run.qmd"
    log_file.write_text('---\ntitle: "old"\ndate: now\n---\n\n', encoding="utf-8")
    logger = RunLogger(None, log_file)
    logger._active = True

    setattr(shell, _STATE_ATTR, {"logger": logger, "magics_registered": True})

    with patch.object(logger, "set_title") as mock_set_title:
        magics.runlog("title 'My Analysis'")
        mock_set_title.assert_called_once_with("My Analysis")


def test_runlog_title_requires_argument(capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)

    from ipy_runlog.extension import _STATE_ATTR

    setattr(shell, _STATE_ATTR, {"logger": None, "magics_registered": True})

    magics.runlog("title")

    output = capsys.readouterr().out
    assert "a title is required" in output


def test_runlog_title_when_not_running(capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)

    from ipy_runlog.extension import _STATE_ATTR

    setattr(shell, _STATE_ATTR, {"logger": None, "magics_registered": True})

    magics.runlog("title 'My Session'")

    output = capsys.readouterr().out
    assert "runlog is not running" in output


# ---------------------------------------------------------------------------
# _resolve_output_path
# ---------------------------------------------------------------------------


def test_resolve_output_path_uses_default_directory() -> None:
    with patch("ipy_runlog.extension.Path.cwd", return_value=Path("/work")):
        output_path = _resolve_output_path("My Analysis", None)

    assert output_path == Path("/work/.ipy_runlog/my-analysis.qmd")


def test_resolve_output_path_uses_specified_directory() -> None:
    output_path = _resolve_output_path("My Analysis", "./logs")

    assert output_path == Path("logs/my-analysis.qmd")


def test_resolve_output_path_none_title_uses_timestamp(monkeypatch) -> None:
    with patch("ipy_runlog.extension.Path.cwd", return_value=Path("/work")):
        output_path = _resolve_output_path(None, None)

    assert output_path.suffix == ".qmd"
    assert output_path.parent == Path("/work/.ipy_runlog")
