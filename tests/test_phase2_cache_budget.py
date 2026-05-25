# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""TOOL-05 verification gate: second-run verify completes in <500ms.

Two-tier gate (per Plan 02-07 contract, review HIGH-4):

- HARD gate: ``report.summary.duration_ms < 500`` — internal timing that
  measures check execution + cache lookup overhead only. The cache is what
  TOOL-05 is gating, and this is what proves it.
- SOFT gate: subprocess wall-clock < 1500ms — advisory; ``uv run`` cold
  imports alone can blow this on slow machines / cold CI. Logged as a
  warning unless ``VERIFY_KIT_STRICT_WALL_CLOCK=1`` is set.

Additional sub-test (Decision 2.3): a failed check must also be cached —
second run must still report ``cached == True`` for the failing check AND
``duration_ms < 500``.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import warnings
from pathlib import Path

import pytest

from tests._helpers import render_and_install


_HARD_BUDGET_MS = 500
_SOFT_BUDGET_S = 1.5


def _run_verify_json(scratch: Path) -> tuple[dict, float]:
    """Run ``verify-kit verify --quick --format=json``; return (report_dict, wall_s)."""
    # Call the venv's verify-kit console script directly (no `uv run` re-sync).
    verify_kit = scratch / ".venv" / "bin" / "verify-kit"
    t0 = time.perf_counter()
    result = subprocess.run(
        [str(verify_kit), "verify", "--quick", "--format=json"],
        cwd=scratch,
        capture_output=True,
        text=True,
        timeout=120,
    )
    wall_s = time.perf_counter() - t0
    # exit 0 (pass) or 1 (fail) both produce JSON.
    assert result.stdout.strip(), (
        f"empty stdout (exit {result.returncode})\nSTDERR:\n{result.stderr}"
    )
    report = json.loads(result.stdout)
    return report, wall_s


def _assert_wall_clock_soft(wall_s: float) -> None:
    """Soft gate: warn (or fail under strict env) if wall clock > 1.5s."""
    if wall_s < _SOFT_BUDGET_S:
        return
    msg = (
        f"subprocess wall clock {wall_s:.3f}s exceeded soft budget "
        f"{_SOFT_BUDGET_S}s (advisory only)"
    )
    if os.environ.get("VERIFY_KIT_STRICT_WALL_CLOCK"):
        pytest.fail(msg + " — VERIFY_KIT_STRICT_WALL_CLOCK=1 is set")
    warnings.warn(msg, stacklevel=2)


@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("RUN_SLOW_TESTS"),
    reason="set RUN_SLOW_TESTS=1 to run scratch-render gate tests",
)
def test_cache_hit_under_500ms_internal_duration(tmp_path: Path) -> None:
    """Second `verify --quick` run is fully cached and internal duration < 500ms."""
    scratch = render_and_install(tmp_path)

    # Warm-up run populates the cache.
    warm_report, _ = _run_verify_json(scratch)
    assert isinstance(warm_report, dict)

    # Second run — should hit cache for every check.
    cached_report, wall_s = _run_verify_json(scratch)

    # HARD gate: every check is cached.
    statuses = [(c["check_id"], c.get("cached")) for c in cached_report["checks"]]
    uncached = [cid for cid, c in statuses if not c]
    assert not uncached, f"expected all checks to be cached on 2nd run; got uncached={uncached}"

    # HARD gate: internal duration < 500ms.
    duration_ms = cached_report["summary"]["duration_ms"]
    assert duration_ms < _HARD_BUDGET_MS, (
        f"cached internal duration {duration_ms}ms exceeded hard budget "
        f"{_HARD_BUDGET_MS}ms"
    )

    # SOFT gate (wall clock) — advisory only.
    _assert_wall_clock_soft(wall_s)


@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("RUN_SLOW_TESTS"),
    reason="set RUN_SLOW_TESTS=1 to run scratch-render gate tests",
)
def test_failed_check_is_also_cached(tmp_path: Path) -> None:
    """Decision 2.3 — failed checks cache, second run still has cached=True + <500ms."""
    scratch = render_and_install(tmp_path)

    # Induce a check failure: write a corrupt .mise.toml.
    mise = scratch / ".mise.toml"
    mise.write_text("this is not valid toml === ===\n[ broken")

    # Warm-up: populates cache (will include the failed mise check).
    _run_verify_json(scratch)

    # Second run: same corrupt mise — must still hit cache.
    cached_report, _ = _run_verify_json(scratch)

    # Every check (failing or otherwise) must be cached.
    uncached = [c["check_id"] for c in cached_report["checks"] if not c.get("cached")]
    assert not uncached, (
        f"expected ALL checks to be cached on 2nd run (incl. failing); "
        f"got uncached={uncached}"
    )
    duration_ms = cached_report["summary"]["duration_ms"]
    assert duration_ms < _HARD_BUDGET_MS, (
        f"cached internal duration with failing check {duration_ms}ms exceeded "
        f"hard budget {_HARD_BUDGET_MS}ms"
    )
