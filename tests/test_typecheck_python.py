# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.typecheck (typecheck.python — pyright standard mode).

Covers (hermetic — pyright is never actually invoked; subprocess is monkeypatched):
- registry registration + spec metadata
- pass on a clean pyright JSON report (0 errors)
- fail on an error diagnostic, with a dotted code + clickable file/line
- fail (not silent pass) when pyright produces non-JSON (venv not synced)
- fail with tool-missing when uv is absent
- carryover-cwd: subprocess.run receives cwd=cwd

The real end-to-end forcing function (render scratch → plant a type error →
`typecheck.python` goes red) was verified manually against a rendered
has_backend scaffold; these hermetic tests guard the parse/registration contract
in CI without a slow render+sync+pyright run.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def tc_modules(tmp_path_factory: pytest.TempPathFactory):
    # _vcs_ref="HEAD": typecheck.python was added after the latest release tag,
    # so render from the worktree HEAD (not the tag) to include it.
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("tc-scratch"), _vcs_ref="HEAD"
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import typecheck as typecheck_mod

        yield registry, typecheck_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _pyright_json(errors: list[dict], files: int = 3) -> str:
    return json.dumps(
        {
            "generalDiagnostics": errors,
            "summary": {"filesAnalyzed": files, "errorCount": len(errors)},
        }
    )


def test_typecheck_python_registered(tc_modules) -> None:
    registry, _ = tc_modules
    ids = {s.check_id for s in registry.list_checks()}
    assert "typecheck.python" in ids


def test_typecheck_python_spec_metadata(tc_modules) -> None:
    registry, _ = tc_modules
    spec = registry.get_check("typecheck.python")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "typecheck"
    assert spec.fixable is False
    assert spec.tool == "pyright"


def test_typecheck_pass_on_clean_report(
    tc_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, tc_mod = tc_modules
    spec = registry.get_check("typecheck.python")

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=_pyright_json([]), stderr=""
        )

    monkeypatch.setattr(tc_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert "0 errors" in result.message


def test_typecheck_fail_on_error_with_dotted_code_and_location(
    tc_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, tc_mod = tc_modules
    spec = registry.get_check("typecheck.python")
    diag = {
        "severity": "error",
        "rule": "reportReturnType",
        "message": 'Type "int" is not assignable to return type "str"',
        "file": str(tmp_path / "harness" / "boom.py"),
        "range": {"start": {"line": 1, "character": 11}},
    }

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            args=argv, returncode=1, stdout=_pyright_json([diag]), stderr=""
        )

    monkeypatch.setattr(tc_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "typecheck.python.reportReturnType"
    # 0-based pyright range is surfaced as 1-based for humans/IDEs.
    assert result.error.line == 2
    assert result.error.column == 12
    assert result.error.file is not None


def test_typecheck_fail_on_non_json_stdout(
    tc_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-JSON stdout (e.g. venv not synced) must FAIL, never silently pass."""
    registry, tc_mod = tc_modules
    spec = registry.get_check("typecheck.python")

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            args=argv, returncode=2, stdout="", stderr="error: pyright not found"
        )

    monkeypatch.setattr(tc_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "typecheck.python.tool-error"


def test_typecheck_fail_when_uv_missing(
    tc_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, tc_mod = tc_modules
    spec = registry.get_check("typecheck.python")

    def fake_run(argv, **kwargs):
        raise FileNotFoundError("uv")

    monkeypatch.setattr(tc_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "typecheck.python.tool-missing"


def test_typecheck_passes_cwd_to_subprocess(
    tc_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Carryover-cwd: subprocess.run receives cwd=cwd (REVIEW-CHECKLIST §1)."""
    registry, tc_mod = tc_modules
    spec = registry.get_check("typecheck.python")
    captured: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=_pyright_json([]), stderr=""
        )

    monkeypatch.setattr(tc_mod.subprocess, "run", fake_run)
    spec.fn(cwd=tmp_path)
    assert captured["cwd"] == tmp_path
