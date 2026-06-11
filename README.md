# ipy-auditlog

A lightweight IPython extension that records code cell execution history as
JSON Lines (JSONL).

## Installation

With `pip`:

```bash
pip install ipy-auditlog
```

In a `uv` project:

```bash
uv add ipy-auditlog
```

## Usage

Load the extension in Jupyter Notebook, JupyterLab, or IPython, then start
recording:

```python
%load_ext ipy_auditlog
%auditlog_start
```

By default, the log is written to `.ipy_audit/` in the current working
directory. The file name is generated from the current date and time, for
example:

```text
.ipy_audit/20260611-123456.jsonl
```

Check the current status or stop recording with:

```python
%auditlog_status
%auditlog_stop
```

### Options

Pass a name to `%auditlog_start` to choose the log file name. The `.jsonl`
extension is added automatically when omitted:

```python
%auditlog_start experiment-01
```

Use `--directory` (or `-d`) to change the output directory:

```python
%auditlog_start experiment-01 --directory ./logs
```

Cell outputs are not recorded by default. Enable them with `--with-output`:

```python
%auditlog_start experiment-01 --with-output
```

Execution errors are recorded by default. Disable error details with
`--no-error`.

Run the following command for the complete option list:

```python
%auditlog_start --help
```

## Log Format

Logs use UTF-8 encoded JSON Lines, with one event per line. New events are
appended when the target file already exists.

Event types:

- `audit_started`: recording started
- `cell_executed`: a cell finished executing
- `audit_stopped`: recording stopped

A `cell_executed` event contains:

- `started_at` and `ended_at`: local timestamps in ISO 8601 format
- `elapsed_sec`: execution time in seconds
- `status`: `success` or `failed`
- `execution_count`: the IPython execution count
- `code`: the cell source code
- `output`: the cell result when `--with-output` is enabled; non-JSON values are
  stored using `repr()`
- `error`: error type, message, and traceback when error recording is enabled

## Development

Install this repository in editable mode:

```bash
python -m pip install -e .
```

With `uv`:

```bash
uv pip install -e .
```

Run the test suite:

```bash
uv run pytest
```
