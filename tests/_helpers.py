# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""
Shared test helpers for Phase 2+ verify-kit tests.

Every test that needs a rendered scaffold imports from this module rather
than inventing its own `copier` invocation. See Plan 02-01, Task 0.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
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
    # Phase 7 add-ons (v0.2+)
    "has_web": False,
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


def render_scratch_project(
    tmp_path: Path,
    *,
    _vcs_ref: str | None = None,
    **overrides: object,
) -> Path:
    """Render the verify-kit template into ``tmp_path/scratch`` and return the path.

    Args:
        tmp_path:   Directory to render into (test fixture or tempdir).
        _vcs_ref:   Optional VCS ref to pass to Copier. Use ``"HEAD"`` in Phase 7+
                    tests so renders include prompts added after the v0.1.0 tag.
                    Defaults to ``None`` (Copier uses the latest tag), which
                    preserves the behaviour of all existing Phase 1-6 tests.
        **overrides:  Question answers that override the built-in defaults.
    """
    dst = tmp_path / "scratch"
    answers = {**_DEFAULT_ANSWERS, **overrides}
    copy_kwargs: dict[str, object] = {
        "src_path": str(_REPO_ROOT),
        "dst_path": str(dst),
        "data": answers,
        "defaults": True,
        "unsafe": True,
        "quiet": True,
    }
    if _vcs_ref is not None:
        copy_kwargs["vcs_ref"] = _vcs_ref
    run_copy(**copy_kwargs)  # type: ignore[arg-type]
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


#: Writable per-run COREPACK_HOME so `corepack enable pnpm` (run by the web
#: polarity tests) symlinks the pnpm shim into a tmp dir we own — NOT
#: /usr/local/bin. Without this, corepack tries to symlink into a
#: system-owned bin dir and fails with EACCES on repeated local runs / in
#: sandboxes (verify-kit-kbi). A unique per-process dir avoids cross-run
#: collisions; it is created lazily here so the directory exists before any
#: subprocess uses it.
_COREPACK_HOME = Path(tempfile.gettempdir()) / f"vk-corepack-{os.getpid()}"
_COREPACK_HOME.mkdir(parents=True, exist_ok=True)

#: Outer-process env minus VIRTUAL_ENV / UV_PROJECT_ENVIRONMENT / PYTHONPATH
#: etc. — pass via ``subprocess.run(..., env=_CLEAN_ENV)`` so the scratch
#: project resolves its own venv, not the outer one (REVIEW-CHECKLIST §8).
#:
#: Also strips Node-specific vars (NODE_*, npm_config_*, PNPM_HOME, NVM_*)
#: so that outer Node/pnpm installations don't leak into web polarity tests
#: (07-RESEARCH.md §proc.run subprocess discipline; threat T-07-05).
#:
#: COREPACK_HOME is forced to a writable per-run tmp dir (verify-kit-kbi) so
#: `corepack enable pnpm` does not EACCES trying to symlink into /usr/local/bin.
_CLEAN_ENV: dict[str, str] = {
    **{
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "VIRTUAL_ENV",
            "UV_PROJECT_ENVIRONMENT",
            "PYTHONPATH",
            "PYTHONHOME",
            "PYTHONSTARTUP",
            "PYTHONNOUSERSITE",
            "PNPM_HOME",
            "COREPACK_HOME",
        }
        and not k.startswith("NODE_")
        and not k.startswith("npm_config_")
        and not k.startswith("NVM_")
    },
    "COREPACK_HOME": str(_COREPACK_HOME),
}


__all__ = [
    "render_scratch_project",
    "install_scratch_harness",
    "render_and_install",
    "venv_python",
    "_CLEAN_ENV",
]
