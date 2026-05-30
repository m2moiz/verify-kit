# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.meta (meta.stability — determinism guard).

Covers (hermetic — the real full suite is NEVER run; the enumerated check set
is monkeypatched to a tiny in-memory fake registry so the test cannot flake on
the actual project state):

- registry registration + spec metadata (tier=quick, category=meta, no tool)
- pass when every enumerated quick-tier check returns a STABLE status twice
- PLANTED FAILURE: a flappy check whose status alternates across runs is flagged
  nondeterministic with the dotted code `meta.stability.nondeterministic`
- anti-recursion: meta.stability never probes itself
- only quick-tier checks are enumerated (standard/slow excluded)
- a sibling check that RAISES on both runs is treated as stable (not a flap)
- carryover-cwd: the cwd kwarg is forwarded verbatim to every probed spec.fn

The end-to-end forcing function (render scratch → inject a flappy check →
`meta.stability` goes red) is exercised here against a fake registry rather than
the live suite so it is deterministic and does not depend on which checks the
render happens to ship.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def meta_modules(tmp_path_factory: pytest.TempPathFactory):
    # _vcs_ref="HEAD": meta.stability was added after the latest release tag, so
    # render from the worktree HEAD (not the tag) to include it.
    scratch = render_scratch_project(tmp_path_factory.mktemp("meta-scratch"), _vcs_ref="HEAD")
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.models as models
        import harness.registry as registry
        from harness.checks import meta as meta_mod

        yield registry, models, meta_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _spec(models, check_id: str, tier: str, fn):
    """Build a real CheckSpec wrapping `fn` for the fake registry."""
    return models.CheckSpec(check_id=check_id, fn=fn, tier=tier)


def _stable(status: str):
    """A check fn that always returns the same status (deterministic)."""

    def _fn(cwd: Path):
        return _Result(status)

    return _fn


def _flappy(statuses: list[str]):
    """A check fn whose status cycles through `statuses` on successive calls."""
    box = {"i": 0}

    def _fn(cwd: Path):
        status = statuses[box["i"] % len(statuses)]
        box["i"] += 1
        return _Result(status)

    return _fn


class _Result:
    """Minimal stand-in for a CheckResult — meta.stability reads only `.status`."""

    def __init__(self, status: str) -> None:
        self.status = status


# ── registration / metadata ──────────────────────────────────────────────────


def test_meta_stability_registered(meta_modules) -> None:
    registry, _, _ = meta_modules
    ids = {s.check_id for s in registry.list_checks()}
    assert "meta.stability" in ids


def test_meta_stability_spec_metadata(meta_modules) -> None:
    registry, _, _ = meta_modules
    spec = registry.get_check("meta.stability")
    assert spec is not None
    assert spec.tier == "quick"
    assert spec.category == "meta"
    assert spec.fixable is False
    assert spec.tool is None


# ── pass: all enumerated checks stable ────────────────────────────────────────


