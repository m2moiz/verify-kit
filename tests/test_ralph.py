# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""Tests for harness.ralph (plan 03-02 T07).

These tests load template/harness/ralph.py.jinja2 directly via importlib —
the file contains no Jinja syntax, so it parses as plain Python. This keeps
the test suite fast (no copier-render or venv-install round-trip) while still
asserting on the canonical contract (REVIEW-CHECKLIST §1, §2, plan 03-02 T05).

CANONICAL CONTRACT under test:

    {
      "status":      "done" | "stuck",
      "iters":       int >= 0,
      "cost_usd":    float >= 0.0,
      "output_path": str,                              # cwd/.verify/ralph.json
      "reason":      "iteration_cap" | "cost_cap",     # iff status == "stuck"
    }

This is the SAME shape asserted by the MCP `ralph_run` tool (plan 03-01)
and the 03-01 T08 integration test. Any deviation must update every consumer.
"""
from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


_RALPH_SRC = (
    Path(__file__).resolve().parents[1]
    / "template"
    / "harness"
    / "ralph.py.jinja2"
)


def _load_ralph_module():
    """Load template/harness/ralph.py.jinja2 as a Python module.

    The default importlib machinery refuses .jinja2 extensions; we force a
    SourceFileLoader since the file is pure Python with no Jinja syntax.
    """
    loader = SourceFileLoader("_ralph_under_test", str(_RALPH_SRC))
    spec = importlib.util.spec_from_loader("_ralph_under_test", loader)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ralph():
    return _load_ralph_module()


# ── Canonical shape helpers ──────────────────────────────────────────────────

REQUIRED_KEYS = {"status", "iters", "cost_usd", "output_path"}


def _assert_canonical_shape(result: dict) -> None:
    assert REQUIRED_KEYS <= set(result.keys()), (
        f"missing canonical keys: required {REQUIRED_KEYS}, got {set(result.keys())}"
    )
    assert result["status"] in {"done", "stuck"}, result["status"]
    assert isinstance(result["iters"], int) and result["iters"] >= 0
    assert isinstance(result["cost_usd"], float) and result["cost_usd"] >= 0.0
    assert isinstance(result["output_path"], str)
    assert result["output_path"].endswith(".verify/ralph.json")
    if result["status"] == "stuck":
        assert "reason" in result, "stuck status MUST carry a reason"
        assert result["reason"] in {"iteration_cap", "cost_cap"}
    else:
        # done -> no reason key
        assert "reason" not in result


# ── Tests ────────────────────────────────────────────────────────────────────


def test_ralph_run_hits_iter_cap(ralph, tmp_path: Path) -> None:
    """Iter cap with non-zero cost stub; should_stop fires on iter 2."""
    def stub(cmd, cwd):
        return {"cost_usd": 0.0, "done": False}

    result = ralph.run(
        cwd=tmp_path,
        prompt="x",
        max_iters=2,
        cost_cap_usd=999.0,
        _spawn=stub,
    )
    _assert_canonical_shape(result)
    assert result["status"] == "stuck"
    assert result["reason"] == "iteration_cap"
    assert result["iters"] == 2


def test_ralph_run_hits_cost_cap(ralph, tmp_path: Path) -> None:
    """Cost cap fires before iter cap; reason=='cost_cap'."""
    def stub(cmd, cwd):
        return {"cost_usd": 0.5, "done": False}

    result = ralph.run(
        cwd=tmp_path,
        prompt="x",
        max_iters=100,
        cost_cap_usd=0.4,
        _spawn=stub,
    )
    _assert_canonical_shape(result)
    assert result["status"] == "stuck"
    assert result["reason"] == "cost_cap"
    assert result["cost_usd"] >= 0.4


def test_ralph_run_cap_precedence_cost_wins_tie(ralph, tmp_path: Path) -> None:
    """When BOTH caps fire on the same iter, cost_cap wins (locked tie-break)."""
    def stub(cmd, cwd):
        return {"cost_usd": 1.0, "done": False}

    result = ralph.run(
        cwd=tmp_path,
        prompt="x",
        max_iters=1,
        cost_cap_usd=0.5,
        _spawn=stub,
    )
    _assert_canonical_shape(result)
    assert result["status"] == "stuck"
    assert result["reason"] == "cost_cap", (
        "tie-break: cost_cap MUST win when both fire same iter (plan 03-02 T05)"
    )
    assert result["iters"] == 1


def test_ralph_run_done_signals_no_reason(ralph, tmp_path: Path) -> None:
    """Executor signaling done -> status='done', NO reason key."""
    def stub(cmd, cwd):
        return {"cost_usd": 0.0, "done": True}

    result = ralph.run(
        cwd=tmp_path,
        prompt="x",
        max_iters=5,
        cost_cap_usd=999.0,
        _spawn=stub,
    )
    _assert_canonical_shape(result)
    assert result["status"] == "done"
    assert "reason" not in result


def test_ralph_state_file_is_cwd_relative(
    ralph, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REVIEW-CHECKLIST §1: state path resolves via the cwd ARG, not Path.cwd()."""
    cwd_a = tmp_path / "a"
    cwd_b = tmp_path / "b"
    cwd_a.mkdir()
    cwd_b.mkdir()
    monkeypatch.chdir(cwd_a)

    def stub(cmd, cwd):
        return {"cost_usd": 0.0, "done": True}

    ralph.run(cwd=cwd_b, prompt="x", max_iters=1, cost_cap_usd=999.0, _spawn=stub)

    assert (cwd_b / ".verify" / "ralph.json").exists()
    assert not (cwd_a / ".verify" / "ralph.json").exists()


