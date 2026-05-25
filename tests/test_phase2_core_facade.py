# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.core thin facade (Plan 02-06, Task 1).

Covers Plan 02-06 behavior requirements:
    (a) harness.verify() returns a VerifyReport with summary populated
    (b) tier="quick" filters to quick specs only
    (c) unknown check_id raises ValueError with did-you-mean suggestion text
    (d) no_cache=True does not create .verify/cache.db
    (e) list_checks() returns list of strings (Phase-1 signature preserved)
    (f) cache.evict_if_needed is called BEFORE return (not as dead code after)
    (g) core.verify(cwd=tmp_path) reads tmp_path/pyproject.toml, not the
        process-CWD pyproject (cwd contract — convergence HIGH)
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def core_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("core-facade-scratch"))
    sys.path.insert(0, str(scratch))
    # Wipe any previously-imported harness.* so we re-resolve against scratch.
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness as harness_pkg
        import harness.core as core
        import harness.models as models
        import harness.registry as registry
        import harness.cache as cache_mod
        import harness.config as config_mod

        yield {
            "scratch": scratch,
            "harness": harness_pkg,
            "core": core,
            "models": models,
            "registry": registry,
            "cache": cache_mod,
            "config": config_mod,
        }
    finally:
        sys.path.remove(str(scratch))


def _make_scratch_cwd(tmp_path: Path) -> Path:
    """Create a tmp project root with .mise.toml and .copier-answers.yml present
    so the migrated Phase-1 checks have something to read."""
    (tmp_path / ".mise.toml").write_text(
        '[tools]\npython = "3.13"\nnode = "20"\n', encoding="utf-8"
    )
    (tmp_path / ".copier-answers.yml").write_text(
        "_src_path: file:///fake\n", encoding="utf-8"
    )
    return tmp_path


# ── (a) returns VerifyReport with summary ────────────────────────────────────


def test_verify_returns_report_with_summary(core_modules, tmp_path: Path):
    core = core_modules["core"]
    VerifyReport = core_modules["models"].VerifyReport
    cwd = _make_scratch_cwd(tmp_path)

    report = core.verify(cwd=cwd, no_cache=True, tier="quick")

    assert isinstance(report, VerifyReport)
    assert report.summary is not None
    assert report.summary.total == len(report.checks)


# ── (b) tier="quick" filters to quick specs ──────────────────────────────────


def test_verify_tier_quick_filters(core_modules, tmp_path: Path):
    core = core_modules["core"]
    registry = core_modules["registry"]
    cwd = _make_scratch_cwd(tmp_path)

    # Sanity: registry has both quick and standard tier specs.
    all_specs = registry.list_checks()
    quick_ids = {s.check_id for s in all_specs if s.tier == "quick"}
    assert quick_ids, "Test precondition: registry should have ≥1 quick spec"

    report = core.verify(cwd=cwd, no_cache=True, tier="quick")
    result_ids = {c.check_id for c in report.checks}
    # Every result id must be a quick spec; no standard/slow leakage.
    assert result_ids.issubset(quick_ids)


def test_verify_tier_full_includes_all(core_modules, tmp_path: Path):
    core = core_modules["core"]
    registry = core_modules["registry"]
    cwd = _make_scratch_cwd(tmp_path)

    all_ids = {s.check_id for s in registry.list_checks()}
    report = core.verify(cwd=cwd, no_cache=True, tier="full")
    result_ids = {c.check_id for c in report.checks}
    assert result_ids == all_ids


def test_verify_unknown_tier_raises(core_modules, tmp_path: Path):
    core = core_modules["core"]
    cwd = _make_scratch_cwd(tmp_path)
    with pytest.raises(ValueError):
        core.verify(cwd=cwd, no_cache=True, tier="bogus")


# ── (c) unknown check_id raises ValueError with did-you-mean ─────────────────


