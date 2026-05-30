# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.deps (deps.unused — deptry dependency hygiene).

Covers (hermetic — deptry is never actually spawned; proc_run is monkeypatched
to write a scripted deptry --json-output file at the path the check passes):
- registry registration + spec metadata (tier=standard, category=deps, always-on)
- pass when deptry exits 0 (no issues)
- PLANTED FAILURE: an unused dep (DEP002) → fail with dotted code deps.unused.DEP002
- an undeclared import (DEP001) → fail with deps.unused.DEP001 + file/line
- fail (not silent pass) when deptry exits non-zero with no parseable report
- fail with tool-missing when uv is absent
- the temp json file is cleaned up
- carryover-cwd: proc_run receives cwd=cwd

The real end-to-end forcing function (render a scaffold → add an unused dep like
`cowsay` to pyproject → deps.unused goes red) is verified against rendered
scaffolds across add-on combos during verify-the-verifier (the conditional-dep
matrix must not false-flag add-on deps on a minimal render).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def deps_modules(tmp_path_factory: pytest.TempPathFactory):
    # deps.unused is always-on; a base render includes it. Render from HEAD.
    scratch = render_scratch_project(tmp_path_factory.mktemp("deps-scratch"), _vcs_ref="HEAD")
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import deps as deps_mod

        yield registry, deps_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _fake_deptry(issues, *, returncode: int, write: bool = True):
    """Fake proc_run that writes `issues` JSON to the --json-output path, like deptry."""
    captured: dict[str, object] = {}

    def _run(argv, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        if write and "--json-output" in argv:
            out = Path(argv[argv.index("--json-output") + 1])
            captured["json_path"] = out
            out.write_text(json.dumps(issues))
        return subprocess.CompletedProcess(args=argv, returncode=returncode, stdout="", stderr="")

    return _run, captured


def test_deps_unused_registered(deps_modules) -> None:
    registry, _ = deps_modules
    assert "deps.unused" in {s.check_id for s in registry.list_checks()}


def test_deps_unused_spec_metadata(deps_modules) -> None:
    registry, _ = deps_modules
    spec = registry.get_check("deps.unused")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "deps"
    assert spec.fixable is False
    assert spec.tool == "deptry"


def test_pass_when_no_issues(
    deps_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, deps_mod = deps_modules
    spec = registry.get_check("deps.unused")
    run, _ = _fake_deptry([], returncode=0)
    monkeypatch.setattr(deps_mod, "proc_run", run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_unused_dep_is_flagged(
    deps_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PLANTED: an unused declared dependency (DEP002) reds the check."""
    registry, deps_mod = deps_modules
    spec = registry.get_check("deps.unused")
    issues = [
        {
            "error": {"code": "DEP002", "message": "'cowsay' defined as a dependency but not used"},
            "module": "cowsay",
            "location": {"file": "pyproject.toml", "line": None, "column": None},
        }
    ]
    run, _ = _fake_deptry(issues, returncode=1)
    monkeypatch.setattr(deps_mod, "proc_run", run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deps.unused.DEP002"
    assert "cowsay" in result.error.message


def test_undeclared_import_is_flagged_with_location(
    deps_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, deps_mod = deps_modules
    spec = registry.get_check("deps.unused")
    issues = [
        {
            "error": {"code": "DEP001", "message": "'requests' imported but missing from deps"},
            "module": "requests",
            "location": {"file": "harness/x.py", "line": 2, "column": 8},
        }
    ]
    run, _ = _fake_deptry(issues, returncode=1)
    monkeypatch.setattr(deps_mod, "proc_run", run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deps.unused.DEP001"
    assert result.error.file == "harness/x.py"
    assert result.error.line == 2


def test_tool_error_when_unparseable(
    deps_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-zero exit with no parseable report must FAIL as tool-error, not pass."""
    registry, deps_mod = deps_modules
    spec = registry.get_check("deps.unused")
    # write=False → the json file stays empty (unparseable), exit nonzero.
    run, _ = _fake_deptry([], returncode=2, write=False)
    monkeypatch.setattr(deps_mod, "proc_run", run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deps.unused.tool-error"


def test_fail_when_uv_missing(
    deps_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, deps_mod = deps_modules
    spec = registry.get_check("deps.unused")

    def _raise(argv, **kwargs):
        raise FileNotFoundError("uv")

    monkeypatch.setattr(deps_mod, "proc_run", _raise)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deps.unused.tool-missing"


def test_temp_json_cleaned_up_and_cwd_forwarded(
    deps_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The temp --json-output file is unlinked, and proc_run gets cwd=cwd."""
    registry, deps_mod = deps_modules
    spec = registry.get_check("deps.unused")
    run, captured = _fake_deptry([], returncode=0)
    monkeypatch.setattr(deps_mod, "proc_run", run)
    spec.fn(cwd=tmp_path)
    assert captured["cwd"] == tmp_path
    # the temp file the check created must be gone (finally: unlink missing_ok)
    jp = captured.get("json_path")
    if jp is not None:
        assert not Path(jp).exists()
