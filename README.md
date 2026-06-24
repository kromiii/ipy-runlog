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

Load the extension in Jupyter Notebook, JupyterLab, or IPython, then start
recording:

```python
%load_ext ipy_runlog
%runlog start
```

By default, the log is written to `.ipy_runlog/` in the current working
directory. The file name is generated from the current date and time, for
example:

```text
.ipy_runlog/20260611-123456.jsonl
```

Check the current status or stop recording with:

```python
%runlog status
%runlog stop
```

### Options

Pass a name to `%runlog start` to choose the log file name. The `.jsonl`
extension is added automatically when omitted:

```python
%runlog start experiment-01
```

Use `-d` to change the output directory:

```python
%runlog start experiment-01 -d ./logs
```

Cell outputs are not recorded by default. Enable them with `--output`:

```python
%runlog start experiment-01 --output
```

Execution errors are always recorded. Run the following for the complete option
list:

```python
%runlog start --help
```

## How It Works

The extension uses IPython event handlers to monitor cell execution:

- **`pre_run_cell`**: Triggered before a cell is executed. The extension captures the source code of the cell at this point.
- **`post_run_cell`**: Triggered after a cell finishes executing. The extension calculates the elapsed time, determines if it was successful or failed (including error details), and optionally captures the output.

Each event is appended as a single JSON line to the log file.

## Log Format

Logs use UTF-8 encoded JSON Lines, with one event per line. New events are
appended when the target file already exists.

Event types:

- `recording_started`: recording started
- `cell_executed`: a cell finished executing
- `recording_stopped`: recording stopped

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