def test_ralph_subprocess_uses_explicit_cwd(
    ralph, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every subprocess.run invocation must pass cwd=cwd explicitly."""
    captured_kwargs: list[dict] = []

    class _FakeProc:
        stdout = '{"cost_usd": 0.0, "done": true}'

        def __init__(self, *args, **kwargs):
            pass

    def fake_run(cmd, *args, **kwargs):
        captured_kwargs.append(kwargs)
        return _FakeProc()

    monkeypatch.setattr(ralph.subprocess, "run", fake_run)

    cwd_b = tmp_path / "b"
    cwd_b.mkdir()
    ralph.run(cwd=cwd_b, prompt="x", max_iters=1, cost_cap_usd=999.0)

    assert captured_kwargs, "subprocess.run was never called"
    for kw in captured_kwargs:
        assert kw.get("cwd") == cwd_b, (
            f"subprocess.run kwargs missing cwd={cwd_b!r}; got {kw}"
        )


def test_ralph_status_returns_no_runs_when_absent(ralph, tmp_path: Path) -> None:
    """status() on a clean dir returns {'status': 'no_runs'}."""
    out = ralph.status(cwd=tmp_path)
    assert out == {"status": "no_runs"}


def test_ralph_status_returns_last_result(ralph, tmp_path: Path) -> None:
    """After run(), status() returns the parsed state file contents."""
    def stub(cmd, cwd):
        return {"cost_usd": 0.0, "done": True}

    result = ralph.run(
        cwd=tmp_path, prompt="x", max_iters=1, cost_cap_usd=999.0, _spawn=stub
    )
    out = ralph.status(cwd=tmp_path)
    assert out["status"] == result["status"]
    assert out["iters"] == result["iters"]
    assert out["output_path"] == result["output_path"]


def test_ralph_no_statements_after_return(ralph) -> None:
    """REVIEW-CHECKLIST §2: run() and status() have no statements after return."""
    import ast
    import inspect

    for fn in (ralph.run, ralph.status):
        src = inspect.getsource(fn)
        # Dedent so the AST parses standalone.
        import textwrap

        tree = ast.parse(textwrap.dedent(src))
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)

        def _check(body, in_should_stop=False):
            for i, node in enumerate(body):
                # Recurse into compound statements.
                if isinstance(node, ast.If):
                    # Detect the "if should_stop:" branch (heuristic: name match).
                    test_src = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
                    is_stop_branch = "should_stop" in test_src
                    _check(node.body, in_should_stop or is_stop_branch)
                    _check(node.orelse, in_should_stop)
                elif isinstance(node, (ast.For, ast.While)):
                    _check(node.body, in_should_stop)
                    _check(node.orelse, in_should_stop)
                elif isinstance(node, (ast.Try,)):
                    _check(node.body, in_should_stop)
                    for h in node.handlers:
                        _check(h.body, in_should_stop)
                    _check(node.orelse, in_should_stop)
                    _check(node.finalbody, in_should_stop)
                elif isinstance(node, ast.Return):
                    # Must be the LAST stmt of its block.
                    assert i == len(body) - 1, (
                        f"return in {fn.__name__} has statements after it "
                        f"(index {i} of {len(body)})"
                    )
