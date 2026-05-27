# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Bidirectional web add-on polarity tests (Plans 07-01 through 07-08).

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

Plan 07-04: Adds a 4-combo (has_web x has_backend) polarity test:
  - Vite proxy block is present iff has_web=True and has_backend=True.
  - events.ts exists iff has_web=True and has_backend=True.
  - justfile `dev:` recipe is present in the right polarity.
  - expose_headers in app/main.py iff has_web=True (when has_backend=True).

Plan 07-05: Vitest + Playwright infrastructure:
  - pnpm exec vitest run exits 0 with >= 2 passing tests in scratch scaffold.
  - Playwright smoke test exits 0 (skippable via VERIFY_KIT_SKIP_PLAYWRIGHT=1).
  - TRACE-03 (trace.ts fixture header-only): trace.ts must NOT import the OTel SDK.
    The test fixture injects W3C traceparent headers only; the production SDK lives
    in src/otel.ts (see Plan 07-08 below).
  - App.test.tsx and DarkModeToggle.test.tsx exist in the rendered scaffold.

Plan 07-08: Browser OTel SDK (gap closure — TRACE-01 / TRACE-02 / TRACE-04):
  - @opentelemetry/sdk-trace-web ships in production package.json (TRACE-01).
  - src/otel.ts (plain .ts, NOT .ts.jinja2) activates the SDK only when
    VITE_OTEL_EXPORTER_OTLP_ENDPOINT is set at build time (TRACE-02).
  - OTel-on vs OTel-off bundle delta is <= 100 KB gzipped (TRACE-04).
    Skip: VERIFY_KIT_SKIP_BUNDLE_BUDGET=1 (heavy double-build; CI always runs).

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
import os
import re
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


