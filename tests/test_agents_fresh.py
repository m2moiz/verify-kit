# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.agents (agents.fresh — AGENTS.md/CLAUDE.md roster guard).

Covers (hermetic — pure in-process, no subprocess, no external tool):
- registry registration + spec metadata (tier=quick, category=meta, always-on, no tool)
- pass when the only check-namespaced token in AGENTS.md is a real roster id
- PLANTED FAILURE: a stale `web.bogus` reference → fail with agents.fresh.stale_reference
- no false positive on prose dotted tokens (app.main, core.py, pyproject.toml)
- a missing CLAUDE.md is skipped via the file-exists guard, not a crash
- a stale ref in CLAUDE.md is caught with error.file pointing at CLAUDE.md
- an empty cwd (no AGENTS.md, no CLAUDE.md) passes (nothing to validate)

The agents.fresh module is always-on (no jinja gate, no _exclude entry); a base
render includes it. The end-to-end forcing function (render a scaffold → plant a
`web.bogus` into the rendered AGENTS.md → agents.fresh goes red via the harness)
is exercised during verify-the-verifier.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def agents_modules(tmp_path_factory: pytest.TempPathFactory):
    # agents.fresh is always-on; a base render includes it. Render from HEAD so
    # the freshly-added module is present.
    scratch = render_scratch_project(tmp_path_factory.mktemp("agents-scratch"), _vcs_ref="HEAD")
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import agents as agents_mod

        yield registry, agents_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _write_agents(cwd: Path, body: str) -> None:
    (cwd / "AGENTS.md").write_text(body, encoding="utf-8")


def test_agents_fresh_registered(agents_modules) -> None:
    registry, _ = agents_modules
    assert "agents.fresh" in {s.check_id for s in registry.list_checks()}


def test_spec_metadata(agents_modules) -> None:
    registry, _ = agents_modules
    spec = registry.get_check("agents.fresh")
    assert spec is not None
    assert spec.tier == "quick"
    assert spec.category == "meta"
    assert spec.fixable is False
    assert spec.tool is None


def test_pass_on_clean_render(agents_modules, tmp_path: Path) -> None:
    """A real roster id (security.secrets) named in AGENTS.md passes."""
    registry, _ = agents_modules
    spec = registry.get_check("agents.fresh")
    _write_agents(tmp_path, "Run `security.secrets` and `meta.stability` before commit.")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_stale_reference_is_flagged(agents_modules, tmp_path: Path) -> None:
    """PLANTED FAIL: a stale check-namespaced reference reds the check.

    Uses ``meta.bogus`` (``meta`` is a namespace on the base render via
    meta.stability) rather than ``web.bogus`` — the base scaffold has no web
    checks, so ``web`` is not a known namespace there and ``web.bogus`` would be
    correctly ignored. The ``web.bogus`` shape is exercised against a has_web
    render in the end-to-end verify-the-verifier step.
    """
    registry, _ = agents_modules
    spec = registry.get_check("agents.fresh")
    _write_agents(tmp_path, "Run `meta.bogus` before commit.")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "agents.fresh.stale_reference"
    assert "meta.bogus" in result.error.message


def test_app_main_prose_no_false_positive(agents_modules, tmp_path: Path) -> None:
    """Prose dotted tokens with non-check prefixes / file extensions must not trip it."""
    registry, _ = agents_modules
    spec = registry.get_check("agents.fresh")
    _write_agents(
        tmp_path,
        "Wire app.main and app.settings. Edit core.py and pyproject.toml and mise.toml.\n"
        "See ci.yml and by_id.get and tailwind.config too.",
    )
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_claude_md_missing_is_skipped_not_failed(agents_modules, tmp_path: Path) -> None:
    """A cwd with AGENTS.md only (no CLAUDE.md) passes via the file-exists guard."""
    registry, _ = agents_modules
    spec = registry.get_check("agents.fresh")
    _write_agents(tmp_path, "Run `lint.ruff` then `format.ruff`.")
    assert not (tmp_path / "CLAUDE.md").exists()
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"


def test_claude_md_stale_is_caught(agents_modules, tmp_path: Path) -> None:
    """A stale ref in CLAUDE.md is caught with error.file == CLAUDE.md."""
    registry, _ = agents_modules
    spec = registry.get_check("agents.fresh")
    _write_agents(tmp_path, "Run `security.secrets` before commit.")
    (tmp_path / "CLAUDE.md").write_text("Also run `meta.bogus`.", encoding="utf-8")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "agents.fresh.stale_reference"
    assert result.error.file == "CLAUDE.md"
    assert "meta.bogus" in result.error.message


def test_no_agents_md_is_pass(agents_modules, tmp_path: Path) -> None:
    """An empty cwd (both inputs absent) passes — nothing to validate."""
    registry, _ = agents_modules
    spec = registry.get_check("agents.fresh")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None
