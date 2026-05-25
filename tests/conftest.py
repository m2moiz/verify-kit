# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""
Pytest fixtures for verify-kit template smoke tests.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._helpers import render_and_install, render_scratch_project


@pytest.fixture
def template_root() -> Path:
    """Return the verify-kit repo root (where copier.yml lives)."""
    return Path(__file__).parent.parent


@pytest.fixture
def tmp_render_dir(tmp_path: Path) -> Path:
    """Return a fresh scratch directory for rendering into."""
    d = tmp_path / "scratch"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def scratch_project(tmp_path: Path) -> Path:
    """Fresh-render the verify-kit template into a per-test tmp dir."""
    return render_scratch_project(tmp_path)


@pytest.fixture(scope="session")
def scratch_project_installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Session-scoped render + `uv pip install -e .` for slow/smoke tests."""
    return render_and_install(tmp_path_factory.mktemp("installed-scratch"))


@pytest.fixture(scope="session")
def mcp_installed_scratch(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render + install a scaffold for the MCP↔CLI contract suite (Plan 03-01).

    Install command is ``uv pip install -e .`` from the rendered scaffold
    root — NOT ``uv pip install -e harness/`` and NOT
    ``uv pip install -e tmp_path/harness`` (Plan 03-01 acceptance).

    Skips when ``uv`` is not on PATH. Session-scoped so the install cost is
    paid once.
    """
    if shutil.which("uv") is None:
        pytest.skip("uv not available on PATH")
    root = tmp_path_factory.mktemp("mcp-byte-id")
    scratch = render_scratch_project(root)
    subprocess.run(
        ["uv", "venv", "--python", "3.13", str(scratch / ".venv")],
        cwd=scratch,
        check=True,
        capture_output=True,
    )
    env = {**os.environ, "VIRTUAL_ENV": str(scratch / ".venv")}
    subprocess.run(
        ["uv", "pip", "install", "-e", "."],
        cwd=scratch,
        check=True,
        env=env,
        capture_output=True,
    )
    return scratch
