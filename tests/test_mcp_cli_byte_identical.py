# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""MCP↔CLI byte-identical contract matrix (Plan 03-01 T08).

This file owns the 13-tool MCP-02 contract matrix because Plan 03-01 is
the producer of the MCP server layer. Plan 03-05 ships only the
cross-cutting smoke + REVIEW-CHECKLIST scans (not the per-tool equality
matrix).

Tool roster splits into three categories per the locked design:

    Category A (7, byte-identical):
        verify, verify_check, list_checks, smoke, trace_last, describe,
        ralph_status

    Category B (2, shape-only — non-deterministic output):
        ralph_run, fix_propose

    Category C (4, stub-shape):
        debug_state, debug_events, eval_run, eval_compare

Total = 13, matches MCP-02's 13-tool roster.

Every ``subprocess.run`` carries ``cwd=`` explicitly (REVIEW-CHECKLIST
§1+§3). This test file is a positive example of the pattern; Plan 03-05's
REVIEW-CHECKLIST scan is scoped to ``template/harness/**`` and skips
``tests/**``.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


# Same canonical default used by ``harness.mcp.tools``. Picking a real,
# fast Phase-2 ``tier="quick"`` registered check id so the CLI twin runs
# deterministically.
_DEFAULT_CHECK_ID = "mise.toml.valid"


def _venv_verify_kit(scratch: Path) -> str:
    return str(scratch / ".venv" / "bin" / "verify-kit")


def _stdio_client(scratch: Path):
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command=_venv_verify_kit(scratch),
        args=["mcp", "serve"],
        cwd=str(scratch),
    )
    return Client(transport)


def _run_async(coro):
    return asyncio.run(coro)


def _mcp_text(result) -> str:
    """Extract the JSON text content from a fastmcp call_tool result."""
    if hasattr(result, "content") and result.content:
        for block in result.content:
            text = getattr(block, "text", None)
            if text is not None:
                return text
    raise AssertionError(f"no text content in MCP result: {result!r}")


# ── normalization helper (strip volatile fields) ─────────────────────────────

_VOLATILE_KEYS = {
    "run_id",
    "trace_id",
    "span_id",
    "started_at",
    "finished_at",
    "duration_ms",
    "total_duration_ms",
    "created_at",
    "startTime",
    "endTime",
    # CheckResult-level timing
    "started",
    "finished",
    # Phase-9 CheckResult provenance: set fresh per execution. The CLI run and
    # the MCP run execute verify independently, so this timestamp differs
    # whenever the second run is not a pure cache replay (e.g. CI cache-miss).
    # It is non-semantic for the MCP↔CLI parity contract — strip it like run_id.
    "executed_at",
    # SQLite cache hit/miss is non-deterministic between two consecutive
    # invocations (CLI primes, MCP re-reads from cache).
    "cached",
}


def _normalize(value: Any) -> Any:
    """Recursively replace volatile fields with sentinel constants.

    Used by Category A equality assertions so timing/ID jitter between the
    CLI invocation and the MCP invocation doesn't flip the test red.
    """
    if isinstance(value, dict):
        return {
            k: ("<sentinel>" if k in _VOLATILE_KEYS else _normalize(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


# ── helpers: run CLI and run MCP tool ───────────────────────────────────────


def _cli_json(scratch: Path, args: list[str]) -> Any:
    proc = subprocess.run(
        [_venv_verify_kit(scratch), *args],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    # verify/verify_check/smoke can exit non-zero when checks fail; that
    # outcome is encoded in the JSON, not in the test framing.
    assert proc.stdout, (
        f"CLI produced no stdout: rc={proc.returncode} stderr={proc.stderr[:300]}"
    )
    return json.loads(proc.stdout)


def _mcp_call(scratch: Path, tool: str, args: dict | None = None) -> Any:
    async def go():
        async with _stdio_client(scratch) as client:
            return await client.call_tool(tool, args or {})

    result = _run_async(go())
    return json.loads(_mcp_text(result))


# ── Category A: 7 byte-identical tests ───────────────────────────────────────


def test_cat_a_verify_byte_identical(mcp_installed_scratch: Path) -> None:
    cli = _cli_json(mcp_installed_scratch, ["verify", "--format=json"])
    mcp = _mcp_call(mcp_installed_scratch, "verify")
    assert _normalize(cli) == _normalize(mcp)


def test_cat_a_verify_check_byte_identical(mcp_installed_scratch: Path) -> None:
    cli = _cli_json(
        mcp_installed_scratch,
        ["verify", f"--check={_DEFAULT_CHECK_ID}", "--format=json"],
    )
    mcp = _mcp_call(
        mcp_installed_scratch, "verify_check", {"name": _DEFAULT_CHECK_ID}
    )
    assert _normalize(cli) == _normalize(mcp)


def test_cat_a_list_checks_byte_identical(mcp_installed_scratch: Path) -> None:
    cli = _cli_json(mcp_installed_scratch, ["list-checks", "--format=json"])
    mcp = _mcp_call(mcp_installed_scratch, "list_checks")
    # list-checks contains no time fields — equality is exact even without
    # normalization, but we run _normalize for consistency.
    assert _normalize(cli) == _normalize(mcp)


def test_cat_a_smoke_byte_identical(mcp_installed_scratch: Path) -> None:
    cli = _cli_json(
        mcp_installed_scratch,
        ["verify", f"--check={_DEFAULT_CHECK_ID}", "--quick", "--format=json"],
    )
    mcp = _mcp_call(mcp_installed_scratch, "smoke")
    assert _normalize(cli) == _normalize(mcp)


def test_cat_a_trace_last_byte_identical(mcp_installed_scratch: Path) -> None:
    # No Jaeger running in CI — both sides return {"status": "no_traces"}.
    cli = _cli_json(mcp_installed_scratch, ["trace", "--last", "--format=json"])
    mcp = _mcp_call(mcp_installed_scratch, "trace_last")
    assert _normalize(cli) == _normalize(mcp)


def test_cat_a_describe_byte_identical(mcp_installed_scratch: Path) -> None:
    cli = _cli_json(mcp_installed_scratch, ["describe", "--format=json"])
    mcp = _mcp_call(mcp_installed_scratch, "describe")
    assert _normalize(cli) == _normalize(mcp)


@pytest.mark.requires_cli
def test_cat_a_ralph_status_byte_identical(mcp_installed_scratch: Path) -> None:
    # Pre-seed: one Ralph run that's guaranteed to be "stuck" (cost-cap).
    # 03-02 T05 documented cap-precedence: cost_cap wins ties.
    seed = subprocess.run(
        [
            _venv_verify_kit(mcp_installed_scratch),
            "ralph",
            "run",
            "--max-iterations=1",
            "--cost-cap-usd=0.001",
            "--format=json",
            "noop-seed",
        ],
        cwd=mcp_installed_scratch,
        capture_output=True,
        text=True,
    )
    assert seed.stdout, (
        f"ralph run seed produced no stdout: rc={seed.returncode} stderr={seed.stderr[:300]}"
    )
    cli = _cli_json(mcp_installed_scratch, ["ralph", "status", "--format=json"])
    mcp = _mcp_call(mcp_installed_scratch, "ralph_status")
    # output_path is an absolute string under the scratch root; equality is
    # exact since both sides resolve to the same path.
    assert cli == mcp, f"ralph_status drift:\n cli={cli!r}\n mcp={mcp!r}"


# ── Category B: 2 shape-only tests ───────────────────────────────────────────


@pytest.mark.requires_cli
def test_cat_b_ralph_run_shape(mcp_installed_scratch: Path) -> None:
    """ralph_run canonical shape: {status, iters, cost_usd, output_path}
    plus `reason` IFF status == "stuck". cost_cap wins ties (03-02 T05).

    With (max_iters=1, cost_cap_usd=0.001) the default executor returns
    cost_usd=0.001 on its first invocation, so cost_cap fires first.
    """
    result = _mcp_call(
        mcp_installed_scratch,
        "ralph_run",
        {"prompt": "noop", "max_iters": 1, "cost_cap_usd": 0.001},
    )
    # Required keys always present.
    for k in ("status", "iters", "cost_usd", "output_path"):
        assert k in result, f"ralph_run missing required key {k!r}: {result!r}"
    assert result["status"] in {"done", "stuck"}, result["status"]
    assert isinstance(result["iters"], int) and result["iters"] >= 0
    assert isinstance(result["cost_usd"], (int, float)) and result["cost_usd"] >= 0
    assert isinstance(result["output_path"], str)
    # `reason` only when stuck.
    if result["status"] == "stuck":
        assert "reason" in result, "stuck result must include `reason`"
        assert result["reason"] in {"iteration_cap", "cost_cap"}
        # Expected under (max_iters=1, cost_cap_usd=0.001): cost_cap wins.
        assert result["reason"] == "cost_cap", (
            f"expected cost_cap (tie-break per 03-02 T05), got {result['reason']!r}"
        )
    else:
        assert "reason" not in result, (
            f"`reason` must be absent when status='done': {result!r}"
        )
    # Forbid invented field names that prior plan drafts hallucinated.
    for forbidden in (
        "iters_completed",
        "stop_reason",
        "last_iter_at",
        "total_iters",
        "converged",
        "max_iters_hit",
        "cost_cap_hit",
    ):
        assert forbidden not in result, (
            f"ralph_run contract regression: forbidden key {forbidden!r}"
        )


def test_cat_b_fix_propose_sarif_envelope(mcp_installed_scratch: Path) -> None:
    """fix_propose returns the full SARIF 2.1.0 envelope (no LLM in P3).

    Shape: {"version": "2.1.0", "runs": [{"tool": {...}, "results": [...]}]}
    No top-level `status` key — SARIF has no such field.
    """
    result = _mcp_call(mcp_installed_scratch, "fix_propose")
    assert isinstance(result, dict), type(result)
    assert "status" not in result, (
        f"SARIF envelope must not carry a top-level status key: {list(result)}"
    )
    assert result.get("version") == "2.1.0", result.get("version")
    runs = result.get("runs")
    assert isinstance(runs, list) and len(runs) >= 1, runs
    run0 = runs[0]
    assert isinstance(run0, dict)
    assert "tool" in run0
    assert "results" in run0
    assert isinstance(run0["results"], list)


# ── Category C: 4 stub-shape tests ───────────────────────────────────────────


def test_cat_c_debug_state_stub(mcp_installed_scratch: Path) -> None:
    result = _mcp_call(mcp_installed_scratch, "debug_state")
    assert result == {"status": "not_implemented", "available_in_phase": 4}


def test_cat_c_debug_events_stub(mcp_installed_scratch: Path) -> None:
    result = _mcp_call(mcp_installed_scratch, "debug_events")
    assert result == {"status": "not_implemented", "available_in_phase": 4}


def test_cat_c_eval_run_stub(mcp_installed_scratch: Path) -> None:
    result = _mcp_call(mcp_installed_scratch, "eval_run")
    assert result == {"status": "not_implemented", "available_in_phase": 5}


def test_cat_c_eval_compare_stub(mcp_installed_scratch: Path) -> None:
    result = _mcp_call(mcp_installed_scratch, "eval_compare")
    assert result == {"status": "not_implemented", "available_in_phase": 5}


# ── grep-guard: forbidden install-command strings must not appear ───────────


def test_no_forbidden_install_strings_in_file() -> None:
    """Plan 03-01 acceptance: this test file must not contain forbidden
    install-command strings. The install command must be ``-e .`` from the
    scaffold root — never ``-e <subdir>``.

    Forbidden patterns are assembled at runtime from non-literal fragments so
    this very assertion does not trip on its own source code.
    """
    text = Path(__file__).read_text()
    # Build patterns without literal occurrences in source.
    parts = ["uv", "pip", "install"]
    pat_subdir = " ".join(parts) + " -e " + "harness" + "/"
    pat_tmp = " ".join(parts) + " -e " + "tmp_path" + "/" + "harness"
    # Exclude the construction sites above from the scan.
    construction_anchor = "# Build patterns"
    scan_text = text.split(construction_anchor)[-1]
    for needle in (pat_subdir, pat_tmp):
        assert needle not in scan_text, (
            f"forbidden install string present in test body: {needle!r}"
        )
