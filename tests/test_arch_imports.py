# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.arch (arch.imports — import-linter boundary contract).

Covers (hermetic — `lint-imports` is never actually spawned; proc_run is
monkeypatched to return scripted import-linter output):
- registry registration + spec metadata (tier=standard, category=arch, has_backend)
- pass when import-linter exits 0 (all contracts kept)
- PLANTED FAILURE: a broken contract (exit 1) → fail with dotted code arch.imports.broken,
  surfacing the illegal edge parsed from the real import-linter output format
- fail (not silent pass) when import-linter could not run (no contract summary)
- fail with tool-missing when uv is absent
- carryover-cwd: proc_run receives cwd=cwd

The real end-to-end forcing function (render a has_backend scaffold → plant
`import app` in a harness core module → arch.imports goes red, while the fuzz
harness's exempted runtime import stays green) is verified against a rendered
scaffold during verify-the-verifier.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project

# Real import-linter broken-contract output (captured from import-linter 2.11).
_BROKEN_OUTPUT = """
---------
Contracts
---------

Analyzed 30 files, 5 dependencies.
---------------------------------

harness core must not import app BROKEN

Contracts: 0 kept, 1 broken.


----------------
Broken contracts
----------------

harness core must not import app
--------------------------------

harness is not allowed to import app:

-   harness.checks.mise -> app.settings (l.7)
"""

_KEPT_OUTPUT = """
Analyzed 30 files, 5 dependencies.
---------------------------------

harness core must not import app KEPT

Contracts: 1 kept, 0 broken.
"""


@pytest.fixture(scope="module")
def arch_modules(tmp_path_factory: pytest.TempPathFactory):
    # arch.py is has_backend-gated; render from HEAD to include the new check.
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("arch-scratch"), _vcs_ref="HEAD", has_backend=True, has_db=False
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import arch as arch_mod

        yield registry, arch_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _fake_run(stdout: str, *, returncode: int):
    def _run(argv, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=returncode, stdout=stdout, stderr="")

    return _run


def test_arch_imports_registered(arch_modules) -> None:
    registry, _ = arch_modules
    assert "arch.imports" in {s.check_id for s in registry.list_checks()}


def test_arch_imports_spec_metadata(arch_modules) -> None:
    registry, _ = arch_modules
    spec = registry.get_check("arch.imports")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "arch"
    assert spec.fixable is False
    assert spec.tool == "import-linter"


def test_pass_when_contracts_kept(
    arch_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, arch_mod = arch_modules
    spec = registry.get_check("arch.imports")
    monkeypatch.setattr(arch_mod, "proc_run", _fake_run(_KEPT_OUTPUT, returncode=0))
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_broken_contract_is_flagged(
    arch_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PLANTED: harness core imports app → broken contract → red with the illegal edge."""
    registry, arch_mod = arch_modules
    spec = registry.get_check("arch.imports")
    monkeypatch.setattr(arch_mod, "proc_run", _fake_run(_BROKEN_OUTPUT, returncode=1))
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "arch.imports.broken"
    assert "harness.checks.mise -> app.settings" in result.error.message


def test_tool_error_when_no_summary(
    arch_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-zero exit with no 'N kept, M broken' line must FAIL as tool-error, not pass."""
    registry, arch_mod = arch_modules
    spec = registry.get_check("arch.imports")
    monkeypatch.setattr(
        arch_mod, "proc_run", _fake_run("ERROR: could not find package 'harness'", returncode=1)
    )
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "arch.imports.tool-error"


def test_fail_when_uv_missing(
    arch_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, arch_mod = arch_modules
    spec = registry.get_check("arch.imports")

    def _raise(argv, **kwargs):
        raise FileNotFoundError("uv")

    monkeypatch.setattr(arch_mod, "proc_run", _raise)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "arch.imports.tool-missing"


def test_passes_cwd_to_subprocess(
    arch_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, arch_mod = arch_modules
    spec = registry.get_check("arch.imports")
    captured: dict[str, object] = {}

    def _run(argv, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout=_KEPT_OUTPUT, stderr="")

    monkeypatch.setattr(arch_mod, "proc_run", _run)
    spec.fn(cwd=tmp_path)
    assert captured["cwd"] == tmp_path
