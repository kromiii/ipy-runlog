import json
from types import SimpleNamespace

from ipy_runlog.logger import RunLogger


def _read_events(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _read_last_event(path) -> dict:
    return _read_events(path)[-1]


def _make_shell():
    return SimpleNamespace(events=SimpleNamespace(register=lambda *a: None, unregister=lambda *a: None))


def test_start_and_stop_record_recording_lifecycle_events(tmp_path) -> None:
    output_path = tmp_path / "run.jsonl"
    logger = RunLogger(_make_shell(), output_path)

    logger.start()
    assert _read_last_event(output_path)["event"] == "recording_started"

    logger.stop()
    assert _read_last_event(output_path)["event"] == "recording_stopped"


def test_stop_writes_stopped_event_without_reason(tmp_path) -> None:
    output_path = tmp_path / "run.jsonl"
    logger = RunLogger(_make_shell(), output_path)
    logger.start()

    logger.stop()

    event = _read_last_event(output_path)
    assert event["event"] == "recording_stopped"
    assert "reason" not in event


def test_on_exit_writes_stopped_event_with_session_ended_reason(tmp_path) -> None:
    output_path = tmp_path / "run.jsonl"
    logger = RunLogger(_make_shell(), output_path)
    logger.start()

    logger._on_exit()

    event = _read_last_event(output_path)
    assert event["event"] == "recording_stopped"
    assert event["reason"] == "session_ended"


def test_on_exit_is_idempotent_after_stop(tmp_path) -> None:
    output_path = tmp_path / "run.jsonl"
    logger = RunLogger(_make_shell(), output_path)
    logger.start()
    logger.stop()

    # _on_exit should do nothing since _active is already False
    logger._on_exit()

    events = _read_events(output_path)
    assert sum(1 for e in events if e["event"] == "recording_stopped") == 1


def test_rename_moves_file_and_updates_path(tmp_path) -> None:
    output_path = tmp_path / "old.jsonl"
    logger = RunLogger(None, output_path)
    logger._active = True
    output_path.write_text('{"event":"recording_started"}\n', encoding="utf-8")

    logger.rename("newname")

    assert not output_path.exists()
    assert logger.output_path == tmp_path / "newname.jsonl"
    assert logger.output_path.exists()
    events = _read_events(logger.output_path)
    assert events[-1]["event"] == "recording_renamed"


def test_rename_adds_jsonl_extension_if_missing(tmp_path) -> None:
    output_path = tmp_path / "old.jsonl"
    output_path.write_text("", encoding="utf-8")
    logger = RunLogger(None, output_path)
    logger._active = True

    logger.rename("newname")

    assert logger.output_path.suffix == ".jsonl"


def test_rename_preserves_existing_jsonl_extension(tmp_path) -> None:
    output_path = tmp_path / "old.jsonl"
    output_path.write_text("", encoding="utf-8")
    logger = RunLogger(None, output_path)
    logger._active = True

    logger.rename("newname.jsonl")

    assert logger.output_path.name == "newname.jsonl"


def test_cell_event_records_code_and_error_by_default(tmp_path) -> None:
    output_path = tmp_path / "run.jsonl"
    logger = RunLogger(None, output_path)
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

    event = _read_last_event(output_path)
    assert event["code"] == "raise ValueError()"
    assert event["error"]["type"] == "ValueError"
    assert "output" not in event


def test_cell_event_can_record_output_and_omit_error(tmp_path) -> None:
    output_path = tmp_path / "run.jsonl"
    logger = RunLogger(None, output_path, record_output=True, record_error=False)

    logger._on_pre_run_cell(SimpleNamespace(raw_cell="{'answer': 42}"))
    logger._on_post_run_cell(
        SimpleNamespace(
            execution_count=2,
            result={"answer": 42},
            error_in_exec=None,
            error_before_exec=None,
        )
    )

    event = _read_last_event(output_path)
    assert event["output"] == {"answer": 42}
    assert "error" not in event


def test_non_json_output_is_recorded_as_repr(tmp_path) -> None:
    output_path = tmp_path / "run.jsonl"
    logger = RunLogger(None, output_path, record_output=True)

    logger._on_pre_run_cell(SimpleNamespace(raw_cell="{1, 2}"))
    logger._on_post_run_cell(
        SimpleNamespace(
            execution_count=3,
            result={1, 2},
            error_in_exec=None,
            error_before_exec=None,
        )
    )

    event = _read_last_event(output_path)
    assert event["output"] == "{1, 2}"
