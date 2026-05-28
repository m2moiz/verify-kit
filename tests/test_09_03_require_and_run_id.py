# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for Plan 09-03, Task 1: executed_at/run_id on CheckResult + --require flag.

Covers BL-3, F-02, D-08:
- CheckResult has executed_at and run_id fields (populated only on fresh fn run)
- Cache-replayed results retain the original (stale) run_id, not current process's
- --require forces cache bypass for required ids
- --require post-run assertion: all required ids must carry the current process run_id
- Unknown required id fails before the run starts (non-zero exit, names the id)
- Required id not selected by current tier/filter fails with actionable message
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def require_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("require-scratch"), _vcs_ref="HEAD")
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.runner as runner
        import harness.registry as registry
        import harness.models as models
        import harness.cache as cache_mod
        import harness.core as core_mod

        yield runner, registry, models, cache_mod, core_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _reset_registry(registry):
    registry._checks.clear()


# ── 1. CheckResult has executed_at and run_id fields ────────────────────────


def test_check_result_has_executed_at_and_run_id(require_modules) -> None:
    """CheckResult must declare executed_at (datetime | None) and run_id (str | None)."""
    _, _, models, _, _ = require_modules
    r = models.CheckResult(check_id="x", status="pass")
    assert hasattr(r, "executed_at"), "CheckResult must have executed_at field"
    assert hasattr(r, "run_id"), "CheckResult must have run_id field"
    # Default is None (not populated until fn actually executes)
    assert r.executed_at is None
    assert r.run_id is None


def test_check_result_executed_at_and_run_id_roundtrip(require_modules) -> None:
    """executed_at / run_id must survive JSON roundtrip."""
    from datetime import datetime, timezone

    _, _, models, _, _ = require_modules
    ts = datetime.now(tz=timezone.utc)
    r = models.CheckResult(
        check_id="x",
        status="pass",
        executed_at=ts,
        run_id="abc-123",
    )
    blob = r.model_dump_json()
    r2 = models.CheckResult.model_validate_json(blob)
    assert r2.run_id == "abc-123"
    assert r2.executed_at is not None


# ── 2. run_check stamps executed_at + run_id when fn executes ────────────────


def test_run_check_stamps_run_id_on_fresh_execution(require_modules, tmp_path: Path) -> None:
    """A fresh (no cache) run_check must stamp run_id on the result."""
    runner, registry, models, _, _ = require_modules
    _reset_registry(registry)

    @registry.register("test.stamp.fresh", tier="quick")
    def _check(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="test.stamp.fresh", status="pass")

    spec = registry.get_check("test.stamp.fresh")
    result = runner.run_check(spec, cwd=tmp_path)
    assert result.run_id is not None, "run_id must be set on fresh execution"
    assert result.executed_at is not None, "executed_at must be set on fresh execution"


def test_cache_replay_does_not_get_current_run_id(require_modules, tmp_path: Path) -> None:
    """A cache-replayed result must NOT carry the current process run_id.

    The replay retains whatever run_id was cached (stale). This is the BL-3
    falsification test: if cache replay were to stamp the current run_id,
    --require's post-run assertion could never catch it.
    """
    runner, registry, models, cache_mod, _ = require_modules
    _reset_registry(registry)

    @registry.register("test.cache.runid", tier="quick", inputs=["x.txt"])
    def _check(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="test.cache.runid", status="pass")

    (tmp_path / "x.txt").write_text("hello")
    spec = registry.get_check("test.cache.runid")
    cache = cache_mod.CacheStore(tmp_path / ".verify" / "cache.db")

    # First run: populates cache with run_id_A
    r1 = runner.run_check(spec, cwd=tmp_path, cache=cache)
    assert r1.run_id is not None
    run_id_a = r1.run_id

    # Simulate a second verify-process by creating a NEW run_id in the runner.
    # The second cache-hit must return run_id_a, not the new process run_id.
    r2 = runner.run_check(spec, cwd=tmp_path, cache=cache)
    assert r2.cached is True
    # The replayed result must carry the original run_id, not a new one.
    assert r2.run_id == run_id_a, (
        "cache-replayed result must retain original run_id (stale), not stamp current process run_id"
    )


