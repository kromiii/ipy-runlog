from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ipy_auditlog.extension import AuditLogMagics, _parse_start_args, _resolve_output_path


def test_parse_start_args_with_directory() -> None:
    assert _parse_start_args("analysis --directory './audit logs'") == (
        "analysis",
        "./audit logs",
        False,
        True,
    )


def test_parse_start_args_with_directory_only() -> None:
    assert _parse_start_args("-d ~/auditlogs") == (None, "~/auditlogs", False, True)


def test_parse_start_args_with_recording_options() -> None:
    assert _parse_start_args("analysis --output --no-error") == (
        "analysis",
        None,
        True,
        False,
    )


def test_parse_start_args_can_explicitly_select_defaults() -> None:
    assert _parse_start_args("--no-output --error") == (None, None, False, True)


def test_auditlog_start_help_lists_options(capsys) -> None:
    magics = AuditLogMagics(shell=SimpleNamespace())

    magics.auditlog_start("--help")

    output = capsys.readouterr().out
    assert "Usage: %auditlog_start [NAME] [OPTIONS]" in output
    assert "--directory PATH" in output
    assert "--output" in output
    assert "--no-error" in output


def test_resolve_output_path_uses_default_directory() -> None:
    with patch("ipy_auditlog.extension.Path.cwd", return_value=Path("/work")):
        output_path = _resolve_output_path("analysis", None)

    assert output_path == Path("/work/.jupyter_audit/analysis.jsonl")


def test_resolve_output_path_uses_specified_directory() -> None:
    output_path = _resolve_output_path("analysis.jsonl", "./logs")

    assert output_path == Path("logs/analysis.jsonl")
