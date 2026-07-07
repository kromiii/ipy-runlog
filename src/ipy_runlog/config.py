from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def load_config(cwd: Path) -> dict[str, Any]:
    """Load ipy-runlog config from pyproject.toml or .ipy_runlog.toml.

    Search order:
      1. [tool.ipy-runlog] in pyproject.toml
      2. .ipy_runlog.toml in cwd
    """

    # 1. pyproject.toml
    pyproject = cwd / "pyproject.toml"
    if pyproject.exists():
        try:
            with pyproject.open("rb") as f:
                data = tomllib.load(f)
            config = data.get("tool", {}).get("ipy-runlog", {})
            if config:
                return config
        except Exception:
            pass

    # 2. .ipy_runlog.toml
    fallback = cwd / ".ipy_runlog.toml"
    if fallback.exists():
        try:
            with fallback.open("rb") as f:
                return tomllib.load(f)
        except Exception:
            pass

    return {}
