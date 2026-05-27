# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Bidirectional web add-on polarity tests (Plans 07-01, 07-02, and 07-03).

Plan 07-01: Renders the template in two polarities (has_web=True / has_web=False)
and asserts that path-gating works correctly in both directions.

Plan 07-02: Adds a build-smoke test (test_web_baseline_builds) that renders a
scratch scaffold with has_web=True, runs pnpm install + tsc + pnpm build, and
asserts the built dist/index.html artifact is present.

Plan 07-03: Extends the build-smoke with Tailwind v4 + shadcn coupling guards:
  - Tailwind CSS output contains OKLCH tokens (CSS-first pipeline ran).
  - No tailwind.config.{js,ts,mjs,cjs} file exists (Tailwind v4 CSS-first).
  - components.json declares the Tailwind v4 contract.
  - Exactly 7 vendored components exist.
  - App.tsx is the gallery with data-lost-pixel-id markers.

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

import json
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


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required")
def test_web_tailwind_shadcn_baseline(tmp_path: Path) -> None:
    """Plan 07-03 coupling guards: Tailwind v4 + shadcn vendoring assertions.

    Renders has_web=True, runs pnpm install + pnpm build, then asserts:

    1. Tailwind v4 pipeline ran: built CSS contains "oklch" tokens and
       "--background" CSS variable (from the @theme block) and is > 5KB
       (a no-op CSS would be tiny).

    2. Coupling guard: no tailwind.config.{js,ts,mjs,cjs} file in the scaffold
       (Tailwind v4 CSS-first; UI-SPEC Registry Safety).

    3. shadcn vendoring guard: components.json is present and declares
       tailwind.config="" + cssVariables=true; exactly 7 .tsx files exist under
       web/src/components/ui/ matching {button,card,input,label,dialog,sheet,sonner}.

    4. Gallery contract guard: App.tsx contains >= 7 data-lost-pixel-id= markers
       and imports PROJECT_NAME from the config shim (Pitfall §1 check).

    Reuses _CLEAN_ENV + the same pnpm install/build subprocess calls as
    test_web_baseline_builds (no extra network calls beyond the existing install).
    """
    scratch = _render(tmp_path, has_web=True)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    web_dir = scratch / "web"
    assert web_dir.is_dir(), "web/ dir must exist for has_web=True"

    # --- Install and build (same flow as test_web_baseline_builds) -----------
    subprocess.run(
        ["corepack", "enable", "pnpm"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=False,
    )

    subprocess.run(
        ["pnpm", "install", "--frozen-lockfile"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=180,
    )

    subprocess.run(
        ["pnpm", "build"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=120,
    )

    # --- Guard 1: Tailwind v4 pipeline ran (OKLCH tokens in CSS output) ------
    dist_dir = web_dir / "dist" / "assets"
    css_files = list(dist_dir.glob("*.css"))
    assert css_files, (
        f"No CSS file found under {dist_dir}; "
        "check that @tailwindcss/vite plugin is in vite.config.ts.jinja2"
    )
    css_text = css_files[0].read_text(encoding="utf-8")
    assert "oklch" in css_text, (
        "Built CSS does not contain 'oklch' — Tailwind v4 CSS-first pipeline "
        "did not run (missing @import 'tailwindcss' in src/index.css or missing "
        "@tailwindcss/vite in vite.config.ts)"
    )
    assert "--background" in css_text, (
        "Built CSS does not contain '--background' — @theme block was not compiled "
        "(check src/index.css for @theme inline { --color-background: ... })"
    )
    assert len(css_text) > 5_000, (
        f"Built CSS is only {len(css_text)} bytes — suspiciously small. "
        "Tailwind v4 with shadcn should produce > 5KB of output."
    )

    # --- Guard 2: no tailwind.config.* file (Tailwind v4 CSS-first) ----------
    for ext in ("js", "ts", "mjs", "cjs"):
        config_file = web_dir / f"tailwind.config.{ext}"
        assert not config_file.exists(), (
            f"Unexpected {config_file.name} found in scaffold. "
            "Tailwind v4 CSS-first mode must NOT have a tailwind.config file. "
            "Check components.json: tailwind.config must be empty string."
        )

    # --- Guard 3: shadcn vendoring contract ----------------------------------
    components_json = web_dir / "components.json"
    assert components_json.is_file(), (
        "components.json missing from rendered scaffold. "
        "It must be committed at template/web/components.json (no .jinja2 suffix)."
    )
    data = json.loads(components_json.read_text(encoding="utf-8"))
    assert data.get("tailwind", {}).get("config") == "", (
        f"components.json tailwind.config is not empty: "
        f"{data.get('tailwind', {}).get('config')!r}. "
        "Must be empty string to signal Tailwind v4 CSS-first mode."
    )
    assert data.get("tailwind", {}).get("cssVariables") is True, (
        "components.json tailwind.cssVariables is not true. "
        "shadcn v4 requires cssVariables: true for Tailwind v4 OKLCH integration."
    )

    ui_dir = web_dir / "src" / "components" / "ui"
    assert ui_dir.is_dir(), f"src/components/ui/ dir missing from scaffold at {ui_dir}"
    ui_files = {f.stem for f in ui_dir.iterdir() if f.suffix == ".tsx"}
    expected_components = {"button", "card", "input", "label", "dialog", "sheet", "sonner"}
    assert ui_files == expected_components, (
        f"Vendored component mismatch.\n"
        f"  Expected: {sorted(expected_components)}\n"
        f"  Found:    {sorted(ui_files)}\n"
        "Check that exactly 7 shadcn components are committed under "
        "template/web/src/components/ui/ (no .jinja2 suffix)."
    )

    # --- Guard 4: App.tsx gallery contract ------------------------------------
    app_tsx = web_dir / "src" / "App.tsx"
    assert app_tsx.is_file(), f"src/App.tsx missing from scaffold at {app_tsx}"
    app_text = app_tsx.read_text(encoding="utf-8")

    pixel_id_count = app_text.count("data-lost-pixel-id=")
    assert pixel_id_count >= 7, (
        f"App.tsx contains only {pixel_id_count} data-lost-pixel-id= attributes; "
        "expected >= 7 (one per vendored component section). "
        "Lost Pixel plan 07-06 uses these as snapshot targets."
    )

    assert 'from "./config"' in app_text or 'from "@/config"' in app_text, (
        "App.tsx does not import from './config' or '@/config'. "
        "PROJECT_NAME / PROJECT_DESCRIPTION must flow through config.ts.jinja2 "
        "so the Pitfall §1 single-Jinja-file firewall is not broken."
    )
