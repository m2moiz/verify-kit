"""Phase 4 integration test: prove a fresh has_backend=true scaffold runs
`just verify-backend` clean end-to-end.

This test is the phase's success criterion ground-truth. The FULL variant is
the SLOWEST test in the suite — it copier-copies, uv-pip-installs, and runs
the backend slice including docker-compose startup. Generous timeouts; skips
cleanly without Docker or the required CLI tools.
"""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
import pytest


def _docker_daemon_running() -> bool:
    """`docker info` exits 0. Uses docker info, NOT shutil.which('docker') (Codex HIGH #9)."""
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _render_scratch(tmp_path: Path, *, has_backend: str = "true") -> Path:
    """Render a fresh scaffold into tmp_path/scratch and uv-install it."""
    project_root = Path(__file__).resolve().parent.parent
    scratch = tmp_path / "scratch"
    subprocess.run(
        [
            "copier", "copy", "--defaults", "--trust",
            "--data", f"has_backend={has_backend}",
            "--data", "has_db=true",
            "--data", "has_logfire=false",
            "--data", "has_fastapi_mcp=false",
            "--data", "project_name=test-app",
            "--data", "author_name=t",
            "--data", "author_email=t@t.t",
            "--data", "project_description=phase 4 integration",
            str(project_root), str(scratch),
        ],
        cwd=tmp_path, check=True, timeout=180,
    )
    import os
    subprocess.run(
        ["uv", "pip", "install", "-e", "."],
        cwd=scratch, check=True, timeout=600,
        env={**os.environ, "VIRTUAL_ENV": ""},
    )
    return scratch


# ── FULL path (Docker required) ───────────────────────────────────────────────

@pytest.mark.skipif(shutil.which("copier") is None, reason="copier not installed")
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed")
@pytest.mark.skipif(shutil.which("just") is None, reason="just not installed")
@pytest.mark.skipif(not _docker_daemon_running(), reason="docker daemon not running")
def test_fresh_scaffold_verify_backend_full_path_exits_zero(tmp_path: Path):
    """Success criterion 3 ground truth: FULL verify-backend with live stack.

    Brings up docker-compose, runs schemathesis against the LIVE OpenAPI, smokes
    /healthz, tears down. This is the test that proves the phase actually
    delivers — without it, `verify-backend` could exit 0 while skipping the
    live fuzz path (Codex HIGH #4).
    """
    scratch = _render_scratch(tmp_path)
    assert (scratch / "app" / "main.py").exists()
    assert (scratch / "Dockerfile").exists()
    assert (scratch / "docker-compose.yml").exists()

    # Run the FULL verify-backend recipe — brings up stack, fuzzes live OpenAPI,
    # smokes, tears down. The recipe calls `just docker-up` and `just docker-down`
    # so this single subprocess covers the whole cycle.
    r = subprocess.run(
        ["just", "verify-backend"],
        cwd=scratch, capture_output=True, text=True, timeout=1800,
    )
    # Best-effort teardown if the recipe failed mid-flight.
    if r.returncode != 0:
        subprocess.run(
            ["just", "docker-down"], cwd=scratch, timeout=120, check=False,
        )
    assert r.returncode == 0, (
        f"verify-backend FULL path exit {r.returncode}\n"
        f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )
    # Forcing function: the output MUST contain evidence that schemathesis ran
    # against the LIVE OpenAPI — i.e., the URL must appear in the stdout.
    # If the recipe regresses to skip-when-not-running, this assertion catches it.
    assert "http://localhost:8000/openapi.json" in r.stdout, (
        "schemathesis did not run against live OpenAPI — Codex HIGH #4 regression. "
        f"stdout was:\n{r.stdout}"
    )


# ── Quick path (no Docker, no full stack) ────────────────────────────────────

@pytest.mark.skipif(shutil.which("copier") is None, reason="copier not installed")
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed")
@pytest.mark.skipif(shutil.which("just") is None, reason="just not installed")
def test_fresh_scaffold_verify_backend_quick_skips_live_checks(tmp_path: Path):
    """Quick path graceful degradation: no docker-up, pytest passes, fuzz skipped."""
    scratch = _render_scratch(tmp_path)
    r = subprocess.run(
        ["just", "verify-backend-quick"],
        cwd=scratch, capture_output=True, text=True, timeout=900,
    )
    assert r.returncode == 0, (
        f"verify-backend-quick exit {r.returncode}\n"
        f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )
    # The "app not running" message OR "app reachable" confirms the graceful
    # degradation branch fired correctly in whichever state the local env is in.
    assert "app not running" in r.stdout or "app reachable" in r.stdout, (
        f"Expected app-not-running or app-reachable message in stdout:\n{r.stdout}"
    )


# ── has_backend=false polarity (no Docker needed) ────────────────────────────

@pytest.mark.skipif(shutil.which("copier") is None, reason="copier not installed")
def test_has_backend_false_has_no_verify_backend_recipe(tmp_path: Path):
    """has_backend=false scaffold has no verify-backend recipe, no app/, no tests/backend/."""
    project_root = Path(__file__).resolve().parent.parent
    scratch = tmp_path / "scratch"
    subprocess.run(
        [
            "copier", "copy", "--defaults", "--trust",
            "--data", "has_backend=false",
            "--data", "project_name=t",
            "--data", "author_name=t",
            "--data", "author_email=t@t.t",
            "--data", "project_description=t",
            str(project_root), str(scratch),
        ],
        cwd=tmp_path, check=True, timeout=180,
    )
    # justfile has no verify-backend recipe
    justfile_text = (scratch / "justfile").read_text()
    assert "verify-backend:" not in justfile_text
    # No app/, no tests/backend/
    assert not (scratch / "app").exists()
    assert not (scratch / "tests" / "backend").exists()