def test_verify_unknown_check_id_raises_with_suggestion(
    core_modules, tmp_path: Path
):
    core = core_modules["core"]
    cwd = _make_scratch_cwd(tmp_path)

    with pytest.raises(ValueError) as exc:
        core.verify(check_ids=["lnit.ruff"], cwd=cwd, no_cache=True, tier="full")

    msg = str(exc.value)
    assert "lnit.ruff" in msg
    # didyoumean phrasing required by HARN/UX requirement
    assert "did you mean" in msg.lower()


# ── (d) no_cache=True does not create cache.db ───────────────────────────────


def test_verify_no_cache_skips_db_creation(core_modules, tmp_path: Path):
    core = core_modules["core"]
    cwd = _make_scratch_cwd(tmp_path)

    core.verify(cwd=cwd, no_cache=True, tier="quick")
    assert not (cwd / ".verify" / "cache.db").exists()


# ── (e) list_checks returns list of strings (Phase-1 signature) ──────────────


def test_list_checks_returns_strings(core_modules):
    core = core_modules["core"]
    ids = core.list_checks()
    assert isinstance(ids, list)
    assert ids, "registry should have ≥1 spec after harness.checks import"
    assert all(isinstance(x, str) for x in ids)


# ── (f) cache.evict_if_needed called BEFORE return (not dead code) ───────────


def test_verify_evicts_before_return(core_modules, tmp_path: Path):
    """Eviction must run INSIDE verify() — placing it after `return` makes it
    dead code. We mock CacheStore.evict_if_needed and assert it's called exactly
    once during the verify() call, before control returns to us.

    This is the convergence-HIGH 'cache eviction order' guard: a regression
    where the planner wrote `return ...; cache.evict_if_needed(...)` would
    leave the assertion below failing because mock.call_count == 0 at the
    moment verify() returns.
    """
    core = core_modules["core"]
    cache_mod = core_modules["cache"]
    cwd = _make_scratch_cwd(tmp_path)

    with mock.patch.object(
        cache_mod.CacheStore, "evict_if_needed", autospec=True
    ) as evict_spy:
        report = core.verify(cwd=cwd, no_cache=False, tier="quick")
        # The function has already returned to us; eviction must have happened.
        assert evict_spy.call_count == 1, (
            "cache.evict_if_needed must be called inside verify() before return; "
            f"got call_count={evict_spy.call_count}"
        )

    # Sanity: we actually ran checks.
    assert report.summary.total >= 1


# ── (g) cwd contract: load_config reads cwd/pyproject.toml, not process CWD ──


def test_verify_cwd_contract_reads_argument_pyproject(
    core_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """`core.verify(cwd=tmp_path)` MUST call `load_config(cwd / 'pyproject.toml')`
    — NOT `load_config()` with the default that resolves under process CWD.

    Construct a tmp_path with a divergent [tool.verify-kit] section. Spy
    `harness.config.load_config` and assert it's called with the tmp_path
    pyproject, not the process-CWD one.
    """
    core = core_modules["core"]
    config_mod = core_modules["config"]
    cwd = _make_scratch_cwd(tmp_path)

    # Put a divergent pyproject in tmp_path with cache disabled (so we can also
    # observe the parsed config flowed through).
    (cwd / "pyproject.toml").write_text(
        '[tool.verify-kit.cache]\nenabled = false\nmax_size_mb = 7\n',
        encoding="utf-8",
    )

    # Move process CWD elsewhere so any `load_config()` (no-arg) would resolve
    # to a different file.
    monkeypatch.chdir(tmp_path.parent)

    real_load = config_mod.load_config
    captured: dict[str, Path] = {}

    def spy_load_config(path: Path = Path("pyproject.toml")):
        captured["path"] = Path(path)
        return real_load(path)

    monkeypatch.setattr(core, "load_config", spy_load_config)

    core.verify(cwd=cwd, no_cache=True, tier="quick")

    assert "path" in captured, "load_config was not called via core.verify()"
    # Resolved path must point at tmp_path/pyproject.toml — NOT the process-CWD one.
    assert captured["path"] == cwd / "pyproject.toml", (
        f"cwd contract regression: load_config was called with {captured['path']!r}; "
        f"expected {cwd / 'pyproject.toml'!r}"
    )
