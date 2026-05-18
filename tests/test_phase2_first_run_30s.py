"""UX-08 verification gate: end-to-end first run completes in <30 seconds.

Reflects UX-08: "from copier copy to I see my project verified" on a
machine where ``mise``+``just`` are preinstalled (which our CI image
provides). Dev machines may exceed 30s on first dependency download —
this test is meaningful in CI with caches warm.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from tests._helpers import install_scratch_harness, render_scratch_project


_BUDGET_S = 30.0


@pytest.mark.slow
@pytest.mark.requires_network
@pytest.mark.skipif(
    not os.environ.get("RUN_SLOW_TESTS"),
    reason="set RUN_SLOW_TESTS=1 to run scratch-render gate tests",
)
def test_first_run_under_30_seconds(tmp_path: Path) -> None:
    """copier copy → uv pip install -e . → just verify --quick in <30s wall."""
    t0 = time.perf_counter()

    scratch = render_scratch_project(tmp_path)
    install_scratch_harness(scratch)

    result = subprocess.run(
        ["just", "verify", "--quick"],
        cwd=scratch,
        capture_output=True,
        text=True,
        timeout=60,
    )
    elapsed = time.perf_counter() - t0

    assert result.returncode == 0, (
        f"just verify --quick failed (exit {result.returncode})\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert elapsed < _BUDGET_S, (
        f"first-run elapsed {elapsed:.2f}s exceeded UX-08 budget {_BUDGET_S}s"
    )
