# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_FULL_DATA = {
    "project_name": "PerfScratchFull",
    "project_description": "verify-kit full performance benchmark scratch.",
    "project_slug": "perf-scratch-full",
    "package_name": "perf_scratch_full",
    "author_name": "verify-kit CI",
    "author_email": "ci@verify-kit.example",
    "license": "MIT",
    "has_claude_code": False,
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    "has_devcontainer": False,
    "llm_backend": "langfuse-cloud",
    "has_backend": True,
    "has_llm": True,
    "has_logfire": True,
    "has_fastapi_mcp": True,
    "has_db": True,
}


def _copy_full(data_file: Path, dst: Path) -> None:
    subprocess.run(
        [
            "copier",
            "copy",
            "--trust",
            "--defaults",
            "--data-file",
            str(data_file),
            str(_REPO_ROOT),
            str(dst),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.benchmark(group="copier-render-full")
def test_copier_copy_full_combo(benchmark: Any, tmp_path: Path) -> None:
    data_file = tmp_path / "copier-full.json"
    data_file.write_text(json.dumps(_FULL_DATA), encoding="utf-8")

    counter = 0

    def render_once() -> None:
        nonlocal counter
        counter += 1
        _copy_full(data_file, tmp_path / f"scratch-full-{counter}")

    benchmark.pedantic(
        render_once,
        rounds=3,
        iterations=1,
        warmup_rounds=1,
    )
