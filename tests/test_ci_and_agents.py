# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for CI workflow templates and agent integration files (Plan 01-04).

Covers:
  - CI-01: ci.yml ≤20 effective lines
  - CI-03: act can parse and list workflows
  - CI-04: cache step covers uv/pnpm/pre-commit paths
  - AGT-01: AGENTS.md is substantive (≥40 non-blank lines)
  - Area 4: per-agent thin-pointer files are conditional (Form B) and ≤200 words
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


# ─── Shared helpers ──────────────────────────────────────────────────────────

COMMON_DATA = {
    "project_name": "test-project",
    "project_description": "A test project",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
}

# All-agents-on data
ALL_AGENTS_DATA = {
    **COMMON_DATA,
    "has_claude_code": True,
    "has_cursor": True,
    "has_windsurf": True,
    "has_copilot": True,
    "has_zed": False,
    "has_continue": False,
    "has_backend": False,
    "has_llm": False,
}


def _render(template_root: Path, dest: Path, extra_data: dict | None = None) -> Path:
    """Run copier.run_copy with COMMON_DATA merged with extra_data."""
    import copier

    data = {**COMMON_DATA, **(extra_data or {})}
    copier.run_copy(
        str(template_root),
        str(dest),
        data=data,
        defaults=True,
        unsafe=True,
        overwrite=True,
    )
    return dest


class _WorkflowLoader(yaml.SafeLoader):
    """SafeLoader variant that does NOT coerce on/off/yes/no to booleans.

    PyYAML uses YAML 1.1 by default, which treats bare `on` as True.
    This loader overrides that by registering a string resolver for those tokens.
    """


_WorkflowLoader.add_implicit_resolver(
    "tag:yaml.org,2002:str",
    re.compile(r"^(?:on|off|yes|no|Yes|No|ON|OFF|YES|NO)$"),
    list("oOyYnN"),
)


def _load_workflow(path: Path) -> dict:
    """Parse a workflow YAML file with the no-boolean-coercion loader."""
    return yaml.load(path.read_text(), Loader=_WorkflowLoader)  # noqa: S506


def _count_effective_lines(text: str) -> int:
    """Count non-blank, non-comment lines after stripping raw/endraw markers."""
    lines = text.splitlines()
    stripped = [
        ln for ln in lines
        if ln.strip()  # not blank
        and not ln.strip().startswith("#")  # not a comment
        and ln.strip() not in ("{% raw %}", "{% endraw %}")  # not raw markers
    ]
    return len(stripped)


# ─── Test 1: CI line count ───────────────────────────────────────────────────


def test_ci_yml_is_at_most_20_lines(template_root: Path, tmp_path: Path) -> None:
    """ci.yml renders to ≤20 effective lines (CI-01 relaxed cap)."""
    scratch = tmp_path / "ci-lines"
    _render(template_root, scratch, COMMON_DATA)
    ci_file = scratch / ".github" / "workflows" / "ci.yml"
    assert ci_file.exists(), "ci.yml should always be rendered"
    count = _count_effective_lines(ci_file.read_text())
    assert count <= 20, (
        f"ci.yml has {count} effective lines; must be ≤20 (CI-01 relaxed cap). "
        "Add a Phase-6 composite action if this grows further."
    )


# ─── Test 2: CI workflow YAML validity ───────────────────────────────────────


def test_ci_yml_is_valid_workflow_yaml(template_root: Path, tmp_path: Path) -> None:
    """ci.yml parses as valid YAML with correct structure and required steps."""
    scratch = tmp_path / "ci-yaml"
    _render(template_root, scratch, COMMON_DATA)
    ci_file = scratch / ".github" / "workflows" / "ci.yml"

    data = _load_workflow(ci_file)

    # Top-level keys — "on" must be a STRING key (not True from YAML 1.1 coercion)
    assert "name" in data, "'name' key missing from ci.yml"
    assert "on" in data, (
        "'on' key not found as a STRING in ci.yml — check both the file quoting and loader"
    )
    assert "jobs" in data, "'jobs' key missing from ci.yml"

    steps = data["jobs"]["verify"]["steps"]
    assert steps, "verify job should have at least one step"

    uses_values = [s.get("uses", "") for s in steps]
    assert any("jdx/mise-action@v2" in u for u in uses_values), (
        "ci.yml must use jdx/mise-action@v2 (mise is the single toolchain source)"
    )

    run_values = [s.get("run", "") for s in steps if "run" in s]
    assert any("just verify" in r for r in run_values), (
        "ci.yml must have a step running `just verify`"
    )
    assert any("uv sync" in r for r in run_values), (
        "ci.yml must have a step running `uv sync` (explicit sync per quickstart)"
    )


# ─── Test 3: CI caching ───────────────────────────────────────────────────────


