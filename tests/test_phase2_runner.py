# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.runner (Plan 02-04, Task 3).

Covers:
- run_check returns pass for a registered passing check
- run_check returns fail+ErrorEnvelope when fn raises (.unhandled suffix)
- run_check cache hit short-circuits spec.fn (cached=True, mock counter)
- run_check writes to cache on miss
- run_phase respects config.checks.disabled
- carryover-cwd: run_check from a different process cwd still hands the
  intended `cwd` to the check function AND its subprocess
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def runner_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("runner-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.runner as runner
        import harness.registry as registry
        import harness.models as models
        import harness.cache as cache_mod
        import harness.config as config_mod

        yield runner, registry, models, cache_mod, config_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _reset_registry(registry):
    registry._checks.clear()


def test_run_check_pass(runner_modules, tmp_path: Path) -> None:
    runner, registry, models, _, _ = runner_modules
    _reset_registry(registry)

    @registry.register("test.simple.pass", tier="quick", category="test")
    def _passing(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="test.simple.pass", status="pass", duration_ms=1)

    spec = registry.get_check("test.simple.pass")
    result = runner.run_check(spec, cwd=tmp_path)
    assert result.status == "pass"
    assert result.check_id == "test.simple.pass"


def test_run_check_catches_exceptions(runner_modules, tmp_path: Path) -> None:
    runner, registry, models, _, _ = runner_modules
    _reset_registry(registry)

    @registry.register("test.simple.crash")
    def _crashing(cwd: Path) -> models.CheckResult:
        raise RuntimeError("boom")

    spec = registry.get_check("test.simple.crash")
    result = runner.run_check(spec, cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code.endswith(".unhandled")
    assert result.error.code == "test.simple.crash.unhandled"


def test_run_check_cache_hit(runner_modules, tmp_path: Path) -> None:
    runner, registry, models, cache_mod, _ = runner_modules
    _reset_registry(registry)

    counter = {"n": 0}

    @registry.register(
        "test.cache.demo",
        tier="quick",
        category="test",
        inputs=["something.txt"],
    )
    def _check(cwd: Path) -> models.CheckResult:
        counter["n"] += 1
        return models.CheckResult(check_id="test.cache.demo", status="pass", duration_ms=5)

    # Create the input file so hash_inputs is stable
    (tmp_path / "something.txt").write_text("hello")
    spec = registry.get_check("test.cache.demo")
    cache = cache_mod.CacheStore(tmp_path / ".verify" / "cache.db")

    r1 = runner.run_check(spec, cwd=tmp_path, cache=cache)
    assert r1.status == "pass"
    assert counter["n"] == 1

    r2 = runner.run_check(spec, cwd=tmp_path, cache=cache)
    assert r2.status == "pass"
    assert r2.cached is True
    assert counter["n"] == 1  # fn was NOT called a second time


def test_run_phase_respects_disabled(runner_modules, tmp_path: Path) -> None:
    runner, registry, models, _, config_mod = runner_modules
    _reset_registry(registry)

    @registry.register("test.phase.one")
    def _one(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="test.phase.one", status="pass")

    @registry.register("test.phase.two")
    def _two(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="test.phase.two", status="pass")

    config = config_mod.HarnessConfig(
        checks=config_mod.ChecksConfig(disabled=["test.phase.two"])
    )
    results = runner.run_phase(
        registry.list_checks(), cwd=tmp_path, cache=None, config=config
    )
    ids = [r.check_id for r in results]
    assert "test.phase.one" in ids
    assert "test.phase.two" not in ids


def test_run_phase_returns_list_in_registration_order(
    runner_modules, tmp_path: Path
) -> None:
    runner, registry, models, _, _ = runner_modules
    _reset_registry(registry)

    @registry.register("a.first")
    def _a(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="a.first", status="pass")

    @registry.register("b.second")
    def _b(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="b.second", status="pass")

    @registry.register("c.third")
    def _c(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="c.third", status="pass")

    results = runner.run_phase(registry.list_checks(), cwd=tmp_path)
    assert [r.check_id for r in results] == ["a.first", "b.second", "c.third"]


def test_run_check_propagates_cwd_to_check_and_subprocess(
    runner_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Carryover-cwd verification (f): cwd flows end-to-end.

    1. Test process is in a DIFFERENT cwd than tmp_path.
    2. Register a check whose body asserts cwd==tmp_path AND runs `pwd` via
       subprocess.run(cwd=cwd, ...).
    3. Invoke run_check(spec, cwd=tmp_path).
    4. Returned message contains str(tmp_path) (subprocess actually saw it).
    """
    runner, registry, models, _, _ = runner_modules
    _reset_registry(registry)

    other_dir = tmp_path.parent / "elsewhere"
    other_dir.mkdir(exist_ok=True)
    monkeypatch.chdir(other_dir)

    expected = tmp_path.resolve()

    @registry.register("test.cwd.probe")
    def _probe(cwd: Path) -> models.CheckResult:
        assert cwd.resolve() == expected, f"check fn received cwd={cwd}, expected {expected}"
        proc = subprocess.run(
            ["pwd"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return models.CheckResult(
            check_id="test.cwd.probe",
            status="pass",
            message=proc.stdout.strip(),
        )

    spec = registry.get_check("test.cwd.probe")
    result = runner.run_check(spec, cwd=tmp_path)
    assert result.status == "pass"
    # macOS may resolve /var/folders → /private/var/folders; compare resolved
    assert Path(result.message).resolve() == expected


def test_run_check_writes_through_to_cache(runner_modules, tmp_path: Path) -> None:
    """First call writes to cache; second call returns cached=True."""
    runner, registry, models, cache_mod, _ = runner_modules
    _reset_registry(registry)

    @registry.register("test.writethrough", inputs=["x.txt"])
    def _check(cwd: Path) -> models.CheckResult:
        return models.CheckResult(check_id="test.writethrough", status="pass")

    (tmp_path / "x.txt").write_text("v1")
    spec = registry.get_check("test.writethrough")
    cache = cache_mod.CacheStore(tmp_path / ".verify" / "cache.db")
    r1 = runner.run_check(spec, cwd=tmp_path, cache=cache)
    assert r1.cached is False
    r2 = runner.run_check(spec, cwd=tmp_path, cache=cache)
    assert r2.cached is True
