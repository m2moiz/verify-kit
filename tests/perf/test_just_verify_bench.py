# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASE_DATA = {
    "project_name": "PerfScratchBase",
    "project_description": "verify-kit base performance benchmark scratch.",
    "project_slug": "perf-scratch-base",
    "package_name": "perf_scratch_base",
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
    "has_backend": False,
    "has_llm": False,
    "has_logfire": False,
    "has_fastapi_mcp": False,
    "has_db": False,
}


def _render_base_scratch(tmp_path: Path) -> Path:
    scratch = tmp_path / "scratch-base"
    data_file = tmp_path / "copier-base.json"
    data_file.write_text(json.dumps(_BASE_DATA), encoding="utf-8")
    subprocess.run(
        [
            "copier",
            "copy",
            "--trust",
            "--defaults",
            "--data-file",
            str(data_file),
            str(_REPO_ROOT),
            str(scratch),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return scratch


@pytest.mark.benchmark(group="just-verify-base")
def test_just_verify_base_combo(benchmark: Any, tmp_path: Path) -> None:
    scratch = _render_base_scratch(tmp_path)
    env = {
        **os.environ,
        "VERIFYKIT_AUTH_TOKEN": "dev-token-for-tests",
        "ENV": "dev",
    }

    benchmark.pedantic(
        subprocess.run,
        args=(["just", "verify"],),
        kwargs={
            "cwd": scratch,
            "check": True,
            "env": env,
            "capture_output": True,
            "text": True,
        },
        rounds=3,
        iterations=1,
        warmup_rounds=1,
    )
