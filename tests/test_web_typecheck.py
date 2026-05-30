# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.web :: web.typecheck (TS static type gate).

Vite never type-checks during build, so a standard `just verify` is blind to
TypeScript errors today. web.typecheck closes that gap by running `tsc --noEmit`
over web/. This module guards its registration + parse/skip contract hermetically
(proc_run is monkeypatched — tsc is never actually invoked):

- registry registration + spec metadata (tier/category/fixable/tool)
- pass on a clean tsc run (exit 0)
- fail with a dotted web.typecheck.TSxxxx code + clickable file/line/column on a
  parsed `tsc --pretty false` diagnostic (planted TS error)
- fail with web.typecheck.run.failed when tsc exits non-zero with no parseable
  diagnostic (config error / crash) — never a phantom pass
- skip (offline-first) when web/node_modules/.bin/tsc is absent — the check
  NEVER auto-fetches and NEVER reds an offline run

The real end-to-end forcing function (render a has_web scaffold, plant a TS error,
`web.typecheck` goes red) is exercised by the orchestrator against a rendered
scaffold with `pnpm install` done; these hermetic tests guard the contract in CI
without a slow render+install+tsc run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def web_modules(tmp_path_factory: pytest.TempPathFactory):
    # _vcs_ref="HEAD": web.typecheck was added after the latest release tag, so
    # render from the worktree HEAD (not the tag) to include it. has_web=True so
    # the web check module + harness.web subpackage are rendered.
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("web-tc-scratch"),
        _vcs_ref="HEAD",
        has_web=True,
        # Keep the scaffold minimal — only has_web matters for this check.
        has_backend=False,
        has_db=False,
        has_llm=False,
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import web as web_mod

        yield registry, web_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _present_tsc(monkeypatch: pytest.MonkeyPatch, web_mod) -> None:
    """Make the local-tsc probe (web/node_modules/.bin/tsc) see a binary so the
    check runs instead of taking the offline skip path."""
    monkeypatch.setattr(Path, "exists", lambda self: True)


def test_web_typecheck_registered(web_modules) -> None:
    registry, _ = web_modules
    ids = {s.check_id for s in registry.list_checks()}
    assert "web.typecheck" in ids


def test_web_typecheck_spec_metadata(web_modules) -> None:
    registry, _ = web_modules
    spec = registry.get_check("web.typecheck")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "typecheck"
    assert spec.fixable is False
    assert spec.tool == "tsc"
    assert spec.skip_if_unavailable is True


def test_web_typecheck_pass_on_clean_run(
    web_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, web_mod = web_modules
    spec = registry.get_check("web.typecheck")
    _present_tsc(monkeypatch, web_mod)

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(web_mod, "proc_run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_web_typecheck_fail_parses_first_diagnostic(
    web_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A planted TS error → fail with web.typecheck.TSxxxx + clickable location."""
    registry, web_mod = web_modules
    spec = registry.get_check("web.typecheck")
    _present_tsc(monkeypatch, web_mod)

    # `const _p: number = "x";` produces TS2322 at the assignment.
    tsc_stdout = (
        "src/App.tsx(12,9): error TS2322: "
        "Type 'string' is not assignable to type 'number'.\n"
        "src/App.tsx(20,3): error TS2304: Cannot find name 'wat'.\n"
    )

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            args=argv, returncode=2, stdout=tsc_stdout, stderr=""
        )

    monkeypatch.setattr(web_mod, "proc_run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    # First diagnostic only — code carries the TS error number.
    assert result.error.code == "web.typecheck.TS2322"
    assert result.error.file == "src/App.tsx"
    assert result.error.line == 12
    assert result.error.column == 9
    assert "TS2322" in result.error.message


def test_web_typecheck_fail_on_unparseable_nonzero(
    web_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tsc exits non-zero with no parseable diagnostic → fail, never phantom pass."""
    registry, web_mod = web_modules
    spec = registry.get_check("web.typecheck")
    _present_tsc(monkeypatch, web_mod)

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            args=argv,
            returncode=1,
            stdout="",
            stderr="error TS5083: Cannot read file 'tsconfig.json'.",
        )

    monkeypatch.setattr(web_mod, "proc_run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "web.typecheck.run.failed"


def test_web_typecheck_skip_when_tsc_absent(
    web_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Offline-first: no local web/node_modules/.bin/tsc → skip (never fetch/fail)."""
    registry, web_mod = web_modules
    spec = registry.get_check("web.typecheck")

    # tmp_path has no web/node_modules/.bin/tsc — real Path.exists returns False,
    # so the local-bin probe misses and the check must skip (no subprocess).
    called: dict[str, bool] = {"ran": False}

    def fake_run(argv, **kwargs):  # pragma: no cover — must NOT be reached
        called["ran"] = True
        raise AssertionError("proc_run must not run when tsc is absent (skip path)")

    monkeypatch.setattr(web_mod, "proc_run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"
    assert called["ran"] is False
    assert result.error is None
    assert "tsc not found" in result.message


def test_web_typecheck_passes_cwd_web_to_subprocess(
    web_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Subprocess discipline: proc_run runs in cwd/'web' (not bare cwd)."""
    registry, web_mod = web_modules
    spec = registry.get_check("web.typecheck")
    _present_tsc(monkeypatch, web_mod)
    captured: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        captured["argv"] = argv
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(web_mod, "proc_run", fake_run)
    spec.fn(cwd=tmp_path)
    assert captured["cwd"] == tmp_path / "web"
    # tsc invoked with --noEmit --pretty false for stable parseable output.
    assert "--noEmit" in captured["argv"]
    assert "--pretty" in captured["argv"]
