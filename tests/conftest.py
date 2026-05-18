"""
Pytest fixtures for verify-kit template smoke tests.
"""
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
