# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""SC#1 gate: `verify-kit verify --quick --no-cache` reports
``summary.duration_ms < 2000`` on first run in a scratch project.

Separate from ``test_first_run_30s.py`` which times the full
copier+install+verify chain at 30s wall budget. This test isolates the
verify-only internal duration so we catch regressions in check execution
speed without the noise of copier rendering and uv pip install.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests._helpers import install_scratch_harness, render_scratch_project


_BUDGET_MS = 2000


@pytest.mark.slow
@pytest.mark.requires_network
@pytest.mark.skipif(
    not os.environ.get("RUN_SLOW_TESTS"),
    reason="set RUN_SLOW_TESTS=1 to run scratch-render gate tests",
)
def test_verify_quick_first_run_under_2s_internal(tmp_path: Path) -> None:
    scratch = render_scratch_project(tmp_path)
    install_scratch_harness(scratch)

    result = subprocess.run(
        ["uv", "run", "verify-kit", "verify", "--quick", "--no-cache", "--format=json"],
        cwd=scratch,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"verify-kit verify --quick --no-cache failed (exit {result.returncode})\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    report = json.loads(result.stdout)
    duration_ms = report["summary"]["duration_ms"]
    assert duration_ms < _BUDGET_MS, (
        f"verify --quick first-run reported duration_ms={duration_ms} "
        f"(SC#1 hard budget is <{_BUDGET_MS}ms)"
    )
