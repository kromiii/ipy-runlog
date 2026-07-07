# ipy-runlog

A lightweight IPython extension that records code cell execution history as
[Quarto Markdown (QMD)](https://quarto.org/).

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
.ipy_runlog/20260611-123456.qmd
```

Recording stops automatically when the IPython session ends.

### Commands

Check the current status:

```python
%runlog status
```

Switch to a new log file mid-session (closes the current log):

```python
%runlog new "My Analysis Session"        # title + derived filename: my-analysis-session.qmd
%runlog new "Feature Extraction" -d ./logs  # custom output directory
```

Update the title in the current log's frontmatter without interrupting recording:

```python
%runlog title "My Analysis Session"
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
author = "Jane Doe"
```

Or in `.ipy_runlog.toml` at the project root (used as a fallback when
`pyproject.toml` is absent or has no `[tool.ipy-runlog]` section):

```toml
directory = "./logs"
author = "Jane Doe"
```

Available config keys:

| Key         | Type   | Default           | Description                          |
|-------------|--------|-------------------|--------------------------------------|
| `directory` | string | `.ipy_runlog/`    | Output directory                     |
| `author`    | string | *(none)*          | Author written into the QMD frontmatter |

> **Note**: Python 3.11+ uses the built-in `tomllib`. For Python 3.9–3.10,
> install `tomli` to enable config file support: `pip install tomli`.

## How It Works

The extension uses IPython event handlers to monitor cell execution:

- **`pre_run_cell`**: Triggered before a cell is executed. The extension captures the source code of the cell at this point.
- **`post_run_cell`**: Triggered after a cell finishes executing. The extension calculates the elapsed time and determines if it was successful or failed (including error details).

Each cell is appended to the QMD file as an HTML comment with execution
metadata followed by a fenced Python code block. Errors are recorded in a
fenced `stderr` block.

## Log Format

Logs are UTF-8 encoded [Quarto Markdown](https://quarto.org/) files. Each
file begins with a YAML frontmatter block:

```yaml
---
title: "My Session"
author: "Jane Doe"
date: 2026-06-11T12:34:56.789012
---
```

Each cell execution is recorded as:

````qmd
<!-- cell: started=2026-06-11T12:35:00.000000, ended=2026-06-11T12:35:00.012000, status=success, elapsed=0.012s -->
```python
x = 1 + 1
```

<!-- cell: started=2026-06-11T12:36:00.000000, ended=2026-06-11T12:36:00.005000, status=failed, elapsed=0.005s -->
```python
print(undefined_variable)
```

```stderr
Traceback (most recent call last):
  ...
NameError: name 'undefined_variable' is not defined
```

````

> **Planned feature**: Capturing cell output (stdout and rich display objects)
> is planned for a future release. The focus of the current version is on
> recording code and errors as a lightweight audit trail.

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
