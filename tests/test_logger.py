from types import SimpleNamespace

import pytest

from ipy_runlog.logger import RunLogger, _update_frontmatter


def _read_qmd(path) -> str:
    return path.read_text(encoding="utf-8")


def _make_shell():
    return SimpleNamespace(events=SimpleNamespace(register=lambda *a: None, unregister=lambda *a: None))


# ---------------------------------------------------------------------------
# start / stop lifecycle
# ---------------------------------------------------------------------------


def test_start_writes_frontmatter_with_recording_started(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(_make_shell(), output_path)

    logger.start()

    content = _read_qmd(output_path)
    assert "recording_started:" in content
    assert content.startswith("---\n")


def test_stop_adds_recording_stopped_to_frontmatter(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(_make_shell(), output_path)
    logger.start()

    logger.stop()

    content = _read_qmd(output_path)
    assert "recording_stopped:" in content


def test_stop_does_not_add_recording_stopped_twice(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(_make_shell(), output_path)
    logger.start()
    logger.stop()

    # calling stop again should be a no-op (active is False)
    logger.stop()

    content = _read_qmd(output_path)
    assert content.count("recording_stopped:") == 1


def test_on_exit_adds_recording_stopped_to_frontmatter(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(_make_shell(), output_path)
    logger.start()

    logger._on_exit()

    content = _read_qmd(output_path)
    assert "recording_stopped:" in content


def test_on_exit_is_idempotent_after_stop(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(_make_shell(), output_path)
    logger.start()
    logger.stop()

    logger._on_exit()

    content = _read_qmd(output_path)
    assert content.count("recording_stopped:") == 1


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------


def test_rename_moves_file_and_updates_path(tmp_path) -> None:
    output_path = tmp_path / "old.qmd"
    logger = RunLogger(None, output_path)
    logger._active = True
    output_path.write_text("---\ntitle: \"t\"\n---\n\n", encoding="utf-8")

    logger.rename("newname")

    assert not output_path.exists()
    assert logger.output_path == tmp_path / "newname.qmd"
    assert logger.output_path.exists()


def test_rename_adds_qmd_extension_if_missing(tmp_path) -> None:
    output_path = tmp_path / "old.qmd"
    output_path.write_text("", encoding="utf-8")
    logger = RunLogger(None, output_path)
    logger._active = True

    logger.rename("newname")

    assert logger.output_path.suffix == ".qmd"


def test_rename_preserves_existing_qmd_extension(tmp_path) -> None:
    output_path = tmp_path / "old.qmd"
    output_path.write_text("", encoding="utf-8")
    logger = RunLogger(None, output_path)
    logger._active = True

    logger.rename("newname.qmd")

    assert logger.output_path.name == "newname.qmd"


# ---------------------------------------------------------------------------
# cell execution
# ---------------------------------------------------------------------------


def test_cell_event_records_code_and_comment(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(None, output_path)
    output_path.write_text("---\ntitle: \"t\"\nrecording_started: now\n---\n\n", encoding="utf-8")

    logger._on_pre_run_cell(SimpleNamespace(raw_cell="x = 1"))
    logger._on_post_run_cell(
        SimpleNamespace(
            execution_count=1,
            result=None,
            error_in_exec=None,
            error_before_exec=None,
        )
    )

    content = _read_qmd(output_path)
    assert "<!-- cell:" in content
    assert "status=success" in content
    assert "```python\nx = 1\n```" in content


def test_cell_event_records_error_as_stderr_block(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(None, output_path)
    output_path.write_text("---\ntitle: \"t\"\nrecording_started: now\n---\n\n", encoding="utf-8")
    error = ValueError("invalid value")

    logger._on_pre_run_cell(SimpleNamespace(raw_cell="raise ValueError()"))
    logger._on_post_run_cell(
        SimpleNamespace(
            execution_count=1,
            result=None,
            error_in_exec=error,
            error_before_exec=None,
        )
    )

    content = _read_qmd(output_path)
    assert "status=failed" in content
    assert "```stderr" in content
    assert "ValueError" in content
    assert "invalid value" in content


def test_cell_event_no_stderr_block_on_success(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(None, output_path)
    output_path.write_text("---\ntitle: \"t\"\nrecording_started: now\n---\n\n", encoding="utf-8")

    logger._on_pre_run_cell(SimpleNamespace(raw_cell="1 + 1"))
    logger._on_post_run_cell(
        SimpleNamespace(
            execution_count=1,
            result=2,
            error_in_exec=None,
            error_before_exec=None,
        )
    )

    content = _read_qmd(output_path)
    assert "```stderr" not in content


# ---------------------------------------------------------------------------
# set_title
# ---------------------------------------------------------------------------


def test_set_title_updates_frontmatter(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(None, output_path, title="old title")
    output_path.write_text('---\ntitle: "old title"\nrecording_started: now\n---\n\n', encoding="utf-8")

    logger.set_title("new title")

    content = _read_qmd(output_path)
    assert 'title: "new title"' in content
    assert "old title" not in content


# ---------------------------------------------------------------------------
# author in frontmatter
# ---------------------------------------------------------------------------


def test_author_appears_in_frontmatter(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(_make_shell(), output_path, author="Jane Doe")

    logger.start()

    content = _read_qmd(output_path)
    assert 'author: "Jane Doe"' in content


def test_no_author_field_when_not_set(tmp_path) -> None:
    output_path = tmp_path / "run.qmd"
    logger = RunLogger(_make_shell(), output_path)

    logger.start()

    content = _read_qmd(output_path)
    assert "author:" not in content


# ---------------------------------------------------------------------------
# _update_frontmatter helper
# ---------------------------------------------------------------------------


def test_update_frontmatter_inserts_new_key(tmp_path) -> None:
    path = tmp_path / "f.qmd"
    path.write_text('---\ntitle: "t"\n---\n\nbody\n', encoding="utf-8")

    _update_frontmatter(path, "recording_stopped", "2026-01-01T00:00:00")

    content = path.read_text(encoding="utf-8")
    assert "recording_stopped: 2026-01-01T00:00:00" in content
    assert "body" in content


def test_update_frontmatter_replaces_existing_key(tmp_path) -> None:
    path = tmp_path / "f.qmd"
    path.write_text('---\ntitle: "old"\n---\n\n', encoding="utf-8")

    _update_frontmatter(path, "title", '"new"')

    content = path.read_text(encoding="utf-8")
    assert 'title: "new"' in content
    assert "old" not in content


def test_update_frontmatter_does_nothing_if_file_missing(tmp_path) -> None:
    path = tmp_path / "nonexistent.qmd"
    # Should not raise
    _update_frontmatter(path, "key", "value")
