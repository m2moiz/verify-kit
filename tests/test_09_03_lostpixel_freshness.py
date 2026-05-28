# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for Plan 09-03, Task 2: Lost Pixel freshness failure (BL-4).

parse_lostpixel_output must yield an ErrorEnvelope (not []) when:
  - comparison-results.json is missing
  - comparison-results.json is malformed (invalid JSON)
  - comparison-results.json has zero executed comparisons (empty list)
  - comparison-results.json is stale (mtime before run_start_time)

The ErrorEnvelope must carry the existing fix_command shape where applicable.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def lostpixel_module(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("lp-scratch"),
        has_web=True,
        _vcs_ref="HEAD",
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        from harness.web import lostpixel_adapter

        yield lostpixel_adapter
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


# ── 1. Missing comparison-results.json → ErrorEnvelope in required mode ──────


def test_missing_artifact_yields_error_envelope(lostpixel_module, tmp_path: Path) -> None:
    """Missing comparison-results.json must yield an ErrorEnvelope (not []) in required mode."""
    lp_dir = tmp_path / ".lost-pixel"
    lp_dir.mkdir()
    # No comparison-results.json written

    run_start = time.time()
    result = lostpixel_module.parse_lostpixel_output(lp_dir, run_start_time=run_start, required=True)
    assert len(result) > 0, "Missing artifact must yield ≥1 ErrorEnvelope in required mode"
    assert any(hasattr(e, "code") for e in result), "Result items must be ErrorEnvelope instances"
    # At least one envelope must reference the missing artifact
    codes = [e.code for e in result]
    assert any("missing" in c.lower() or "not_found" in c.lower() or "no_run" in c.lower() for c in codes), (
        f"ErrorEnvelope codes must indicate missing artifact, got: {codes}"
    )


def test_missing_artifact_not_required_returns_empty(lostpixel_module, tmp_path: Path) -> None:
    """Missing comparison-results.json with required=False (legacy) returns [] — backwards compat."""
    lp_dir = tmp_path / ".lost-pixel"
    lp_dir.mkdir()
    run_start = time.time()
    result = lostpixel_module.parse_lostpixel_output(lp_dir, run_start_time=run_start, required=False)
    assert result == [], "Non-required mode with missing artifact must still return []"


# ── 2. Malformed JSON → ErrorEnvelope ────────────────────────────────────────


def test_malformed_json_yields_error_envelope(lostpixel_module, tmp_path: Path) -> None:
    """Malformed comparison-results.json must yield an ErrorEnvelope (not raise)."""
    lp_dir = tmp_path / ".lost-pixel"
    lp_dir.mkdir()
    (lp_dir / "comparison-results.json").write_text("{ this is not valid json !!!", encoding="utf-8")

    run_start = time.time()
    result = lostpixel_module.parse_lostpixel_output(lp_dir, run_start_time=run_start, required=True)
    assert len(result) > 0, "Malformed JSON must yield ≥1 ErrorEnvelope"
    codes = [e.code for e in result]
    assert any("malform" in c.lower() or "parse" in c.lower() or "invalid" in c.lower() for c in codes), (
        f"ErrorEnvelope codes must indicate malformed JSON, got: {codes}"
    )


# ── 3. Zero executed comparisons → ErrorEnvelope ─────────────────────────────


def test_empty_results_array_yields_error_envelope(lostpixel_module, tmp_path: Path) -> None:
    """comparison-results.json with zero items must yield an ErrorEnvelope in required mode."""
    lp_dir = tmp_path / ".lost-pixel"
    lp_dir.mkdir()
    (lp_dir / "comparison-results.json").write_text("[]", encoding="utf-8")

    run_start = time.time()
    result = lostpixel_module.parse_lostpixel_output(lp_dir, run_start_time=run_start, required=True)
    assert len(result) > 0, "Empty results array must yield ≥1 ErrorEnvelope in required mode"
    codes = [e.code for e in result]
    assert any(
        "empty" in c.lower() or "no_run" in c.lower() or "zero" in c.lower() or "stale" in c.lower()
        for c in codes
    ), f"ErrorEnvelope codes must indicate zero comparisons, got: {codes}"


# ── 4. Stale artifact (mtime before run_start) → ErrorEnvelope ───────────────


def test_stale_artifact_yields_error_envelope(lostpixel_module, tmp_path: Path) -> None:
    """comparison-results.json older than run_start_time must yield an ErrorEnvelope."""
    lp_dir = tmp_path / ".lost-pixel"
    lp_dir.mkdir()

    # Write some non-empty results data
    data = [
        {
            "name": "home",
            "baselinePath": "web/.lost-pixel/baseline/home.png",
            "currentPath": "web/.lost-pixel/current/home.png",
            "diffPath": None,
            "diffPercentage": 0.0,
            "threshold": 0.1,
            "isNew": False,
            "isUpdated": False,
            "isDeleted": False,
        }
    ]
    results_file = lp_dir / "comparison-results.json"
    results_file.write_text(json.dumps(data), encoding="utf-8")

    # run_start is AFTER the file was written → file is stale
    time.sleep(0.01)  # ensure mtime < run_start
    run_start = time.time() + 10  # well into the future = file is stale

    result = lostpixel_module.parse_lostpixel_output(lp_dir, run_start_time=run_start, required=True)
    assert len(result) > 0, "Stale artifact must yield ≥1 ErrorEnvelope in required mode"
    codes = [e.code for e in result]
    assert any("stale" in c.lower() or "outdated" in c.lower() for c in codes), (
        f"ErrorEnvelope codes must indicate stale artifact, got: {codes}"
    )


# ── 5. Fresh valid artifact with diffs → existing behaviour preserved ─────────


def test_fresh_artifact_with_diffs_yields_diff_envelopes(lostpixel_module, tmp_path: Path) -> None:
    """A fresh valid artifact with visual diffs must yield per-diff ErrorEnvelopes (existing behaviour)."""
    lp_dir = tmp_path / ".lost-pixel"
    lp_dir.mkdir()

    data = [
        {
            "name": "home",
            "baselinePath": "web/.lost-pixel/baseline/home.png",
            "currentPath": "web/.lost-pixel/current/home.png",
            "diffPath": "web/.lost-pixel/diff/home.png",
            "diffPercentage": 5.0,
            "threshold": 0.1,
            "isNew": False,
            "isUpdated": True,
            "isDeleted": False,
        }
    ]
    results_file = lp_dir / "comparison-results.json"
    results_file.write_text(json.dumps(data), encoding="utf-8")

    # run_start BEFORE the file was written → file is fresh
    run_start = time.time() - 10

    result = lostpixel_module.parse_lostpixel_output(lp_dir, run_start_time=run_start, required=True)
    assert len(result) == 1, "Fresh artifact with 1 diff must yield 1 ErrorEnvelope"
    assert result[0].code == "web.lost_pixel.diff.home"


# ── 6. Fresh valid clean run → empty list in required mode ───────────────────


def test_fresh_artifact_clean_run_yields_empty(lostpixel_module, tmp_path: Path) -> None:
    """A fresh artifact where all snapshots match yields [] (no errors)."""
    lp_dir = tmp_path / ".lost-pixel"
    lp_dir.mkdir()

    data = [
        {
            "name": "home",
            "baselinePath": "web/.lost-pixel/baseline/home.png",
            "currentPath": "web/.lost-pixel/current/home.png",
            "diffPath": None,
            "diffPercentage": 0.0,
            "threshold": 0.1,
            "isNew": False,
            "isUpdated": False,
            "isDeleted": False,
        }
    ]
    results_file = lp_dir / "comparison-results.json"
    results_file.write_text(json.dumps(data), encoding="utf-8")

    run_start = time.time() - 10  # run started before file was written → file is fresh

    result = lostpixel_module.parse_lostpixel_output(lp_dir, run_start_time=run_start, required=True)
    assert result == [], "Fresh clean run must yield no ErrorEnvelopes"
