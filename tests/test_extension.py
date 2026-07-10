from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ipy_runlog.extension import (
    RunLogMagics,
    _parse_comment,
    _parse_new_args,
    _parse_set_args,
    _resolve_output_path,
    _title_to_filename,
)


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
# _parse_set_args
# ---------------------------------------------------------------------------


def test_parse_set_args_title() -> None:
    assert _parse_set_args("--title 'My Title'") == {"title": "My Title"}


def test_parse_set_args_author() -> None:
    assert _parse_set_args("--author 'Jane Doe'") == {"author": "Jane Doe"}


def test_parse_set_args_both() -> None:
    assert _parse_set_args("--title='My Title' --author='Jane Doe'") == {
        "title": "My Title",
        "author": "Jane Doe",
    }


def test_parse_set_args_empty() -> None:
    assert _parse_set_args("") == {}


def test_parse_set_args_rejects_unknown_option() -> None:
    with pytest.raises(ValueError, match="unknown option: --foo"):
        _parse_set_args("--foo bar")


def test_parse_set_args_requires_value() -> None:
    with pytest.raises(ValueError, match="expected one argument"):
        _parse_set_args("--title")


def test_parse_set_args_help() -> None:
    with pytest.raises(ValueError, match="show_help"):
        _parse_set_args("--help")


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
    assert "set" in output
    assert "comment" in output
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
# %runlog set
# ---------------------------------------------------------------------------


def test_runlog_set_updates_title_and_author(tmp_path, capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)

    from ipy_runlog.logger import RunLogger
    from ipy_runlog.extension import _STATE_ATTR

    log_file = tmp_path / "run.qmd"
    log_file.write_text('---\ntitle: "old"\ndate: now\n---\n\n', encoding="utf-8")
    logger = RunLogger(None, log_file)
    logger._active = True

    setattr(shell, _STATE_ATTR, {"logger": logger, "magics_registered": True})

    with (
        patch.object(logger, "rename") as mock_rename,
        patch.object(logger, "set_title") as mock_set_title,
        patch.object(logger, "set_author") as mock_set_author,
    ):
        magics.runlog("set --title 'My Analysis' --author 'Jane Doe'")
        mock_rename.assert_called_once_with("my-analysis")
        mock_set_title.assert_called_once_with("My Analysis")
        mock_set_author.assert_called_once_with("Jane Doe")


def test_runlog_set_requires_at_least_one_option(capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)

    from ipy_runlog.logger import RunLogger
    from ipy_runlog.extension import _STATE_ATTR

    logger = RunLogger(None, Path("dummy.qmd"))
    logger._active = True
    setattr(shell, _STATE_ATTR, {"logger": logger, "magics_registered": True})

    magics.runlog("set")

    output = capsys.readouterr().out
    assert "at least one option must be specified" in output


def test_runlog_set_when_not_running(capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)

    from ipy_runlog.extension import _STATE_ATTR

    setattr(shell, _STATE_ATTR, {"logger": None, "magics_registered": True})

    magics.runlog("set --title 'My Session'")

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


# ---------------------------------------------------------------------------
# _parse_comment
# ---------------------------------------------------------------------------


def test_parse_comment_basic() -> None:
    assert _parse_comment("hogehoge") == "hogehoge"


def test_parse_comment_stripped_double_quotes() -> None:
    assert _parse_comment('"hogehoge"') == "hogehoge"


def test_parse_comment_stripped_single_quotes() -> None:
    assert _parse_comment("'hogehoge'") == "hogehoge"


def test_parse_comment_unmatched_inner_quote() -> None:
    assert _parse_comment("Let's do this") == "Let's do this"


def test_parse_comment_empty_raises() -> None:
    with pytest.raises(ValueError, match="comment text is required"):
        _parse_comment("")
    with pytest.raises(ValueError, match="comment text is required"):
        _parse_comment("   ")


# ---------------------------------------------------------------------------
# %runlog comment
# ---------------------------------------------------------------------------


def test_runlog_comment_when_not_running(capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)
    from ipy_runlog.extension import _STATE_ATTR

    setattr(shell, _STATE_ATTR, {"logger": None, "magics_registered": True})

    magics.runlog("comment hogehoge")

    output = capsys.readouterr().out
    assert "runlog is not running" in output


def test_runlog_comment_help(capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)
    from ipy_runlog.extension import _STATE_ATTR

    setattr(shell, _STATE_ATTR, {"logger": None, "magics_registered": True})

    magics.runlog("comment --help")

    output = capsys.readouterr().out
    assert "Usage: %runlog comment <TEXT>" in output


def test_runlog_comment_empty_text(capsys) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)
    from ipy_runlog.logger import RunLogger
    from ipy_runlog.extension import _STATE_ATTR

    logger = RunLogger(None, Path("dummy.qmd"))
    logger._active = True
    setattr(shell, _STATE_ATTR, {"logger": logger, "magics_registered": True})

    magics.runlog("comment")

    output = capsys.readouterr().out
    assert "runlog comment: comment text is required" in output


def test_runlog_comment_writes_to_logger(tmp_path) -> None:
    shell = SimpleNamespace()
    magics = RunLogMagics(shell=shell)
    from ipy_runlog.logger import RunLogger
    from ipy_runlog.extension import _STATE_ATTR

    log_file = tmp_path / "run.qmd"
    log_file.write_text('---\ntitle: "t"\ndate: now\n---\n\n', encoding="utf-8")
    logger = RunLogger(None, log_file)
    logger._active = True
    setattr(shell, _STATE_ATTR, {"logger": logger, "magics_registered": True})

    with patch.object(logger, "write_comment") as mock_write_comment:
        magics.runlog('comment "my comment"')
        mock_write_comment.assert_called_once_with("my comment")
