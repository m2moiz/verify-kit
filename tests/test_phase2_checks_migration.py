# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks/{mise,copier,just_list} migration (Plan 02-04, Task 1).

Covers the Phase-1 → Phase-2 migration of the three existing checks into the
new `@register`-based registry layout under `harness/checks/`.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def checks_modules(tmp_path_factory: pytest.TempPathFactory):
    """Render a scratch project and import its harness.checks subpackage."""
    scratch = render_scratch_project(tmp_path_factory.mktemp("checks-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401  (trigger registration)
        import harness.registry as registry
        import harness.models as models

        yield checks, registry, models
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def test_importing_harness_checks_populates_registry(checks_modules) -> None:
    _, registry, _ = checks_modules
    ids = {s.check_id for s in registry.list_checks()}
    # Task 1 adds 3, Task 2 adds 4 more.
    assert "mise.toml.valid" in ids
    assert "copier.answers.valid" in ids
    assert "just-list.renders" in ids


def test_mise_spec_metadata(checks_modules) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("mise.toml.valid")
    assert spec is not None
    assert spec.tier == "quick"
    assert spec.category == "toolchain"
    assert spec.inputs == [".mise.toml"]


def test_copier_spec_metadata(checks_modules) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("copier.answers.valid")
    assert spec is not None
    assert spec.tier == "quick"
    assert spec.inputs == [".copier-answers.yml"]


def test_just_list_spec_metadata(checks_modules) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("just-list.renders")
    assert spec is not None
    assert spec.tier == "quick"
    assert spec.inputs == ["justfile"]
    assert spec.skip_if_unavailable is True
    assert spec.tool == "just"


def test_mise_check_pass(checks_modules, tmp_path: Path) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("mise.toml.valid")
    (tmp_path / ".mise.toml").write_text(
        textwrap.dedent(
            """\
            [tools]
            python = "3.13"
            node = "24"
            """
        )
    )
    result = spec.fn(cwd=tmp_path)
    assert result.check_id == "mise.toml.valid"
    assert result.status == "pass"


def test_mise_check_missing_file(checks_modules, tmp_path: Path) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("mise.toml.valid")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert re.match(r"^mise\.toml\..+$", result.error.code)


def test_mise_check_missing_tools(checks_modules, tmp_path: Path) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("mise.toml.valid")
    (tmp_path / ".mise.toml").write_text("[tools]\npython = \"3.13\"\n")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "mise.toml.missing-tools"


def test_mise_check_invalid_toml(checks_modules, tmp_path: Path) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("mise.toml.valid")
    (tmp_path / ".mise.toml").write_text("not toml = = =")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "mise.toml.invalid-toml"


def test_copier_check_skips_when_file_absent(checks_modules, tmp_path: Path) -> None:
    """Phase-1 SKIP behavior preserved: missing file → skip, not fail."""
    _, registry, _ = checks_modules
    spec = registry.get_check("copier.answers.valid")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"


def test_copier_check_pass(checks_modules, tmp_path: Path) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("copier.answers.valid")
    (tmp_path / ".copier-answers.yml").write_text("_src_path: gh:m2moiz/verify-kit\n")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"


def test_copier_check_missing_src_path(checks_modules, tmp_path: Path) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("copier.answers.valid")
    (tmp_path / ".copier-answers.yml").write_text("other_key: value\n")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "copier.answers.missing-src-path"


def test_copier_check_invalid_yaml(checks_modules, tmp_path: Path) -> None:
    _, registry, _ = checks_modules
    spec = registry.get_check("copier.answers.valid")
    (tmp_path / ".copier-answers.yml").write_text(": : not yaml :\n")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "copier.answers.invalid-yaml"


def test_just_list_skips_when_just_missing(
    checks_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When `just` binary is absent, status='skip' (UX-06)."""
    _, registry, _ = checks_modules
    spec = registry.get_check("just-list.renders")

    real_run = subprocess.run

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("just not installed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    # restore for downstream tests in same process
    monkeypatch.setattr(subprocess, "run", real_run)
    assert result.status == "skip"


def test_just_list_pass_when_binary_present(
    checks_modules, tmp_path: Path
) -> None:
    """When `just` is installed and works, status='pass'. Skips if not installed."""
    if shutil.which("just") is None:
        pytest.skip("just binary not installed on host")
    _, registry, _ = checks_modules
    spec = registry.get_check("just-list.renders")
    (tmp_path / "justfile").write_text("hello:\n    echo hi\n")
    result = spec.fn(cwd=tmp_path)
    # Either pass (just present + justfile valid) — main assertion.
    assert result.status == "pass"