def test_ci_yml_caches_uv_pnpm_precommit(template_root: Path, tmp_path: Path) -> None:
    """ci.yml cache step covers ~/.cache/uv, ~/.cache/pnpm, ~/.cache/pre-commit (CI-04)."""
    scratch = tmp_path / "ci-cache"
    _render(template_root, scratch, COMMON_DATA)
    ci_file = scratch / ".github" / "workflows" / "ci.yml"

    data = _load_workflow(ci_file)
    steps = data["jobs"]["verify"]["steps"]

    cache_steps = [s for s in steps if "actions/cache" in s.get("uses", "")]
    assert cache_steps, "ci.yml must have an actions/cache step for CI-04"

    combined_paths = "\n".join(
        s.get("with", {}).get("path", "") for s in cache_steps
    )
    for required_path in ("~/.cache/uv", "~/.cache/pnpm", "~/.cache/pre-commit"):
        assert required_path in combined_paths, (
            f"CI-04: cache step must include path '{required_path}'"
        )


# ─── Test 4: act dry-run ─────────────────────────────────────────────────────


def test_workflows_pass_act_dryrun(template_root: Path, tmp_path: Path) -> None:
    """act -l can parse and list both workflows without errors (CI-03)."""
    act_bin = shutil.which("act")
    if act_bin is None:
        pytest.skip("act not installed — skipping CI-03 local-runnability check")

    scratch = tmp_path / "ci-act"
    _render(template_root, scratch, COMMON_DATA)

    result = subprocess.run(
        [act_bin, "-l"],
        cwd=str(scratch),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"act -l failed (exit {result.returncode}).\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ─── Test 5: AGENTS.md substantive, per-agent files thin ────────────────────


def test_agents_md_is_substantive_and_per_agent_files_are_thin(
    template_root: Path, tmp_path: Path
) -> None:
    """AGENTS.md is ≥40 non-blank lines; each per-agent file is ≤200 words; all reference AGENTS.md."""
    scratch = tmp_path / "agents-check"
    _render(template_root, scratch, ALL_AGENTS_DATA)

    # AGENTS.md substantive check
    agents_md = scratch / "AGENTS.md"
    assert agents_md.exists(), "AGENTS.md should be generated for all consumers"
    non_blank_lines = sum(1 for ln in agents_md.read_text().splitlines() if ln.strip())
    assert non_blank_lines >= 40, (
        f"AGENTS.md has only {non_blank_lines} non-blank lines; must be ≥40 (AGT-01)"
    )

    # Security section checks
    agents_text = agents_md.read_text()
    assert ".env" in agents_text, "AGENTS.md must mention .env in security section"
    assert ".env.example" in agents_text, (
        "AGENTS.md must explicitly allow .env.example (Codex review MEDIUM #5)"
    )

    # Per-agent files: word count ≤200 and reference AGENTS.md
    per_agent_files = [
        scratch / "CLAUDE.md",
        scratch / ".cursor" / "rules" / "verify-kit.mdc",
        scratch / ".windsurf" / "rules" / "verify-kit.md",
        scratch / ".github" / "copilot-instructions.md",
    ]
    for agent_file in per_agent_files:
        assert agent_file.exists(), f"{agent_file.name} should be rendered when its prompt=True"
        content = agent_file.read_text()
        word_count = len(content.split())
        assert word_count <= 200, (
            f"{agent_file} has {word_count} words; per-agent files must be ≤200 words (Area 4)"
        )
        assert "AGENTS.md" in content, (
            f"{agent_file} must reference AGENTS.md (thin-pointer pattern)"
        )


# ─── Test 6: Per-agent files gated by Copier prompts ─────────────────────────


def test_per_agent_files_conditional_on_copier_prompts(
    template_root: Path, tmp_path: Path
) -> None:
    """Form B (Jinja-in-path) gates each per-agent file independently.

    Polarity: has_claude_code=False, has_cursor=True, has_windsurf=False, has_copilot=True
    """
    scratch = tmp_path / "agents-cond"
    _render(
        template_root,
        scratch,
        {
            **COMMON_DATA,
            "has_claude_code": False,
            "has_cursor": True,
            "has_windsurf": False,
            "has_copilot": True,
            "has_zed": False,
            "has_continue": False,
            "has_backend": False,
            "has_llm": False,
        },
    )

    # has_claude_code=False → CLAUDE.md at root should NOT exist
    assert not (scratch / "CLAUDE.md").exists(), (
        "CLAUDE.md should NOT be emitted when has_claude_code=False"
    )

    # has_cursor=True → .cursor/rules/verify-kit.mdc SHOULD exist
    assert (scratch / ".cursor" / "rules" / "verify-kit.mdc").exists(), (
        ".cursor/rules/verify-kit.mdc should be emitted when has_cursor=True"
    )

    # has_windsurf=False → .windsurf/rules/verify-kit.md should NOT exist
    assert not (scratch / ".windsurf" / "rules" / "verify-kit.md").exists(), (
        ".windsurf/rules/verify-kit.md should NOT be emitted when has_windsurf=False"
    )
    # The entire .windsurf/ directory should not exist either
    assert not (scratch / ".windsurf").exists(), (
        ".windsurf/ directory should NOT be created when has_windsurf=False"
    )

    # has_copilot=True → .github/copilot-instructions.md SHOULD exist
    assert (scratch / ".github" / "copilot-instructions.md").exists(), (
        ".github/copilot-instructions.md should be emitted when has_copilot=True"
    )

    # Phase 1 ships NO files under .claude/ (Phase 3 handles that)
    assert not (scratch / ".claude").exists(), (
        ".claude/ should NOT be created in Phase 1 (hooks/skills land in Phase 3)"
    )
