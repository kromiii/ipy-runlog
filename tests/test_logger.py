import json
from types import SimpleNamespace

from ipy_runlog.logger import RunLogger


def _read_last_event(path):
    return json.loads(path.read_text(encoding="utf-8").splitlines()[-1])


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
