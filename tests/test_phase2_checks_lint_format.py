"""Tests for harness.checks.{lint,format} (Plan 02-04, Task 2).

Covers:
- registry size after adding 4 new lint/format specs
- biome local-binary resolution path (node_modules/.bin → shutil.which → skip)
- offline-first: pnpm dlx is NEVER invoked (review HIGH-5)
- error envelope dotted codes match Decision 1.2
- subprocess.run is called with cwd=cwd (carryover-cwd)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def lf_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("lf-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        import harness.models as models
        from harness.checks import lint as lint_mod
        from harness.checks import format as format_mod

        yield registry, models, lint_mod, format_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def test_registry_size_after_lint_format(lf_modules) -> None:
    registry, _, _, _ = lf_modules
    ids = {s.check_id for s in registry.list_checks()}
    assert {
        "mise.toml.valid",
        "copier.answers.valid",
        "just-list.renders",
        "lint.ruff",
        "lint.biome",
        "format.ruff",
        "format.biome",
    } <= ids
    assert len(registry.list_checks()) >= 7


def test_lint_ruff_spec_metadata(lf_modules) -> None:
    registry, _, _, _ = lf_modules
    spec = registry.get_check("lint.ruff")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "lint"
    assert spec.fixable is False
    assert spec.tool == "ruff"


def test_format_ruff_fixable_metadata(lf_modules) -> None:
    registry, _, _, _ = lf_modules
    spec = registry.get_check("format.ruff")
    assert spec is not None
    assert spec.fixable is True
    assert spec.tier == "standard"


def test_lint_biome_skip_when_no_local_binary(
    lf_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If no node_modules/.bin/biome AND no PATH biome → skip."""
    registry, _, lint_mod, _ = lf_modules
    spec = registry.get_check("lint.biome")
    monkeypatch.setattr(lint_mod.shutil, "which", lambda _: None)
    # tmp_path has no node_modules
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"
    assert "biome" in result.message.lower()


def test_format_biome_skip_when_no_local_binary(
    lf_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, _, _, format_mod = lf_modules
    spec = registry.get_check("format.biome")
    monkeypatch.setattr(format_mod.shutil, "which", lambda _: None)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"


def test_lint_biome_skip_message_does_not_mention_pnpm_dlx(
    lf_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Offline-first contract (review HIGH-5): never recommend `pnpm dlx`."""
    registry, _, lint_mod, _ = lf_modules
    spec = registry.get_check("lint.biome")
    monkeypatch.setattr(lint_mod.shutil, "which", lambda _: None)
    result = spec.fn(cwd=tmp_path)
    assert "pnpm dlx" not in result.message


def test_lint_biome_uses_local_node_modules_binary(
    lf_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When node_modules/.bin/biome exists, it is preferred over PATH."""
    registry, _, lint_mod, _ = lf_modules
    spec = registry.get_check("lint.biome")
    bindir = tmp_path / "node_modules" / ".bin"
    bindir.mkdir(parents=True)
    fake_biome = bindir / "biome"
    fake_biome.write_text("#!/bin/sh\nexit 0\n")
    fake_biome.chmod(0o755)

    captured: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(lint_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(lint_mod.shutil, "which", lambda _: "/usr/bin/biome")  # should be IGNORED
    result = spec.fn(cwd=tmp_path)
    # The local binary path must be used, not /usr/bin/biome
    assert str(fake_biome) == captured["argv"][0]
    assert captured["cwd"] == tmp_path
    assert result.status in ("pass", "fail")  # binary ran; pass/fail depends on JSON


def test_lint_ruff_pass_when_no_issues(
    lf_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, _, lint_mod, _ = lf_modules
    spec = registry.get_check("lint.ruff")

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="[]\n", stderr="")

    monkeypatch.setattr(lint_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"


def test_lint_ruff_fail_uses_dotted_error_code(
    lf_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, _, lint_mod, _ = lf_modules
    spec = registry.get_check("lint.ruff")
    payload = '[{"code":"E501","message":"line too long","filename":"a.py","location":{"row":1,"column":1}}]'

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=1, stdout=payload, stderr="")

    monkeypatch.setattr(lint_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert re.match(r"^lint\.ruff\.[A-Z0-9]+$", result.error.code)


def test_lint_ruff_passes_cwd_to_subprocess(
    lf_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Carryover-cwd: subprocess.run receives cwd=cwd."""
    registry, _, lint_mod, _ = lf_modules
    spec = registry.get_check("lint.ruff")
    captured: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(lint_mod.subprocess, "run", fake_run)
    spec.fn(cwd=tmp_path)
    assert captured["cwd"] == tmp_path


def test_format_ruff_pass(lf_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry, _, _, format_mod = lf_modules
    spec = registry.get_check("format.ruff")

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(format_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"


def test_format_ruff_fail(lf_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry, _, _, format_mod = lf_modules
    spec = registry.get_check("format.ruff")

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=1, stdout="Would reformat 3 files", stderr="")

    monkeypatch.setattr(format_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "format.ruff.unformatted"