def _render(tmp_path: Path, *, has_web: bool, has_backend: bool = False) -> Path:
    """Render the template with polarity axes: has_web and has_backend.

    Passes ``_vcs_ref="HEAD"`` so Copier uses the current worktree HEAD rather
    than the latest released tag (v0.1.0). The has_web prompt was added in
    Plan 07-01, after the v0.1.0 release; without this override Copier would
    clone the tag and silently omit has_web from the answer context, causing
    the Guard-2 conditional directory to resolve to an empty string.
    """
    return render_scratch_project(
        tmp_path,
        _vcs_ref="HEAD",
        **{**_BASE, "has_web": has_web, "has_backend": has_backend},  # type: ignore[arg-type]
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


@pytest.mark.parametrize(
    "has_web,has_backend",
    [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)
def test_web_backend_four_combos(tmp_path: Path, has_web: bool, has_backend: bool) -> None:
    """Plan 07-04: All 4 (has_web x has_backend) polarity combos render correctly.

    Asserts the following matrix of structural properties:

    | has_web | has_backend | proxy in vite.config? | events.ts? | dev: in justfile? | expose_headers in main.py? | web/ exists? |
    |---------|-------------|----------------------|------------|-------------------|----------------------------|--------------|
    | False   | False       | n/a                  | n/a        | No                | n/a                        | No           |
    | False   | True        | n/a                  | n/a        | Yes (uvicorn)     | No                         | No           |
    | True    | False       | No                   | No         | Yes (vite-only)   | n/a                        | Yes          |
    | True    | True        | Yes                  | Yes        | Yes (mprocs)      | Yes                        | Yes          |

    The build-smoke (pnpm install + tsc + build) runs only on the True/False and
    True/True combos where has_web=True (the two has_web=False combos are cheap
    absence-checks that return early without Node invocation).

    Design: for has_web=False combos the test asserts web/ dir is absent and
    returns early — no pnpm steps needed. This keeps total wall-clock roughly
    equal to the 07-02/07-03 baseline (still one full build; three new combos
    add < 5s aggregate for the absence checks).
    """
    scratch = _render(tmp_path, has_web=has_web, has_backend=has_backend)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    web_dir = scratch / "web"
    justfile_path = scratch / "justfile"

    # ── Combo-invariant: web/ directory presence ──────────────────────────────
    if has_web:
        assert web_dir.is_dir(), (
            f"web/ must exist when has_web=True (combo has_web={has_web}, "
            f"has_backend={has_backend})"
        )
    else:
        assert not web_dir.exists(), (
            f"web/ must NOT exist when has_web=False (combo has_web={has_web}, "
            f"has_backend={has_backend})"
        )
        # Cheap absence combo: assert justfile dev: + early return (no pnpm needed)
        assert justfile_path.is_file(), "justfile must always be present"
        justfile_text = justfile_path.read_text(encoding="utf-8")
        if has_backend:
            # (False, True): backend-only dev recipe (uvicorn), no mprocs
            assert "\ndev:\n" in justfile_text, (
                "justfile must have a 'dev:' recipe when has_backend=True (uvicorn-only path)"
            )
            assert "mprocs" not in justfile_text, (
                "justfile must NOT have mprocs when has_web=False (only web+backend needs it)"
            )
            # TRACE-04: expose_headers NOT present when has_web=False
            main_py = scratch / "app" / "main.py"
            assert main_py.is_file(), "app/main.py must exist when has_backend=True"
            assert "expose_headers" not in main_py.read_text(encoding="utf-8"), (
                "expose_headers must NOT appear in main.py when has_web=False "
                "(TRACE-04: only added under has_web=True conditional)"
            )
        else:
            # (False, False): no dev recipe at all
            assert "\ndev:\n" not in justfile_text, (
                "justfile must NOT have a 'dev:' recipe when has_web=False and has_backend=False"
            )
        return  # no Node steps needed for has_web=False combos

    # ── has_web=True combos: check rendered files ─────────────────────────────
    vite_config = web_dir / "vite.config.ts"
    assert vite_config.is_file(), f"vite.config.ts missing at {vite_config}"
    vite_text = vite_config.read_text(encoding="utf-8")

    events_ts = web_dir / "src" / "lib" / "events.ts"
    justfile_text = justfile_path.read_text(encoding="utf-8")

    if has_backend:
        # (True, True): proxy + events.ts + mprocs dev recipe + expose_headers
        assert "proxy" in vite_text, (
            "vite.config.ts must contain a proxy block when has_backend=True "
            "(Vite dev → FastAPI :8000)"
        )
        assert events_ts.is_file(), (
            "src/lib/events.ts must exist when has_web=True and has_backend=True "
            "(SSE bypass-proxy subscriber; Pitfall §5)"
        )
        assert "http://localhost:8000/__debug/events" in events_ts.read_text(encoding="utf-8"), (
            "events.ts must use absolute URL to bypass Vite proxy buffering (Pitfall §5)"
        )
        assert "\ndev:\n" in justfile_text, (
            "justfile must have a 'dev:' recipe for the web+backend combo"
        )
        assert "mprocs" in justfile_text, (
            "justfile dev: recipe must use mprocs for web+backend combo (D-W06)"
        )
        # TRACE-04: expose_headers present when has_web=True
        main_py = scratch / "app" / "main.py"
        assert main_py.is_file(), "app/main.py must exist when has_backend=True"
        assert "expose_headers" in main_py.read_text(encoding="utf-8"), (
            "expose_headers must appear in main.py when has_web=True (TRACE-04)"
        )
    else:
        # (True, False): no proxy, no events.ts, vite-only dev recipe, no mprocs
        assert "proxy" not in vite_text, (
            "vite.config.ts must NOT contain a proxy block when has_backend=False "
            "(frontend-only mode D-W04)"
        )
        assert not events_ts.exists(), (
            "src/lib/events.ts must NOT exist when has_backend=False "
            "(file-level Guard-1 exclude in copier.yml)"
        )
        assert "\ndev:\n" in justfile_text, (
            "justfile must have a 'dev:' recipe for web-only combo (pnpm --dir web dev)"
        )
        assert "mprocs" not in justfile_text, (
            "justfile must NOT have mprocs when has_web=True but has_backend=False "
            "(mprocs only needed for parallel dev)"
        )

    # ── Build smoke: runs only for has_web=True combos ────────────────────────
    if shutil.which("node") is None:
        pytest.skip("Node required for build smoke")

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
        ["pnpm", "exec", "tsc", "--noEmit"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=60,
    )

    subprocess.run(
        ["pnpm", "build"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=120,
    )

    dist_index = web_dir / "dist" / "index.html"
    assert dist_index.is_file(), (
        f"pnpm build succeeded but dist/index.html is missing at {dist_index}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required")
def test_web_vitest_and_playwright(tmp_path: Path) -> None:
    """Plan 07-05: Vitest + Playwright infrastructure assertions.

    Uses the (has_web=True, has_backend=False) scratch scaffold — the cheapest
    combo that exercises the full test infrastructure.

    Assertions in three tiers (cheapest first):

    Tier 1 (file-level guards):
      - src/__tests__/App.test.tsx exists (07-05 Task 1 contract).
      - src/__tests__/DarkModeToggle.test.tsx exists (07-05 Task 1 contract).

    Tier 2 (trace fixture safety — TRACE-03):
      - tests/e2e/fixtures/trace.ts contains NO "@opentelemetry/sdk-trace-web"
        or "sdk-trace-web" reference (header-only, no SDK; deferred to v0.3).

    Tier 3 (runtime — skippable):
      - ``pnpm exec vitest run`` exits 0 with >= 2 passing tests.
      - (Optional, skipped by default for fast local runs via
        VERIFY_KIT_SKIP_PLAYWRIGHT=1) ``pnpm exec playwright install --with-deps
        chromium`` + ``pnpm exec playwright test`` exit 0.

    Cache hint for CI (07-07): cache ~/.cache/ms-playwright keyed by
    @playwright/test version from ``pnpm list --json @playwright/test``.
    """
    scratch = _render(tmp_path, has_web=True)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    web_dir = scratch / "web"
    assert web_dir.is_dir(), "web/ dir must exist for has_web=True"

    # ── Tier 1: file-level guards ─────────────────────────────────────────────
    app_test = web_dir / "src" / "__tests__" / "App.test.tsx"
    assert app_test.is_file(), (
        f"src/__tests__/App.test.tsx missing from rendered scaffold at {app_test}. "
        "Check that template/web/src/__tests__/App.test.tsx is committed."
    )

    toggle_test = web_dir / "src" / "__tests__" / "DarkModeToggle.test.tsx"
    assert toggle_test.is_file(), (
        f"src/__tests__/DarkModeToggle.test.tsx missing from rendered scaffold at {toggle_test}. "
        "Check that template/web/src/__tests__/DarkModeToggle.test.tsx is committed."
    )

    # ── Tier 2: trace fixture safety (TRACE-03) ───────────────────────────────
    # The FIXTURE stays header-only — it is the Playwright W3C traceparent
    # injector and must NOT import the OTel SDK.
    # The production SDK lives in src/otel.ts (see OTel-present assertions below).
    trace_fixture = web_dir / "tests" / "e2e" / "fixtures" / "trace.ts"
    assert trace_fixture.is_file(), (
        f"tests/e2e/fixtures/trace.ts missing from rendered scaffold at {trace_fixture}. "
        "Check that template/web/tests/e2e/fixtures/trace.ts is committed."
    )
    trace_text = trace_fixture.read_text(encoding="utf-8")
    # TRACE-03: no SDK import in the FIXTURE — comments mentioning the package
    # name are fine, but there must be no actual import/require of the OTel SDK
    # in trace.ts.  The SDK ships in production src/otel.ts (TRACE-01, 07-08).
    otel_sdk_import = re.search(
        r'^\s*(import\s|require\s*\()\s*[\'"]@opentelemetry/sdk-trace-web[\'"]',
        trace_text,
        re.MULTILINE,
    )
    assert otel_sdk_import is None, (
        "trace.ts imports '@opentelemetry/sdk-trace-web' — this test fixture must "
        "stay header-only (TRACE-03). The production SDK lives in src/otel.ts."
    )

    # ── Tier 2b: OTel-present assertions (TRACE-01 / TRACE-02 — Plan 07-08) ──
    # The production web package.json must contain the OTel SDK packages.
    pkg_json = web_dir / "package.json"
    assert pkg_json.is_file(), f"package.json missing from rendered scaffold: {pkg_json}"
    pkg_text = pkg_json.read_text(encoding="utf-8")
    assert "@opentelemetry/sdk-trace-web" in pkg_text, (
        "Rendered web/package.json does not contain '@opentelemetry/sdk-trace-web'. "
        "The OTel SDK must ship in production dependencies (TRACE-01, Plan 07-08)."
    )
    assert "@opentelemetry/instrumentation-fetch" in pkg_text, (
        "Rendered web/package.json does not contain '@opentelemetry/instrumentation-fetch'. "
        "Fetch auto-instrumentation must be included (TRACE-02, Plan 07-08)."
    )

    # src/otel.ts must exist as a plain .ts file (NOT .ts.jinja2 — Pitfall §1).
    otel_ts = web_dir / "src" / "otel.ts"
    otel_ts_jinja = web_dir / "src" / "otel.ts.jinja2"
    assert otel_ts.is_file(), (
        f"src/otel.ts missing from rendered scaffold at {otel_ts}. "
        "The inert-by-default OTel init file must exist (TRACE-01, Plan 07-08)."
    )
    assert not otel_ts_jinja.exists(), (
        "src/otel.ts.jinja2 found — Pitfall §1 violation. Only vite.config.ts.jinja2 "
        "and src/config.ts.jinja2 may carry .jinja2; use plain .ts for otel.ts."
    )

    otel_ts_text = otel_ts.read_text(encoding="utf-8")
    assert "VITE_OTEL_EXPORTER_OTLP_ENDPOINT" in otel_ts_text, (
        "src/otel.ts does not reference VITE_OTEL_EXPORTER_OTLP_ENDPOINT. "
        "The inert-by-default guard must check this env var (TRACE-02, Plan 07-08)."
    )
    # src/otel.ts must actually import the SDK (not just reference it in a comment).
    otel_sdk_init = re.search(
        r'^\s*import\s.*[\'"]@opentelemetry/sdk-trace-web[\'"]',
        otel_ts_text,
        re.MULTILINE,
    )
    assert otel_sdk_init is not None, (
        "src/otel.ts does not import '@opentelemetry/sdk-trace-web'. "
        "The production OTel init must use the SDK (TRACE-01, Plan 07-08)."
    )

    # main.tsx must call initOtel() before createRoot.
    main_tsx = web_dir / "src" / "main.tsx"
    assert main_tsx.is_file(), f"src/main.tsx missing from rendered scaffold: {main_tsx}"
    assert "initOtel" in main_tsx.read_text(encoding="utf-8"), (
        "src/main.tsx does not call initOtel(). "
        "OTel must be initialised before React mounts (Plan 07-08)."
    )

    # ── Tier 3: runtime Vitest + Playwright ───────────────────────────────────
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

    # Build first so vite preview has something to serve (required for Playwright)
    subprocess.run(
        ["pnpm", "build"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=120,
    )

    # --- Vitest run (always runs) ---
    vitest_result = subprocess.run(
        ["pnpm", "exec", "vitest", "run"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert vitest_result.returncode == 0, (
        f"pnpm exec vitest run failed (exit {vitest_result.returncode}).\n"
        f"stdout: {vitest_result.stdout[-2000:]}\n"
        f"stderr: {vitest_result.stderr[-1000:]}"
    )

    # Parse number of passing tests from vitest output.
    # Vitest prints: "Tests  N passed (N)" or "Tests  X failed | N passed (T)"
    stdout = vitest_result.stdout + vitest_result.stderr
    passed_match = re.search(r"(\d+)\s+passed", stdout)
    passed_count = int(passed_match.group(1)) if passed_match else 0
    assert passed_count >= 2, (
        f"vitest run passed only {passed_count} test(s); expected >= 2 "
        f"(App.test.tsx x2 + DarkModeToggle.test.tsx x1).\n"
        f"Output: {stdout[-2000:]}"
    )

    # --- Playwright (skippable for fast local runs) ---
    skip_playwright = os.environ.get("VERIFY_KIT_SKIP_PLAYWRIGHT") == "1"
    if skip_playwright:
        return  # opt-out — CI always runs this

    # Install Chromium browser binaries (cached in CI via ~/.cache/ms-playwright)
    subprocess.run(
        ["pnpm", "exec", "playwright", "install", "--with-deps", "chromium"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=300,
    )

    # Run Playwright smoke spec
    subprocess.run(
        ["pnpm", "exec", "playwright", "test"],
        cwd=str(web_dir),
        env={**_CLEAN_ENV, "CI": "1"},  # CI=1 → single worker, no server reuse
        check=True,
        timeout=120,
    )


def test_web_ci_matrix_shape() -> None:
    """Plan 07-07: CI matrix assertions for template-selftest.yml.

    Asserts:
      1. All 6 expected combos appear in the matrix.combo list.
      2. +web+llm is NOT in the matrix (explicitly skipped per CONTEXT.md).
      3. timeout-minutes: 20 is set on the job.
      4. fail-fast: false is set on the strategy.
    """
    import yaml

    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "template-selftest.yml"
    assert workflow_path.is_file(), f"template-selftest.yml not found at {workflow_path}"

    with open(workflow_path, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    job = workflow["jobs"]["selftest"]

    # 3. timeout-minutes: 20
    assert job.get("timeout-minutes") == 20, (
        f"job.timeout-minutes should be 20; got {job.get('timeout-minutes')!r}"
    )

    # 4. fail-fast: false
    strategy = job.get("strategy", {})
    assert strategy.get("fail-fast") is False, (
        f"strategy.fail-fast should be false; got {strategy.get('fail-fast')!r}"
    )

    # 1. All 6 expected combos in matrix.combo
    combo_list = strategy.get("matrix", {}).get("combo", [])
    expected_combos = {"base", "backend", "llm", "web", "backend-web", "full"}
    present_combos = set(combo_list)
    missing = expected_combos - present_combos
    assert not missing, (
        f"Expected combos missing from matrix.combo: {sorted(missing)}. "
        f"Present: {sorted(present_combos)}"
    )

    # 2. +web+llm is NOT in the matrix (explicitly skipped)
    assert "web-llm" not in present_combos and "llm-web" not in present_combos, (
        "web+llm combo should NOT be in the matrix (non-realistic combo per CONTEXT.md). "
        f"Present combos: {sorted(present_combos)}"
    )


def test_web_cli_surface_guard() -> None:
    """Plan 07-07: CLI-surface regression guards.

    Asserts:
      1. No --check='web.*' or --check="web.*" glob in template/justfile.jinja2.
         (HIGH-1 regression guard: CLI does exact match only per core.py:101.)
      2. verify-web and verify-web-quick recipe bodies begin with `uv run verify-kit verify`.
         (HIGH-6 regression guard: bare `verify-kit` is not on PATH in scratch scaffolds.)
    """
    justfile = Path(__file__).parent.parent / "template" / "justfile.jinja2"
    assert justfile.is_file(), f"template/justfile.jinja2 not found at {justfile}"
    text = justfile.read_text(encoding="utf-8")

    # Guard 1: no glob --check= pattern
    assert "--check='web.*'" not in text, (
        "justfile.jinja2 contains --check='web.*' glob — CLI does exact match only "
        "(core.py.jinja2:101 uses by_id.get(cid)). Enumerate each check ID explicitly."
    )
    assert '--check="web.*"' not in text, (
        'justfile.jinja2 contains --check="web.*" glob — same issue as above.'
    )

    # Guard 2: verify-web and verify-web-quick recipe bodies use `uv run verify-kit verify`
    lines = text.splitlines()
    in_verify_web = False
    in_verify_web_quick = False
    for line in lines:
        if re.match(r"^verify-web:", line) and "quick" not in line:
            in_verify_web = True
            in_verify_web_quick = False
            continue
        if re.match(r"^verify-web-quick:", line):
            in_verify_web_quick = True
            in_verify_web = False
            continue
        # Recipe ends when a non-indented non-empty line appears (new recipe or Jinja block)
        if line and not line[0].isspace() and not line.startswith("{"):
            in_verify_web = False
            in_verify_web_quick = False

        if in_verify_web and line.strip():
            assert "uv run verify-kit verify" in line, (
                f"verify-web recipe body must use 'uv run verify-kit verify'; got: {line!r}"
            )
            in_verify_web = False  # only check first non-empty body line
        if in_verify_web_quick and line.strip():
            assert "uv run verify-kit verify" in line, (
                f"verify-web-quick recipe body must use 'uv run verify-kit verify'; got: {line!r}"
            )
            in_verify_web_quick = False


def test_web_preset_schema_coverage() -> None:
    """Plan 07-07: Preset schema coverage assertion.

    Runs the same logic as preset-schema-check.yml inline:
      - Both public presets have _schema_version: "0.2"
      - Both presets cover all non-computed copier.yml prompt keys
      - No surplus keys (typo guard)
    """
    import yaml

    repo_root = Path(__file__).parent.parent
    copier_yml = repo_root / "copier.yml"
    presets_dir = repo_root / "presets"

    assert copier_yml.is_file(), f"copier.yml not found at {copier_yml}"
    assert presets_dir.is_dir(), f"presets/ directory not found at {presets_dir}"

    COPIER_INTERNAL_KEYS = {
        "_subdirectory", "_jinja_extensions", "_answers_file",
        "_templates_suffix", "_min_copier_version", "_envops",
        "_exclude", "_tasks", "_message_before_copy", "_message_after_copy",
    }
    SCHEMA_VERSION = "0.2"

    with open(copier_yml, encoding="utf-8") as f:
        copier_data = yaml.safe_load(f)

    prompt_keys = set()
    for key, val in copier_data.items():
        if key in COPIER_INTERNAL_KEYS or key.startswith("_"):
            continue
        # Skip computed prompts (when: false) — auto-derived from other prompts
        if isinstance(val, dict) and val.get("when") is False:
            continue
        prompt_keys.add(key)

    assert prompt_keys, "No prompt keys found in copier.yml — check COPIER_INTERNAL_KEYS filter"

    preset_files = sorted(presets_dir.glob("*.yml"))
    preset_files = [p for p in preset_files if not p.name.endswith(".local.yml")]
    assert len(preset_files) >= 2, (
        f"Expected at least 2 public preset files in presets/; found {len(preset_files)}: "
        + ", ".join(p.name for p in preset_files)
    )

    errors: list[str] = []
    for preset_path in preset_files:
        with open(preset_path, encoding="utf-8") as f:
            preset_data = yaml.safe_load(f)

        schema_version = preset_data.get("_schema_version")
        if schema_version != SCHEMA_VERSION:
            errors.append(
                f"{preset_path.name}: _schema_version is {schema_version!r}; "
                f"expected {SCHEMA_VERSION!r}"
            )

        preset_keys = {k for k in preset_data if not k.startswith("_")}
        missing_keys = prompt_keys - preset_keys
        if missing_keys:
            errors.append(
                f"{preset_path.name}: missing copier.yml keys: {sorted(missing_keys)}"
            )
        surplus_keys = preset_keys - prompt_keys
        if surplus_keys:
            errors.append(
                f"{preset_path.name}: surplus keys (typo?): {sorted(surplus_keys)}"
            )

    assert not errors, (
        "Preset schema check failed:\n" + "\n".join(f"  {e}" for e in errors)
    )


def test_web_otel_bundle_budget(tmp_path: pytest.TempPathFactory) -> None:
    """TRACE-04: OTel-on bundle delta is <= 100 KB gzipped.

    Performs two pnpm builds of a scratch scaffold web/:

    Build A: VITE_OTEL_EXPORTER_OTLP_ENDPOINT unset (inert default).
    Build B: VITE_OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318/v1/traces"
             (active OTel path — tree-shaking cannot drop the exporter code).

    For each build, gzips every dist/assets/*.js chunk and sums the gzipped
    bytes.  Asserts (sum_B − sum_A) ≤ 100 KB (102400 bytes) — TRACE-04.

    Skip guard:
      Set VERIFY_KIT_SKIP_BUNDLE_BUDGET=1 to skip the double-build cost for fast
      local runs.  CI always runs this (no skip flag set).  The skip flag is
      analogous to VERIFY_KIT_SKIP_PLAYWRIGHT.
    """
    import gzip

    if os.environ.get("VERIFY_KIT_SKIP_BUNDLE_BUDGET") == "1":
        pytest.skip("VERIFY_KIT_SKIP_BUNDLE_BUDGET=1 — skipping double-build OTel budget guard")

    scratch = _render(tmp_path, has_web=True)
    web_dir = scratch / "web"
    assert web_dir.is_dir(), f"web/ dir must exist: {web_dir}"

    # Install once; reuse node_modules across both builds.
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

    def _gzip_js_size(dist_dir: Path) -> int:
        """Sum gzipped sizes of all dist/assets/*.js chunks."""
        total = 0
        for js_file in dist_dir.glob("assets/*.js"):
            data = js_file.read_bytes()
            total += len(gzip.compress(data, compresslevel=9))
        return total

    # ── Build A: inert (no OTel exporter activated) ───────────────────────────
    subprocess.run(
        ["pnpm", "build"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=180,
    )
    size_a = _gzip_js_size(web_dir / "dist")

    # ── Build B: OTel active (exporter endpoint set) ──────────────────────────
    otel_env = {**_CLEAN_ENV, "VITE_OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318/v1/traces"}
    subprocess.run(
        ["pnpm", "build"],
        cwd=str(web_dir),
        env=otel_env,
        check=True,
        timeout=180,
    )
    size_b = _gzip_js_size(web_dir / "dist")

    # ── TRACE-04 assertion ────────────────────────────────────────────────────
    delta = size_b - size_a
    assert delta <= 102400, (  # 100 * 1024 bytes
        f"OTel-on build is {delta / 1024:.1f} KB gzipped larger than inert build; "
        f"expected <= 100 KB (TRACE-04).  "
        f"Inert size: {size_a / 1024:.1f} KB, OTel-on size: {size_b / 1024:.1f} KB."
    )


@pytest.mark.skipif(
    os.environ.get("VERIFY_KIT_SKIP_E2E") == "1",
    reason="opt-out for fast local runs (set VERIFY_KIT_SKIP_E2E=1)",
)
@pytest.mark.skipif(shutil.which("node") is None, reason="Node required")
def test_web_verify_web_quick_boss_test(tmp_path: Path) -> None:
    """Plan 07-07: End-to-end boss test — render scaffold + just verify-web-quick.

    Proves the full pipeline: has_web prompt -> bounded path-shapes -> adapters
    -> registry -> CLI -> recipe -> exit 0.

    Uses has_web=true, has_backend=false (cheapest combo; no Docker needed).
    Runs just verify-web-quick (NOT verify-web — skips Lighthouse + Lost Pixel
    which require Chrome/Docker and are too slow for unit test budget).

    Gate: VERIFY_KIT_SKIP_E2E=1 skips this test for devs without Node.
    """
    scratch = _render(tmp_path, has_web=True)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    web_dir = scratch / "web"
    assert web_dir.is_dir(), "web/ dir must exist for has_web=True"

    # Install pnpm dependencies
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

    # Install Playwright Chromium (needed for web.playwright and web.axe checks)
    subprocess.run(
        ["pnpm", "exec", "playwright", "install", "--with-deps", "chromium"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=300,
    )

    # Build the web app first (vite preview needs dist/)
    subprocess.run(
        ["pnpm", "build"],
        cwd=str(web_dir),
        env=_CLEAN_ENV,
        check=True,
        timeout=120,
    )

    # Boss test: just verify-web-quick must exit 0
    result = subprocess.run(
        ["just", "verify-web-quick"],
        cwd=str(scratch),
        env=_CLEAN_ENV,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"just verify-web-quick failed (exit {result.returncode}).\n"
        f"stdout: {result.stdout[-3000:]}\n"
        f"stderr: {result.stderr[-1000:]}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required")
def test_web_harness_registry_smoke(tmp_path: Path) -> None:
    """Plan 07-06: registry smoke + adapter contract guards in scratch scaffold.

    Assertions:
      1. Registry smoke: python -c 'from harness.registry import list_checks;...'
         returns all 5 web.* check IDs.
      2. scaffold pytest tests/web/ passes (4 adapter + registry tests).
      3. Forbidden-kwarg guard: web.py has zero severity=/tags=/readOnlyHint= etc.
      4. ErrorEnvelope(fixable=) guard: no adapters pass fixable= to ErrorEnvelope.

    Uses (has_web=True, has_backend=False) scratch scaffold — cheapest combo
    that exercises the full harness.web subpackage.
    """
    scratch = _render(tmp_path, has_web=True)
    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    web_dir = scratch / "web"
    assert web_dir.is_dir(), "web/ dir must exist for has_web=True"

    # --- pnpm install for later runtime checks ---
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

    # --- Assertion 1: Registry smoke ----------------------------------------
    registry_check = subprocess.run(
        [
            "python", "-c",
            (
                "from harness.registry import list_checks; "
                "ids = sorted(c.check_id for c in list_checks()); "
                "expected = ['web.axe', 'web.lighthouse', 'web.lost_pixel', "
                "            'web.playwright', 'web.vitest']; "
                "missing = [x for x in expected if x not in ids]; "
                "assert not missing, f'Missing web checks: {missing}'"
            ),
        ],
        cwd=str(scratch),
        env=_CLEAN_ENV,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert registry_check.returncode == 0, (
        f"Registry smoke failed (exit {registry_check.returncode}).\n"
        f"stdout: {registry_check.stdout}\nstderr: {registry_check.stderr}"
    )

    # --- Assertion 2: Scaffold pytest tests/web/ ----------------------------
    pytest_result = subprocess.run(
        ["uv", "run", "pytest", "tests/web/", "-q", "--tb=short"],
        cwd=str(scratch),
        env=_CLEAN_ENV,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert pytest_result.returncode == 0, (
        f"scaffold pytest tests/web/ failed (exit {pytest_result.returncode}).\n"
        f"stdout: {pytest_result.stdout[-3000:]}\nstderr: {pytest_result.stderr[-1000:]}"
    )

    # --- Assertion 3: Forbidden-kwarg guard on web.py -----------------------
    web_py = scratch / "harness" / "checks" / "web.py"
    assert web_py.is_file(), f"harness/checks/web.py not found in scaffold at {web_py}"
    web_py_text = web_py.read_text(encoding="utf-8")

    forbidden_kwargs = ["severity=", "tags=", "readOnlyHint=", "destructiveHint=", "destructive="]
    for kw in forbidden_kwargs:
        # Check only within actual @register call blocks (not docstring comments)
        register_calls = re.findall(r"@register\((.*?)\)", web_py_text, re.DOTALL)
        for call_body in register_calls:
            assert kw not in call_body, (
                f"Forbidden kwarg '{kw}' found in a @register() call in "
                f"harness/checks/web.py. REVIEW-CHECKLIST §4 / FROZEN API surface. "
                f"Call body: {call_body[:80]!r}"
            )

    # --- Assertion 4: ErrorEnvelope(fixable=) guard on all adapters ---------
    adapter_dir = scratch / "harness" / "web"
    assert adapter_dir.is_dir(), f"harness/web/ not found in scaffold at {adapter_dir}"

    for adapter_file in adapter_dir.glob("*.py"):
        if adapter_file.name.startswith("_") and adapter_file.name != "_env.py":
            continue
        source = adapter_file.read_text(encoding="utf-8")
        match = re.search(r"ErrorEnvelope\([^)]*fixable", source)
        assert match is None, (
            f"Found ErrorEnvelope(...fixable=...) in {adapter_file.name} at "
            f"char {match.start()} — REVIEW-CHECKLIST §4 violation. "
            "Per-check fixability lives on @register(fixable=...) only."
        )
