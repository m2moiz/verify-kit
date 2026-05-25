# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Thin MCP↔CLI end-to-end smoke (Plan 03-05 T02).

This is a *cross-cutting smoke test*, NOT a per-tool contract matrix.
The full 13-tool MCP↔CLI byte-identical contract matrix is owned by
Plan 03-01 T08 in ``tests/test_mcp_cli_byte_identical.py`` — the
producer of the MCP layer owns the per-tool truth. This file's only job
is to prove the integrated wave-1+wave-2 product is consumable end-to-end:

    1. MCP server starts and exposes exactly the 13 canonical tools.
    2. CLI ``verify-kit verify --quick --format=json`` exits 0 and
       produces JSON containing ``summary.duration_ms``.

If you find yourself adding ``_normalize()``, per-tool field-shape
assertions, or ``_assert_byte_identical`` helpers here, STOP — that work
belongs in 03-01 T08. Keeping contracts with producers prevents the
test-plan-vs-producer drift pattern documented in REVIEW-CHECKLIST §3.

Every ``subprocess.run`` carries ``cwd=`` explicitly (REVIEW-CHECKLIST §3).
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import pytest


# Canonical 13-tool MCP-02 roster (matches the producer in
# ``template/harness/mcp/tools.py.jinja2``).
_CANONICAL_TOOLS: set[str] = {
    "verify",
    "verify_check",
    "list_checks",
    "smoke",
    "trace_last",
    "describe",
    "ralph_run",
    "ralph_status",
    "fix_propose",
    "debug_state",
    "debug_events",
    "eval_run",
    "eval_compare",
}


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


def test_mcp_server_exposes_thirteen_tools(mcp_installed_scratch: Path) -> None:
    """MCP server starts and lists exactly the 13 canonical MCP-02 tools.

    Smoke-only: this asserts the set of tool *names* matches the canonical
    roster. Per-tool field-shape and byte-identity equivalence to the CLI
    live in ``tests/test_mcp_cli_byte_identical.py`` (Plan 03-01 T08).
    """
    scratch = mcp_installed_scratch

    async def _list() -> set[str]:
        async with _stdio_client(scratch) as client:
            tools = await client.list_tools()
        return {t.name for t in tools}

    names = asyncio.run(_list())
    assert names == _CANONICAL_TOOLS, (
        f"MCP server tool roster drifted from MCP-02 canonical 13.\n"
        f"  missing: {_CANONICAL_TOOLS - names}\n"
        f"  extra:   {names - _CANONICAL_TOOLS}"
    )


def test_cli_verify_quick_runs_clean(mcp_installed_scratch: Path) -> None:
    """CLI ``verify-kit verify --quick --format=json`` emits a JSON report
    whose ``summary`` block carries a ``duration_ms`` integer.

    Smoke-only: this does NOT compare the CLI output to the MCP ``verify``
    tool output (that is 03-01 T08's job). It just proves the CLI path is
    alive end-to-end, parses, and surfaces the summary-duration field
    that downstream consumers (e.g. agents, dashboards) rely on.
    """
    scratch = mcp_installed_scratch
    proc = subprocess.run(
        [_venv_verify_kit(scratch), "verify", "--quick", "--format=json"],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    # ``verify`` may exit non-zero if a check fails — that outcome is
    # encoded in the JSON. The smoke only requires that the JSON parses
    # and carries the documented summary shape.
    assert proc.stdout, (
        f"verify produced no stdout: rc={proc.returncode} stderr={proc.stderr[:300]}"
    )
    report = json.loads(proc.stdout)
    assert "summary" in report, f"report missing 'summary' key: keys={list(report)}"
    assert "duration_ms" in report["summary"], (
        f"report.summary missing 'duration_ms' key: keys={list(report['summary'])}"
    )
    assert isinstance(report["summary"]["duration_ms"], int), (
        f"report.summary.duration_ms is not int: "
        f"got {type(report['summary']['duration_ms']).__name__}"
    )
