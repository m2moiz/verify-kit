# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Regression test for the web.lost_pixel exit-code interpretation.

Lost Pixel OSS signals comparison results via the process EXIT CODE, not a
results file (it never writes comparison-results.json — that is a SaaS artifact):

  exit 0  → no differences            → check status='pass'
  exit 1  → diffs found (difference/*.png written) → status='fail' + diff envelope
  exit >1 → Lost Pixel/Docker crashed → status='fail' + run.failed envelope

This exercises the REAL check path (check_web_lost_pixel, not just
parse_lostpixel_output) by faking Docker availability and patching the
subprocess layer so lost-pixel "runs" with a chosen exit code.

--require freshness is NOT the check's concern: the runner (harness.core)
enforces it generically by asserting each required id carries the current
process run_id. That mechanism is covered by test_09_03_require_and_run_id.py.
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
def web_check_modules(tmp_path_factory: pytest.TempPathFactory):
    """Render a has_web scratch project and yield (web_mod, scratch)."""
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("lp-exitcode"),
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
        import harness.checks.web as web_mod

        yield web_mod, scratch
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _make_fake_popen() -> MagicMock:
    """A MagicMock that looks like a subprocess.Popen handle (vite preview)."""
    fake = MagicMock()
    fake.terminate = MagicMock()
    fake.wait = MagicMock(return_value=0)
    fake.kill = MagicMock()
    fake.communicate = MagicMock(return_value=(b"", b""))
    fake.returncode = 0
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    return fake


def _proc_run_stub(comparison_returncode: int):
    """Build a proc_run replacement.

    The check calls proc_run twice in the outside-docker path:
      1. `pnpm exec lost-pixel --version`  → must return a clean version string
      2. `docker run ... lostpixel/...`    → the comparison; returns the chosen code
    """

    def _stub(args, *_args, **_kwargs):
        if "--version" in args:
            return types.SimpleNamespace(returncode=0, stdout="3.22.0\n", stderr="")
        return types.SimpleNamespace(returncode=comparison_returncode, stdout="", stderr="")

    return _stub


def _fake_project(tmp_path: Path, *, diff_name: str | None = None) -> Path:
    """Create a fake cwd with web/dist/ and optionally a difference PNG."""
    cwd = tmp_path / "project"
    web_dir = cwd / "web"
    (web_dir / "dist").mkdir(parents=True)
    (web_dir / ".lost-pixel").mkdir(parents=True)
    if diff_name is not None:
        difference = web_dir / ".lost-pixel" / "difference"
        difference.mkdir(parents=True)
        (difference / f"{diff_name}.png").write_bytes(b"\x89PNG\r\n")
    return cwd


def _patch_subprocess(monkeypatch, web_mod, comparison_returncode: int) -> None:
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    monkeypatch.setattr(web_mod, "proc_run", _proc_run_stub(comparison_returncode))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _make_fake_popen())
    monkeypatch.setattr(time, "sleep", lambda _: None)


# ── exit 0 → pass ─────────────────────────────────────────────────────────────


def test_exit_zero_is_pass(web_check_modules, tmp_path: Path, monkeypatch) -> None:
    """Lost Pixel exit 0 (no differences) → status='pass'."""
    web_mod, _ = web_check_modules
    cwd = _fake_project(tmp_path)
    _patch_subprocess(monkeypatch, web_mod, comparison_returncode=0)

    result = web_mod.check_web_lost_pixel(cwd=cwd)

    assert result.status == "pass", (
        f"Lost Pixel exit 0 must be a pass (no diffs), got {result.status!r}"
    )
    assert result.error is None


# ── exit 1 + difference PNG → fail with diff envelope ─────────────────────────


def test_exit_one_with_diff_png_is_fail(web_check_modules, tmp_path: Path, monkeypatch) -> None:
    """Lost Pixel exit 1 + difference/<name>.png → status='fail' + diff envelope."""
    web_mod, _ = web_check_modules
    cwd = _fake_project(tmp_path, diff_name="gallery-full")
    _patch_subprocess(monkeypatch, web_mod, comparison_returncode=1)

    result = web_mod.check_web_lost_pixel(cwd=cwd)

    assert result.status == "fail", (
        f"Lost Pixel exit 1 (diffs found) must be a fail, got {result.status!r}"
    )
    assert result.error is not None
    assert result.error.code == "web.lost_pixel.diff.gallery-full", result.error.code
    assert result.error.fix_command == "git add web/.lost-pixel/baseline/gallery-full.png"


# ── exit 1 without a diff PNG → fail (generic), not a phantom pass ────────────


def test_exit_one_without_diff_png_is_fail(web_check_modules, tmp_path: Path, monkeypatch) -> None:
    """Exit 1 but no difference PNG on disk → fail with the generic diff code."""
    web_mod, _ = web_check_modules
    cwd = _fake_project(tmp_path)  # no difference/ PNG
    _patch_subprocess(monkeypatch, web_mod, comparison_returncode=1)

    result = web_mod.check_web_lost_pixel(cwd=cwd)

    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "web.lost_pixel.diff.unknown", result.error.code


# ── exit >1 → crash envelope (with surfaced output) ───────────────────────────


def test_exit_gt_one_is_crash(web_check_modules, tmp_path: Path, monkeypatch) -> None:
    """Lost Pixel exit 125 (Docker crash) → status='fail' with run.failed code."""
    web_mod, _ = web_check_modules
    cwd = _fake_project(tmp_path)
    _patch_subprocess(monkeypatch, web_mod, comparison_returncode=125)

    result = web_mod.check_web_lost_pixel(cwd=cwd)

    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "web.lost_pixel.run.failed", result.error.code