def test_pass_when_all_quick_checks_stable(
    meta_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, models, meta_mod = meta_modules
    spec = registry.get_check("meta.stability")

    fake = [
        _spec(models, "fake.pass", "quick", _stable("pass")),
        _spec(models, "fake.skip", "quick", _stable("skip")),
        _spec(models, "fake.fail", "quick", _stable("fail")),
    ]
    monkeypatch.setattr(meta_mod, "list_checks", lambda: fake)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


# ── PLANTED FAILURE: a flappy check is flagged ────────────────────────────────


def test_fail_on_flappy_check_with_dotted_code(
    meta_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A check whose status alternates pass→fail across the two runs must red."""
    registry, models, meta_mod = meta_modules
    spec = registry.get_check("meta.stability")

    fake = [
        _spec(models, "fake.stable", "quick", _stable("pass")),
        # First probe → "pass", second probe → "fail": the planted flap.
        _spec(models, "fake.flappy", "quick", _flappy(["pass", "fail"])),
    ]
    monkeypatch.setattr(meta_mod, "list_checks", lambda: fake)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "meta.stability.nondeterministic"
    # The flappy id is named; the stable one is not implicated.
    assert "fake.flappy" in result.message
    assert "fake.stable" not in result.message
    assert "fake.flappy" in result.error.message


# ── anti-recursion: never probes itself ───────────────────────────────────────


def test_does_not_recurse_into_itself(
    meta_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """meta.stability must exclude its own id from the probed set."""
    registry, models, meta_mod = meta_modules
    spec = registry.get_check("meta.stability")

    probed: list[str] = []

    def _tracking_fn(check_id: str):
        def _fn(cwd: Path):
            probed.append(check_id)
            return _Result("pass")

        return _fn

    fake = [
        _spec(models, "meta.stability", "quick", _tracking_fn("meta.stability")),
        _spec(models, "fake.other", "quick", _tracking_fn("fake.other")),
    ]
    monkeypatch.setattr(meta_mod, "list_checks", lambda: fake)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    # The self entry was filtered out: it was never invoked, only fake.other was.
    assert "meta.stability" not in probed
    assert probed.count("fake.other") == 2


# ── tier filtering: only quick-tier checks enumerated ─────────────────────────


def test_only_quick_tier_checks_probed(
    meta_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A flappy STANDARD/SLOW check must be ignored (out of the quick set)."""
    registry, models, meta_mod = meta_modules
    spec = registry.get_check("meta.stability")

    probed: list[str] = []

    def _tracking_flappy(check_id: str, statuses: list[str]):
        box = {"i": 0}

        def _fn(cwd: Path):
            probed.append(check_id)
            status = statuses[box["i"] % len(statuses)]
            box["i"] += 1
            return _Result(status)

        return _fn

    fake = [
        _spec(models, "fake.quick", "quick", _stable("pass")),
        # This one flaps, but it is STANDARD tier → must NOT be enumerated, so
        # meta.stability stays green.
        _spec(models, "fake.standard", "standard", _tracking_flappy("fake.standard", ["pass", "fail"])),
        _spec(models, "fake.slow", "slow", _tracking_flappy("fake.slow", ["skip", "fail"])),
    ]
    monkeypatch.setattr(meta_mod, "list_checks", lambda: fake)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert "fake.standard" not in probed
    assert "fake.slow" not in probed


# ── a consistently-raising sibling is stable, not a flap ──────────────────────


def test_consistently_raising_check_is_stable(
    meta_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A check that raises on BOTH runs is deterministic — must not red the guard."""
    registry, models, meta_mod = meta_modules
    spec = registry.get_check("meta.stability")

    def _always_raises(cwd: Path):
        raise RuntimeError("sibling check is broken but consistently so")

    fake = [
        _spec(models, "fake.ok", "quick", _stable("pass")),
        _spec(models, "fake.boom", "quick", _always_raises),
    ]
    monkeypatch.setattr(meta_mod, "list_checks", lambda: fake)

    result = spec.fn(cwd=tmp_path)
    # A consistently-raising check yields the same sentinel twice → stable.
    assert result.status == "pass"


# ── carryover-cwd: cwd forwarded to every probe ───────────────────────────────


def test_forwards_cwd_to_every_probe(
    meta_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cwd kwarg must be forwarded verbatim to each probed spec.fn (§1)."""
    registry, models, meta_mod = meta_modules
    spec = registry.get_check("meta.stability")

    seen_cwds: list[Path] = []

    def _capture_fn(cwd: Path):
        seen_cwds.append(cwd)
        return _Result("pass")

    fake = [_spec(models, "fake.capture", "quick", _capture_fn)]
    monkeypatch.setattr(meta_mod, "list_checks", lambda: fake)

    spec.fn(cwd=tmp_path)
    # Probed twice, both times with the exact cwd we passed in.
    assert seen_cwds == [tmp_path, tmp_path]
