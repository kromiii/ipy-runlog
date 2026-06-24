# ipy-runlog

A lightweight IPython extension that records code cell execution history as
JSON Lines (JSONL).

## Motivation

Experiments are shaped by failed attempts as well as successful ones.
Recording both preserves the trial-and-error process, giving an experiment
notebook a coherent story instead of showing only its final results.

## Installation

With `pip`:

```bash
pip install ipy-runlog
```

In a `uv` project:

```bash
uv add ipy-runlog
```

## Usage

Load the extension — recording starts automatically:

```python
%load_ext ipy_runlog
```

The log is written to `.ipy_runlog/` in the current working directory. The
file name is generated from the current date and time, for example:

```text
.ipy_runlog/20260611-123456.jsonl
```

Recording stops automatically when the IPython session ends.

### Commands

Check the current status:

```python
%runlog status
```

Switch to a new log file mid-session (closes the current log):

```python
%runlog new experiment-01
%runlog new experiment-01 --output   # also record cell output
%runlog new experiment-01 -d ./logs  # custom output directory
```

Rename the current log file without interrupting recording:

```python
%runlog rename feature-extraction
```

Stop recording manually:

```python
%runlog stop
```

Show help:

```python
%runlog help
%runlog new --help
```

### Configuration

You can set defaults in `pyproject.toml`:

```toml
[tool.ipy-runlog]
directory = "./logs"
output = true
```

Or in `.ipy_runlog.toml` at the project root (used as a fallback when
`pyproject.toml` is absent or has no `[tool.ipy-runlog]` section):

```toml
directory = "./logs"
output = true
```

Available config keys:

| Key         | Type   | Default          | Description                          |
|-------------|--------|------------------|--------------------------------------|
| `directory` | string | `.ipy_runlog/`   | Output directory                     |
| `output`    | bool   | `false`          | Record cell output                   |
| `name`      | string | current timestamp| Default log file name                |

> **Note**: Python 3.11+ uses the built-in `tomllib`. For Python 3.9–3.10,
> install `tomli` to enable config file support: `pip install tomli`.

## How It Works

The extension uses IPython event handlers to monitor cell execution:

- **`pre_run_cell`**: Triggered before a cell is executed. The extension captures the source code of the cell at this point.
- **`post_run_cell`**: Triggered after a cell finishes executing. The extension calculates the elapsed time, determines if it was successful or failed (including error details), and optionally captures the output.

Each event is appended as a single JSON line to the log file. On normal
session exit, a final `recording_stopped` event is written automatically via
`atexit`.

## Log Format

Logs use UTF-8 encoded JSON Lines, with one event per line. New events are
appended when the target file already exists.

Event types:

- `recording_started`: recording started
- `cell_executed`: a cell finished executing
- `recording_renamed`: log file was renamed with `%runlog rename`
- `recording_stopped`: recording stopped (includes `"reason": "session_ended"` on automatic stop)

A `cell_executed` event contains:

- `started_at` and `ended_at`: local timestamps in ISO 8601 format
- `elapsed_sec`: execution time in seconds
- `status`: `success` or `failed`
- `execution_count`: the IPython execution count
- `code`: the cell source code
- `output`: the cell result when `--output` is enabled; non-JSON values are
  stored using `repr()`
- `error`: error type, message, and traceback (always recorded on failure)

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
