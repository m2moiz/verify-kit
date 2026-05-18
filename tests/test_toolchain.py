"""
Toolchain tests for verify-kit Plan 01-02.

Tests:
1. test_mise_toml_pins_python_313_and_node_24
   Render the template; assert .mise.toml parses as TOML and pins python=3.13 + node=24.

1b. test_justfile_verify_recipe_passes_flags_literally
   Render the template; assert the justfile contains the literal substring
   `uv run verify-kit verify {{FLAGS}}` — no Jinja artefacts ({% raw %} markers, nested
   braces, etc.) should survive into the consumer project.

2. test_justfile_lists_only_phase_1_recipes
   Render the template; run `just --list` and assert it lists the expected 4 Phase-1
   recipes only (no stubs for unbuilt targets). Skips if `just` is not installed.

3. test_makefile_aliases_verify_to_just
   Render the template; assert Makefile contains `just verify` on a tab-prefixed line
   and that `make -n verify` (dry-run) prints `just verify`. Skips on Windows.

4. test_just_verify_runs_three_checks_end_to_end
   Golden-path test: render → uv sync → just verify → verify-kit verify --format json.
   Gated behind RUN_SLOW_TESTS=1 env var. Requires mise + just + uv on PATH.
"""

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import copier
import pytest


# Shared data for pre-filling prompts in tests.
BASE_DATA = {
    "project_name": "scratch",
    "project_description": "smoke test",
    "author_name": "Test",
    "author_email": "t@t.io",
    "license": "MIT",
    "has_claude_code": False,
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    "has_backend": False,
    "has_llm": False,
    "has_devcontainer": False,
}


def _render_template(template_root: Path, dest: Path) -> None:
    """Render the template into dest with default answers."""
    copier.run_copy(
        str(template_root),
        str(dest),
        data=BASE_DATA,
        defaults=True,
        unsafe=True,
        quiet=True,
    )


# ── Test 1 ────────────────────────────────────────────────────────────────────


def test_mise_toml_pins_python_313_and_node_24(
    template_root: Path, tmp_path: Path
) -> None:
    """Rendered .mise.toml must declare python=3.13 and node=24 under [tools]."""
    scratch = tmp_path / "scratch"
    _render_template(template_root, scratch)

    mise_toml = scratch / ".mise.toml"
    assert mise_toml.exists(), ".mise.toml must be rendered"

    data = tomllib.loads(mise_toml.read_text())

    tools = data.get("tools", {})
    assert tools.get("python") == "3.13", (
        f"Expected python = '3.13' in [tools], got {tools.get('python')!r}"
    )
    assert tools.get("node") == "24", (
        f"Expected node = '24' in [tools], got {tools.get('node')!r}"
    )


# ── Test 1b ───────────────────────────────────────────────────────────────────


def test_justfile_verify_recipe_passes_flags_literally(
    template_root: Path, tmp_path: Path
) -> None:
    """Rendered justfile must contain the literal string `uv run verify-kit verify {{FLAGS}}`
    with NO Jinja artefacts (no {% raw %} markers, no {{ '{{' }} constructs).

    This is the acceptance gate for the {% raw %}...{% endraw %} escaping in Task 1.
    If Copier leaks Jinja syntax into the consumer project, `just verify --fix` would
    break on first invocation.
    """
    scratch = tmp_path / "scratch"
    _render_template(template_root, scratch)

    justfile = scratch / "justfile"
    assert justfile.exists(), "justfile must be rendered"

    content = justfile.read_text()

    # The literal just-side expression must be present
    assert "uv run verify-kit verify {{FLAGS}}" in content, (
        "justfile must contain the literal string 'uv run verify-kit verify {{FLAGS}}'.\n"
        f"Actual justfile content:\n{content}"
    )

    # No Jinja artefacts should survive Copier rendering
    assert "{%" not in content, (
        "Jinja block tag {%...%} must NOT appear in rendered justfile (Copier leaked Jinja syntax)"
    )
    assert "{{ '{{' }}" not in content, (
        "Nested-brace Jinja artefact must NOT appear in rendered justfile"
    )


# ── Test 2 ────────────────────────────────────────────────────────────────────


def test_justfile_lists_only_phase_1_recipes(
    template_root: Path, tmp_path: Path
) -> None:
    """Rendered justfile must expose Phase-1 + Phase-2 (Plan 02-06) recipes and no stubs.

    Skips if `just` binary is not installed (CI may run this job without mise).

    Phase-2 (Plan 02-06) adds verify-clean, trace-up, trace-down, trace.
    """
    if not shutil.which("just"):
        pytest.skip("just binary not installed — mise install required")

    scratch = tmp_path / "scratch"
    _render_template(template_root, scratch)

    result = subprocess.run(
        ["just", "--list"],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`just --list` exited {result.returncode}.\nstderr: {result.stderr}"
    )

    output = result.stdout.lower()

    # Expected Phase-1 + Phase-2 recipes
    for recipe in (
        "verify",
        "lint",
        "format",
        "shell",
        "verify-clean",
        "trace-up",
        "trace-down",
        "trace",
    ):
        assert recipe in output, (
            f"Expected recipe '{recipe}' in `just --list` output.\nOutput:\n{result.stdout}"
        )

    # Forbidden stubs (Area 3 compliance — no stubs for unbuilt targets)
    for stub in ("smoke", "eval", "mutation"):
        assert stub not in output, (
            f"Stub recipe '{stub}' must NOT appear in `just --list` output.\n"
            f"Output:\n{result.stdout}"
        )


