"""
Pytest fixtures for verify-kit template smoke tests.
"""
from pathlib import Path

import pytest


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
