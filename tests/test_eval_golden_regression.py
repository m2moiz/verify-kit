# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.eval_golden (eval.golden_regression — offline LLM gate).

Covers (hermetic — pytest/pydantic-evals are never actually spawned; proc_run is
monkeypatched to return a scripted CompletedProcess, and the golden test/dataset
files are stubbed under a tmp cwd so the early no_dataset skip does not fire):
- registry registration + spec metadata (tier=slow, category=llm, tool=pydantic-evals)
- skip (no_dataset) when the golden test/dataset is absent
- pass when pytest exits 0 with passing cases
- skip (cassette_missing) when pytest exits 0 but everything was skipped
- skip (cassette_missing) when pytest exits 5 (no tests collected)
- PLANTED FAILURE: a failing case (nonzero exit) → fail with eval.golden_regression.case_failed
- fail (cassette_missing) when VCR blocked an un-cassetted request (no network)
- fail with tool-missing when uv is absent
- carryover-cwd: proc_run receives cwd=cwd

The render uses has_llm so harness.checks.eval_golden is present. The real
end-to-end forcing function (render a has_llm scaffold, record a cassette, mutate
an expected value → red; delete the cassette → red with no network) is exercised
during verify-the-verifier.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def eval_golden_modules(tmp_path_factory: pytest.TempPathFactory):
    # eval.golden_regression is has_llm-gated; render a has_llm scratch from HEAD.
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("eval-golden-scratch"), _vcs_ref="HEAD", has_llm=True
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import eval_golden as eval_golden_mod

        yield registry, eval_golden_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _stub_golden_files(cwd: Path) -> None:
    """Create the golden test + dataset under cwd so the no_dataset skip is bypassed."""
    (cwd / "tests" / "llm").mkdir(parents=True, exist_ok=True)
    (cwd / "tests" / "llm" / "test_golden_regression.py").write_text("# stub", encoding="utf-8")
    (cwd / "eval" / "datasets").mkdir(parents=True, exist_ok=True)
    (cwd / "eval" / "datasets" / "golden.jsonl").write_text("{}\n", encoding="utf-8")


def _fake_proc(stdout: str = "", stderr: str = "", *, returncode: int):
    """Return (run_fn, captured) where run_fn mimics proc_run's CompletedProcess."""
    captured: dict[str, object] = {}

    def _run(argv, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        captured["argv"] = argv
        return subprocess.CompletedProcess(
            args=argv, returncode=returncode, stdout=stdout, stderr=stderr
        )

    return _run, captured


def test_eval_golden_registered(eval_golden_modules) -> None:
    registry, _ = eval_golden_modules
    assert "eval.golden_regression" in {s.check_id for s in registry.list_checks()}


def test_spec_metadata(eval_golden_modules) -> None:
    registry, _ = eval_golden_modules
    spec = registry.get_check("eval.golden_regression")
    assert spec is not None
    assert spec.tier == "slow"
    assert spec.category == "llm"
    assert spec.fixable is False
    assert spec.tool == "pydantic-evals"


def test_skip_when_no_dataset(eval_golden_modules, tmp_path: Path) -> None:
    """An empty cwd (no golden test/dataset) skips cleanly, never spawns pytest."""
    registry, _ = eval_golden_modules
    spec = registry.get_check("eval.golden_regression")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"
    assert result.error is not None
    assert result.error.code == "eval.golden_regression.no_dataset"


def test_pass_when_cases_match(
    eval_golden_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, mod = eval_golden_modules
    spec = registry.get_check("eval.golden_regression")
    _stub_golden_files(tmp_path)
    run, _ = _fake_proc("1 passed in 0.5s", returncode=0)
    monkeypatch.setattr(mod, "proc_run", run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_skip_when_all_skipped(
    eval_golden_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit 0 but everything skipped (no cassette) → skip cassette_missing."""
    registry, mod = eval_golden_modules
    spec = registry.get_check("eval.golden_regression")
    _stub_golden_files(tmp_path)
    run, _ = _fake_proc("1 skipped in 0.1s", returncode=0)
    monkeypatch.setattr(mod, "proc_run", run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"
    assert result.error is not None
    assert result.error.code == "eval.golden_regression.cassette_missing"


def test_skip_when_no_tests_collected(
    eval_golden_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pytest exit 5 (no tests collected) → skip, not fail."""
    registry, mod = eval_golden_modules
    spec = registry.get_check("eval.golden_regression")
    _stub_golden_files(tmp_path)
    run, _ = _fake_proc("no tests ran", returncode=5)
    monkeypatch.setattr(mod, "proc_run", run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"
    assert result.error is not None
    assert result.error.code == "eval.golden_regression.cassette_missing"


def test_case_failed_is_flagged(
    eval_golden_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PLANTED: a failing golden case (nonzero exit) reds the check as case_failed."""
    registry, mod = eval_golden_modules
    spec = registry.get_check("eval.golden_regression")
    _stub_golden_files(tmp_path)
    stdout = (
        "FAILED tests/llm/test_golden_regression.py::test_golden_regression - AssertionError\n"
        "AssertionError: echo_ok failed: expected output did not match the cassette replay\n"
        "1 failed in 0.4s"
    )
    run, _ = _fake_proc(stdout, returncode=1)
    monkeypatch.setattr(mod, "proc_run", run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "eval.golden_regression.case_failed"
    assert "echo_ok" in result.message


def test_cassette_blocked_is_fail_no_network(
    eval_golden_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VCR blocking an un-cassetted request → fail cassette_missing (no live call)."""
    registry, mod = eval_golden_modules
    spec = registry.get_check("eval.golden_regression")
    _stub_golden_files(tmp_path)
    stderr = "vcr.errors.CannotOverwriteExistingCassetteException: no match for POST ..."
    run, _ = _fake_proc("1 error in 0.3s", stderr, returncode=1)
    monkeypatch.setattr(mod, "proc_run", run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "eval.golden_regression.cassette_missing"


def test_tool_missing_when_uv_absent(
    eval_golden_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, mod = eval_golden_modules
    spec = registry.get_check("eval.golden_regression")
    _stub_golden_files(tmp_path)

    def _raise(argv, **kwargs):
        raise FileNotFoundError("uv")

    monkeypatch.setattr(mod, "proc_run", _raise)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "eval.golden_regression.tool-missing"


def test_cwd_forwarded(
    eval_golden_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """proc_run receives cwd=cwd (carryover-cwd discipline)."""
    registry, mod = eval_golden_modules
    spec = registry.get_check("eval.golden_regression")
    _stub_golden_files(tmp_path)
    run, captured = _fake_proc("1 passed in 0.5s", returncode=0)
    monkeypatch.setattr(mod, "proc_run", run)
    spec.fn(cwd=tmp_path)
    assert captured["cwd"] == tmp_path
