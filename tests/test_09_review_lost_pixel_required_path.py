# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Regression test for CR-02: check_web_lost_pixel must fail when required=True
and comparison-results.json is missing/empty/stale, exercising the REAL check
path (through check_web_lost_pixel, not just parse_lostpixel_output directly).

The BL-4 headline fix (parse_lostpixel_output now supports required=True) was
previously NOT wired into the production check: line ~534 called
parse_lostpixel_output(lostpixel_dir) with no arguments, so required mode was
never activated. This regression test proves the wire is in place by:

  1. Rendering a has_web scratch project.
  2. Importing harness.checks.web and harness.models from the rendered project.
  3. Faking Docker availability via DOCKER_HOST env var (avoids the skip branch).
  4. Patching web_mod.proc_run (the module-local alias) and subprocess.Popen so
     lost-pixel "runs" successfully but produces no comparison-results.json.
  5. Setting REQUIRED_CHECK_MODE = True (the signal the runner would set).
  6. Calling check_web_lost_pixel directly.
  7. Asserting status='fail' (not 'pass') -- proving required mode is active.
"""
from __future__ import annotations

import subprocess
import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def cr02_modules(tmp_path_factory: pytest.TempPathFactory):
    """Render a has_web scratch project and yield (web_mod, models_mod, scratch)."""
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("cr02-lp-required"),
        has_web=True,
        has_backend=True,
        has_db=False,
        _vcs_ref="HEAD",
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.models as models_mod
        # Import checks.web — this triggers @register side-effects on the rendered project
        import harness.checks.web as web_mod

        yield web_mod, models_mod, scratch
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _noop_proc_result(returncode: int = 0) -> types.SimpleNamespace:
    """Return a fake proc result (CompletedProcess-like namespace)."""
    return types.SimpleNamespace(
        returncode=returncode,
        stdout="",
        stderr="",
    )


def _make_fake_popen() -> MagicMock:
    """Build a MagicMock that looks like a subprocess.Popen handle."""
    fake = MagicMock()
    fake.terminate = MagicMock()
    fake.wait = MagicMock(return_value=0)
    fake.kill = MagicMock()
    # communicate() is used internally by subprocess.run — return (b"", b"")
    fake.communicate = MagicMock(return_value=(b"", b""))
    fake.returncode = 0
    # Support context manager usage (with Popen(...) as p:)
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    return fake


# ── CR-02 regression: missing artifact + required mode → status=fail ──────────


def test_check_web_lost_pixel_required_missing_artifact_fails(
    cr02_modules, tmp_path: Path, monkeypatch
) -> None:
    """REQUIRED_CHECK_MODE=True + missing comparison-results.json → status='fail'.

    This is the CR-02 regression guard: before the fix, parse_lostpixel_output was
    called with no args so required mode was never activated. The check returned
    'pass' even when comparison-results.json was absent.
    """
    web_mod, models_mod, scratch = cr02_modules

    # Build a minimal fake cwd with web/.lost-pixel/ but NO comparison-results.json
    fake_cwd = tmp_path / "cr02-project"
    web_dir = fake_cwd / "web"
    lostpixel_dir = web_dir / ".lost-pixel"
    lostpixel_dir.mkdir(parents=True)
    # web/dist/ must exist to pass the dist-missing guard in the outside-docker path
    (web_dir / "dist").mkdir(parents=True)

    # Make Docker appear available via DOCKER_HOST env var (bypasses the "skip" branch)
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")

    # Patch proc_run at the harness.checks.web module level.
    # web.py does `from harness.proc import run as proc_run` so we must patch the
    # module-local name, not harness.proc.run, for the patch to take effect.
    monkeypatch.setattr(web_mod, "proc_run", lambda *args, **kwargs: _noop_proc_result(0))

    # Patch subprocess.Popen so the vite-preview Popen in the outside-docker path
    # doesn't actually spawn a process. The check also calls subprocess.run indirectly
    # via proc_run (already patched above), so only Popen needs mocking here.
    fake_popen = _make_fake_popen()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: fake_popen)

    # Skip the 2-second vite preview startup sleep
    monkeypatch.setattr(time, "sleep", lambda _: None)

    # Set REQUIRED_CHECK_MODE = True — this is what runner.run_check does when
    # spec.check_id is in required_ids (the CR-02 contextvar bridge)
    token = models_mod.REQUIRED_CHECK_MODE.set(True)
    try:
        result = web_mod.check_web_lost_pixel(cwd=fake_cwd)
    finally:
        models_mod.REQUIRED_CHECK_MODE.reset(token)

    assert result.status == "fail", (
        f"check_web_lost_pixel with REQUIRED_CHECK_MODE=True and missing "
        f"comparison-results.json must return status='fail', got {result.status!r}. "
        "CR-02: parse_lostpixel_output must be called with required=True so missing "
        "artifacts are caught in --require mode."
    )
    assert result.error is not None, "A failing result must carry an ErrorEnvelope"
    code = result.error.code
    assert any(kw in code.lower() for kw in ("missing", "no_run", "stale", "empty")), (
        f"ErrorEnvelope code must indicate missing artifact in required mode, got: {code!r}"
    )


# ── Non-required (legacy) mode: missing artifact still returns pass ────────────


def test_check_web_lost_pixel_non_required_missing_artifact_passes(
    cr02_modules, tmp_path: Path, monkeypatch
) -> None:
    """Legacy non-required mode (default) with missing comparison-results.json → status='pass'.

    Confirms backwards-compatible behaviour after CR-02: when REQUIRED_CHECK_MODE
    is False (the default), a missing artifact is not a failure.
    """
    web_mod, models_mod, scratch = cr02_modules

    fake_cwd = tmp_path / "cr02-project-nonrequired"
    web_dir = fake_cwd / "web"
    lostpixel_dir = web_dir / ".lost-pixel"
    lostpixel_dir.mkdir(parents=True)
    (web_dir / "dist").mkdir(parents=True)

    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    monkeypatch.setattr(web_mod, "proc_run", lambda *args, **kwargs: _noop_proc_result(0))

    fake_popen = _make_fake_popen()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: fake_popen)

    monkeypatch.setattr(time, "sleep", lambda _: None)

    # REQUIRED_CHECK_MODE is False (default) — do NOT set it to True
    result = web_mod.check_web_lost_pixel(cwd=fake_cwd)

    assert result.status == "pass", (
        f"Non-required mode (REQUIRED_CHECK_MODE=False) with missing "
        f"comparison-results.json must return 'pass' (legacy backwards-compatible "
        f"behaviour), got {result.status!r}"
    )