# ── Test 3 ────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(sys.platform == "win32", reason="Makefile test skipped on Windows")
def test_makefile_aliases_verify_to_just(
    template_root: Path, tmp_path: Path
) -> None:
    """Rendered Makefile must have `just verify` on a tab-prefixed line and
    `make -n verify` dry-run must print `just verify`."""
    if not shutil.which("make"):
        pytest.skip("make binary not installed")

    scratch = tmp_path / "scratch"
    _render_template(template_root, scratch)

    makefile = scratch / "Makefile"
    assert makefile.exists(), "Makefile must be rendered"

    content = makefile.read_text()
    assert "just verify" in content, "Makefile must contain 'just verify'"

    # Verify the recipe line is tab-prefixed (Make requirement)
    lines = content.splitlines()
    tab_lines = [ln for ln in lines if ln.startswith("\t") and "just verify" in ln]
    assert tab_lines, (
        "Makefile must have a tab-prefixed recipe line containing 'just verify'"
    )

    # Dry-run make to confirm `just verify` is what gets invoked
    result = subprocess.run(
        ["make", "-n", "verify"],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`make -n verify` exited {result.returncode}.\nstderr: {result.stderr}"
    )
    assert "just verify" in result.stdout, (
        f"`make -n verify` output must contain 'just verify'.\nOutput:\n{result.stdout}"
    )


# ── Test 4 (slow / golden-path) ───────────────────────────────────────────────


@pytest.mark.slow
def test_just_verify_runs_three_checks_end_to_end(
    template_root: Path, tmp_path: Path
) -> None:
    """Golden-path test: render → uv sync → just verify → verify-kit --format json.

    Gated behind RUN_SLOW_TESTS=1 environment variable.
    Requires: uv, just on PATH (installed via mise on a dev machine).
    """
    if not os.environ.get("RUN_SLOW_TESTS"):
        pytest.skip("Slow test skipped — set RUN_SLOW_TESTS=1 to run")

    if not shutil.which("just"):
        pytest.skip("just binary not installed — run `mise install` first")

    if not shutil.which("uv"):
        pytest.skip("uv binary not installed")

    scratch = tmp_path / "scratch"
    _render_template(template_root, scratch)

    # Step a: uv sync — creates .venv, resolves deps, installs project in editable mode
    sync_result = subprocess.run(
        ["uv", "sync"],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    assert sync_result.returncode == 0, (
        f"`uv sync` failed (exit {sync_result.returncode}).\n"
        f"stdout: {sync_result.stdout}\nstderr: {sync_result.stderr}"
    )

    # Step b: just verify — exercises the full task-runner surface (TOOL-02/04)
    just_result = subprocess.run(
        ["uv", "run", "just", "verify"],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    assert just_result.returncode == 0, (
        f"`just verify` failed (exit {just_result.returncode}).\n"
        f"stdout: {just_result.stdout}\nstderr: {just_result.stderr}"
    )

    # Step c: verify-kit verify --format json — parse and assert report shape
    json_result = subprocess.run(
        ["uv", "run", "verify-kit", "verify", "--format", "json"],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    # exit_code may be non-zero if checks fail, but JSON output must be parseable
    assert json_result.stdout.strip(), (
        "verify-kit verify --format json must produce JSON output"
    )

    try:
        report = json.loads(json_result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"verify-kit verify --format json produced invalid JSON: {exc}\n"
            f"Output:\n{json_result.stdout}"
        )

    assert "checks" in report, "Report JSON must have 'checks' key"
    assert "exit_code" in report, "Report JSON must have 'exit_code' key"

    check_ids = [c["check_id"] for c in report["checks"]]
    assert "mise-toml-valid" in check_ids, "'mise-toml-valid' check must be present"
    assert "copier-answers-valid" in check_ids, "'copier-answers-valid' check must be present"
    assert "just-list-renders" in check_ids, "'just-list-renders' check must be present"
    assert len(report["checks"]) == 3, (
        f"Expected 3 checks in Phase-1 report, got {len(report['checks'])}: {check_ids}"
    )

    # On a clean scaffold, exit_code must be 0
    assert report["exit_code"] == 0, (
        f"exit_code must be 0 on a clean scaffold.\n"
        f"Checks: {json.dumps(report['checks'], indent=2)}"
    )
