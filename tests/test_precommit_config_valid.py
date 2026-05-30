# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.precommit (precommit.config.valid — offline YAML guard).

Covers (fully hermetic — operates on .pre-commit-config.yaml files written into
tmp_path; no subprocess, no network):
- registry registration + spec metadata (tier=quick, category=precommit)
- pass on a valid config containing the gitleaks hook
- PLANTED FAILURE: drop the gitleaks hook → fail precommit.config.valid.missing-hooks
- PLANTED FAILURE: malformed YAML → fail precommit.config.valid.invalid-yaml
- structurally-invalid (no repos list) → fail invalid-structure
- skip when no .pre-commit-config.yaml exists
- the check module contains NO `subprocess` usage (pure parse — bead s07 contract)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project

_VALID_CONFIG = """\
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.15
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks
"""

_NO_GITLEAKS = """\
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.15
    hooks:
      - id: ruff
"""

_MALFORMED = """\
repos:
  - repo: x
    hooks:
      - id: ruff
    rev: [unclosed
"""


@pytest.fixture(scope="module")
def precommit_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("precommit-scratch"), _vcs_ref="HEAD")
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import precommit as precommit_mod

        yield registry, precommit_mod, scratch
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _write_config(tmp_path: Path, text: str) -> Path:
    (tmp_path / ".pre-commit-config.yaml").write_text(text)
    return tmp_path


def test_precommit_registered(precommit_modules) -> None:
    registry, _, _ = precommit_modules
    assert "precommit.config.valid" in {s.check_id for s in registry.list_checks()}


def test_precommit_spec_metadata(precommit_modules) -> None:
    registry, _, _ = precommit_modules
    spec = registry.get_check("precommit.config.valid")
    assert spec is not None
    assert spec.tier == "quick"
    assert spec.category == "precommit"
    assert spec.fixable is False
    assert spec.tool is None


def test_pass_on_valid_config_with_gitleaks(precommit_modules, tmp_path: Path) -> None:
    registry, _, _ = precommit_modules
    spec = registry.get_check("precommit.config.valid")
    _write_config(tmp_path, _VALID_CONFIG)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_missing_gitleaks_is_flagged(precommit_modules, tmp_path: Path) -> None:
    """PLANTED: the secret-scan hook is gone → missing-hooks."""
    registry, _, _ = precommit_modules
    spec = registry.get_check("precommit.config.valid")
    _write_config(tmp_path, _NO_GITLEAKS)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "precommit.config.valid.missing-hooks"


def test_malformed_yaml_is_flagged(precommit_modules, tmp_path: Path) -> None:
    """PLANTED: invalid YAML → invalid-yaml (not a silent pass)."""
    registry, _, _ = precommit_modules
    spec = registry.get_check("precommit.config.valid")
    _write_config(tmp_path, _MALFORMED)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "precommit.config.valid.invalid-yaml"


def test_structurally_invalid_is_flagged(precommit_modules, tmp_path: Path) -> None:
    registry, _, _ = precommit_modules
    spec = registry.get_check("precommit.config.valid")
    _write_config(tmp_path, "just_a_string\n")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "precommit.config.valid.invalid-structure"


def test_skip_when_no_config(precommit_modules, tmp_path: Path) -> None:
    registry, _, _ = precommit_modules
    spec = registry.get_check("precommit.config.valid")
    result = spec.fn(cwd=tmp_path)  # tmp_path has no .pre-commit-config.yaml
    assert result.status == "skip"


def test_check_module_uses_no_subprocess(precommit_modules) -> None:
    """Bead s07 contract: the check is a PURE yaml parse — no child-process calls.

    Checks for actual usage (an import or call), not the bare word, so a docstring
    that *describes* the no-subprocess guarantee doesn't trip the assertion.
    """
    _, precommit_mod, scratch = precommit_modules
    source = (Path(scratch) / "harness" / "checks" / "precommit.py").read_text()
    for forbidden in ("import subprocess", "subprocess.", "from harness.proc", "proc_run", "os.system"):
        assert forbidden not in source, (
            f"precommit.config.valid must not shell out (found {forbidden!r}) — pure yaml parse"
        )


def test_rendered_scaffold_config_passes(precommit_modules) -> None:
    """The scaffold's OWN rendered .pre-commit-config.yaml must satisfy the check."""
    registry, _, scratch = precommit_modules
    spec = registry.get_check("precommit.config.valid")
    result = spec.fn(cwd=Path(scratch))
    assert result.status == "pass", f"rendered scaffold config failed: {result.message}"
