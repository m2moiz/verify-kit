"""
Shared test helpers for Phase 2+ verify-kit tests.

Every test that needs a rendered scaffold imports from this module rather
than inventing its own `copier` invocation. See Plan 02-01, Task 0.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import yaml
from copier import run_copy

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COPIER_YML = _REPO_ROOT / "copier.yml"

# Known-default answers for Phase 1 `copier.yml` questions. Any question NOT
# listed here is intentionally omitted so Copier falls back to its declared
# `default:` (combined with defaults=True in run_copy). This keeps us robust
# against Phase 1 adding/removing questions.
_KNOWN_DEFAULTS: dict[str, Any] = {
    "project_name": "Scratch",
    "project_title": "Scratch",
    "project_description": "Scratch project for verify-kit tests.",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
    "include_devcontainer": False,
    "has_devcontainer": False,
    "addons_web": False,
    "addons_game": False,
    "addons_audio": False,
    "addons_llm": False,
    "addons_backend": False,
    "has_backend": False,
    "has_llm": False,
    "has_logfire": False,
    "has_fastapi_mcp": False,
    "has_db": False,
    "has_claude_code": False,
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    "llm_backend": "none",
}


def _build_default_answers() -> dict[str, Any]:
    """Introspect copier.yml and return defaults for known question keys."""
    if not _COPIER_YML.exists():
        return dict(_KNOWN_DEFAULTS)
    data = yaml.safe_load(_COPIER_YML.read_text()) or {}
    answers: dict[str, Any] = {}
    for key, val in data.items():
        if key.startswith("_"):
            continue
        if not isinstance(val, dict) or "type" not in val:
            continue
        if key in _KNOWN_DEFAULTS:
            answers[key] = _KNOWN_DEFAULTS[key]
    return answers


_DEFAULT_ANSWERS = _build_default_answers()


def render_scratch_project(tmp_path: Path, **overrides: object) -> Path:
    """Render the verify-kit template into `tmp_path/scratch` and return the path."""
    dst = tmp_path / "scratch"
    answers = {**_DEFAULT_ANSWERS, **overrides}
    run_copy(
        src_path=str(_REPO_ROOT),
        dst_path=str(dst),
        data=answers,
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    return dst


def install_scratch_harness(scratch: Path) -> None:
    """Create an isolated 3.13 venv in `scratch/.venv` and install harness into it.

    The verify-kit repo itself runs on Python 3.11+, but rendered scratch
    projects pin Python 3.13 (template/.mise.toml + template/pyproject.toml).
    Reusing the verify-kit venv would fail with ``requires-python >= 3.13``.

    Implementation mirrors the proven pattern from
    ``tests/test_phase2_observability.py``: ``uv venv --python 3.13`` then
    ``uv pip install -e .`` with ``VIRTUAL_ENV`` pointed at the new venv.

    Downstream tests should invoke commands via ``uv run`` (auto-discovers
    ``.venv``) or call ``venv_python(scratch)`` for the explicit interpreter.
    """
    venv = scratch / ".venv"
    subprocess.run(
        ["uv", "venv", "--python", "3.13", str(venv)],
        cwd=scratch,
        check=True,
        capture_output=True,
    )
    env = {**os.environ, "VIRTUAL_ENV": str(venv)}
    subprocess.run(
        ["uv", "pip", "install", "-e", "."],
        cwd=scratch,
        check=True,
        env=env,
        capture_output=True,
    )


def venv_python(scratch: Path) -> str:
    """Return absolute path to the python interpreter inside scratch/.venv."""
    return str(scratch / ".venv" / "bin" / "python")


def render_and_install(tmp_path: Path, **overrides: object) -> Path:
    """Render + install. Convenience for tests that need an importable harness."""
    scratch = render_scratch_project(tmp_path, **overrides)
    install_scratch_harness(scratch)
    return scratch


__all__ = [
    "render_scratch_project",
    "install_scratch_harness",
    "render_and_install",
    "venv_python",
]
