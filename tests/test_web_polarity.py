# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Bidirectional web add-on polarity tests (Plans 07-01 and 07-02).

Plan 07-01: Renders the template in two polarities (has_web=True / has_web=False)
and asserts that path-gating works correctly in both directions.

Plan 07-02: Adds a build-smoke test (test_web_baseline_builds) that renders a
scratch scaffold with has_web=True, runs pnpm install + tsc + pnpm build, and
asserts the built dist/index.html artifact is present.

Design notes:
  - Uses the ``render_scratch_project`` Python-API helper (not raw subprocess)
    to avoid the cwd-leak described in REVIEW-CHECKLIST §1.
  - ``_CLEAN_ENV`` is imported from _helpers and must be passed to any
    subprocess targeting a scratch project (REVIEW-CHECKLIST §8). The helper
    already strips Python venv vars + Node-specific vars (NODE_*, npm_config_*,
    PNPM_HOME, NVM_*) per 07-RESEARCH.md §proc.run discipline (threat T-07-05).
  - Dotfile-absence assertions cover the case Phase 4 missed 3x:
    web/.*, web/**/.*, harness/web/.*, harness/web/**/.* must be empty under
    has_web=False (REVIEW-CHECKLIST §3).

Lives at the repo top-level (NOT under tests/web/) per REVIEW-CHECKLIST §7 —
tests/web/ is a harness pytest-invocation target and we must not recurse.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tests._helpers import _CLEAN_ENV, render_scratch_project  # noqa: F401

# ── Base answers shared across all polarity renders ───────────────────────────

_BASE: dict[str, object] = {
    "project_name": "WebPolarity",
    "project_description": "web polarity test scaffold",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
    # Disable all agent integrations to keep the scaffold minimal.
    "has_claude_code": False,  # noqa: S106 (not a password)
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    # Disable other add-ons — has_web is tested in isolation (D-W04: decoupled polarity).
    "has_backend": False,
    "has_db": False,
    "has_llm": False,
    "has_logfire": False,
    "has_fastapi_mcp": False,
    "has_devcontainer": False,
    "llm_backend": "none",
}