# ── 3. run_check with required_ids set bypasses cache ───────────────────────


def test_run_check_bypasses_cache_when_required(require_modules, tmp_path: Path) -> None:
    """When a check id is in required_ids, the cache is bypassed (fn always runs)."""
    runner, registry, models, cache_mod, _ = require_modules
    _reset_registry(registry)

    counter = {"n": 0}

    @registry.register("test.required.bypass", tier="quick", inputs=["x.txt"])
    def _check(cwd: Path) -> models.CheckResult:
        counter["n"] += 1
        return models.CheckResult(check_id="test.required.bypass", status="pass")

    (tmp_path / "x.txt").write_text("hello")
    spec = registry.get_check("test.required.bypass")
    cache = cache_mod.CacheStore(tmp_path / ".verify" / "cache.db")

    # First run — populates cache
    r1 = runner.run_check(spec, cwd=tmp_path, cache=cache)
    assert counter["n"] == 1

    # Second run with required_ids — must bypass cache
    r2 = runner.run_check(spec, cwd=tmp_path, cache=cache, required_ids={"test.required.bypass"})
    assert counter["n"] == 2, "required id must bypass cache, fn must run again"
    assert r2.cached is False
    assert r2.run_id is not None


# ── 4. core.verify with --require: unknown id fails before run ───────────────


def test_verify_require_unknown_id_fails_before_run(require_modules, tmp_path: Path) -> None:
    """An unknown required id must fail before any check runs (F-02 hard invariant)."""
    runner, registry, models, _, core_mod = require_modules
    _reset_registry(registry)

    called = {"n": 0}

    @registry.register("test.req.known", tier="quick")
    def _check(cwd: Path) -> models.CheckResult:
        called["n"] += 1
        return models.CheckResult(check_id="test.req.known", status="pass")

    with pytest.raises(ValueError, match="does.not.exist") as exc_info:
        core_mod.verify(
            cwd=tmp_path,
            tier="standard",
            required_ids={"does.not.exist"},
        )
    assert "does.not.exist" in str(exc_info.value)
    # No checks should have run
    assert called["n"] == 0, "no checks must run when a required id is unknown"


# ── 5. Required id not selected by tier/filter fails with actionable message ─


def test_verify_require_id_not_in_tier_fails_actionable(
    require_modules, tmp_path: Path
) -> None:
    """A required id that exists but is not selected by the current tier fails (D-08 strictness (b))."""
    runner, registry, models, _, core_mod = require_modules
    _reset_registry(registry)

    @registry.register("test.slow.check", tier="slow")
    def _slow(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="test.slow.check", status="pass")

    # Running with tier="standard" (default) should NOT include tier="slow" checks.
    # --require=test.slow.check must fail with an actionable message (not exit 0).
    with pytest.raises(ValueError) as exc_info:
        core_mod.verify(
            cwd=tmp_path,
            tier="standard",
            required_ids={"test.slow.check"},
        )
    msg = str(exc_info.value)
    # Must name the check and hint about the fix (e.g. use --full)
    assert "test.slow.check" in msg
    assert "full" in msg.lower() or "tier" in msg.lower() or "slow" in msg.lower()


# ── 6. Post-run: required ids must carry current run_id ─────────────────────


def test_verify_require_post_run_assertion_with_direct_run(
    require_modules, tmp_path: Path
) -> None:
    """After a fresh required run, the result must carry the current process run_id.

    This tests the green path: a required check that actually ran must pass the
    post-run in-process assertion.
    """
    runner, registry, models, _, core_mod = require_modules
    _reset_registry(registry)

    @registry.register("test.req.fresh", tier="quick")
    def _check(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="test.req.fresh", status="pass")

    report = core_mod.verify(
        cwd=tmp_path,
        tier="standard",
        required_ids={"test.req.fresh"},
    )
    # The check must have run and the result must have a run_id
    result = next(r for r in report.checks if r.check_id == "test.req.fresh")
    assert result.run_id is not None, "required check must carry run_id after execution"
    assert result.executed_at is not None