def _render(tmp_path: Path, *, has_web: bool) -> Path:
    """Render the template with a single polarity axis: has_web.

    Passes ``_vcs_ref="HEAD"`` so Copier uses the current worktree HEAD rather
    than the latest released tag (v0.1.0). The has_web prompt was added in
    Plan 07-01, after the v0.1.0 release; without this override Copier would
    clone the tag and silently omit has_web from the answer context, causing
    the Guard-2 conditional directory to resolve to an empty string.
    """
    return render_scratch_project(
        tmp_path,
        _vcs_ref="HEAD",
        **{**_BASE, "has_web": has_web},  # type: ignore[arg-type]
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("has_web", [True, False])
def test_web_polarity_directory_presence(tmp_path: Path, has_web: bool) -> None:
    """Both polarities render without error; directories flip correctly.

    has_web=True  → web/.gitkeep, harness/web/.gitkeep,
                     harness/checks/web.py are all present.
    has_web=False → none of those paths exist.
    """
    scratch = _render(tmp_path, has_web=has_web)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    web_dir = scratch / "web"
    harness_web_dir = scratch / "harness" / "web"
    harness_checks_web = scratch / "harness" / "checks" / "web.py"

    if has_web:
        assert web_dir.is_dir(), (
            "web/ directory must exist when has_web=True "
            "(Guard-1 _exclude or Guard-2 path shape failed)"
        )
        assert (web_dir / ".gitkeep").is_file(), (
            "web/.gitkeep must exist when has_web=True"
        )
        assert harness_web_dir.is_dir(), (
            "harness/web/ must exist when has_web=True"
        )
        assert (harness_web_dir / ".gitkeep").is_file(), (
            "harness/web/.gitkeep must exist when has_web=True"
        )
        assert harness_checks_web.is_file(), (
            "harness/checks/web.py must exist when has_web=True "
            "(Guard-1 _exclude or Guard-2 path shape failed for .jinja2 stub)"
        )
    else:
        assert not web_dir.exists(), (
            "web/ directory must NOT exist when has_web=False "
            "(Guard-1 or Guard-2 failed — polarity leak)"
        )
        assert not harness_web_dir.exists(), (
            "harness/web/ must NOT exist when has_web=False"
        )
        assert not harness_checks_web.exists(), (
            "harness/checks/web.py must NOT exist when has_web=False"
        )


def test_web_false_no_dotfile_leaks(tmp_path: Path) -> None:
    """has_web=False: no dotfiles under web/ or harness/web/ leaked.

    This is the specific coverage that Phase 4 missed 3x (REVIEW-CHECKLIST §3).
    We use rglob patterns to exhaustively check that no file whose path includes
    a web-related directory segment exists in the rendered output.
    """
    scratch = _render(tmp_path, has_web=False)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    # Dotfile-absence checks: REVIEW-CHECKLIST §3 and §8
    leaked_web_dotfiles = list(scratch.rglob("web/.*"))
    assert not leaked_web_dotfiles, (
        "Dotfiles leaked under web/ when has_web=False:\n"
        + "\n".join(f"  {p.relative_to(scratch)}" for p in leaked_web_dotfiles)
    )

    leaked_web_dotfiles_deep = list(scratch.rglob("web/**/.*"))
    assert not leaked_web_dotfiles_deep, (
        "Deep dotfiles leaked under web/**/ when has_web=False:\n"
        + "\n".join(f"  {p.relative_to(scratch)}" for p in leaked_web_dotfiles_deep)
    )

    leaked_harness_web_dotfiles = list(scratch.rglob("harness/web/.*"))
    assert not leaked_harness_web_dotfiles, (
        "Dotfiles leaked under harness/web/ when has_web=False "
        "(harness-side dotfile coverage — REVIEW-CHECKLIST §3):\n"
        + "\n".join(f"  {p.relative_to(scratch)}" for p in leaked_harness_web_dotfiles)
    )

    leaked_harness_web_dotfiles_deep = list(scratch.rglob("harness/web/**/.*"))
    assert not leaked_harness_web_dotfiles_deep, (
        "Deep dotfiles leaked under harness/web/**/ when has_web=False:\n"
        + "\n".join(f"  {p.relative_to(scratch)}" for p in leaked_harness_web_dotfiles_deep)
    )


def test_web_false_no_literal_jinja_brace_filenames(tmp_path: Path) -> None:
    """has_web=False: no literal Jinja-brace filenames leaked into rendered output.

    Asserts that Copier resolved the conditional path and did NOT ship literal
    ``{% if has_web %}...{% endif %}`` strings as actual filenames. A rendered
    file with a brace-literal name would indicate Jinja did not expand the
    conditional in the path (e.g. if the Guard-2 directory was missing from the
    source tree or the Copier version doesn't support conditional paths).
    """
    scratch = _render(tmp_path, has_web=False)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    jinja_brace_files: list[str] = []
    for node in scratch.rglob("*"):
        if "{%" in node.name or "%}" in node.name:
            jinja_brace_files.append(str(node.relative_to(scratch)))

    assert not jinja_brace_files, (
        "Literal Jinja-brace filenames found in rendered output (has_web=False).\n"
        "Copier did not resolve the conditional path — check that the Guard-2\n"
        "source directories exist with the exact literal brace names:\n"
        + "\n".join(f"  {p}" for p in sorted(jinja_brace_files))
    )


def test_web_true_no_literal_jinja_brace_filenames(tmp_path: Path) -> None:
    """has_web=True: no literal Jinja-brace filenames leaked into rendered output.

    Mirror of the has_web=False check above, for the positive polarity.
    """
    scratch = _render(tmp_path, has_web=True)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    jinja_brace_files: list[str] = []
    for node in scratch.rglob("*"):
        if "{%" in node.name or "%}" in node.name:
            jinja_brace_files.append(str(node.relative_to(scratch)))

    assert not jinja_brace_files, (
        "Literal Jinja-brace filenames found in rendered output (has_web=True).\n"
        "Copier did not resolve the conditional path — check that the Guard-2\n"
        "source directories exist with the exact literal brace names:\n"
        + "\n".join(f"  {p}" for p in sorted(jinja_brace_files))
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required")
def test_web_baseline_builds(tmp_path: Path) -> None:
    """Plan 07-02 build-smoke: has_web=True scaffold installs, typechecks, and builds.

    Renders a scratch scaffold with has_web=True, has_backend=False (cheaper
    polarity; 07-04 adds the has_backend=True variant), then runs:
      1. pnpm install --frozen-lockfile
      2. pnpm exec tsc --noEmit
      3. pnpm build

    Asserts that dist/index.html is produced (proof that vite build ran to
    completion). Skips if Node is not on PATH so CI or local devs without Node
    still see green for the path-gating tests from 07-01.

    _CLEAN_ENV drops outer Python venv vars AND Node-specific vars (NODE_*,
    npm_config_*, PNPM_HOME, NVM_*) to prevent false-pass from env leakage
    (REVIEW-CHECKLIST §8, threat T-07-05).
    """
    scratch = _render(tmp_path, has_web=True)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    web_dir = scratch / "web"
    assert web_dir.is_dir(), "web/ dir must exist for has_web=True"

    # Step 1: enable corepack/pnpm (ignore errors — node version on PATH may
    # already have corepack active; the lockfile was generated with pnpm@9.15.0
    # but any compatible pnpm 9.x can install --frozen-lockfile correctly).
    subprocess.run(
        ["corepack", "enable", "pnpm"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=False,  # non-zero is OK if corepack is not installed / no perms
    )

    # Step 2: install dependencies from the shipped lockfile
    subprocess.run(
        ["pnpm", "install", "--frozen-lockfile"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=180,
    )

    # Step 3: typecheck
    subprocess.run(
        ["pnpm", "exec", "tsc", "--noEmit"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=60,
    )

    # Step 4: production build
    subprocess.run(
        ["pnpm", "build"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=120,
    )

    # Assert the build produced an index.html artifact
    dist_index = web_dir / "dist" / "index.html"
    assert dist_index.is_file(), (
        f"pnpm build succeeded but dist/index.html is missing at {dist_index}; "
        "check vite.config.ts build.outDir setting"
    )
