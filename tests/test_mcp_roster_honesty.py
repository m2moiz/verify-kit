# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""MCP roster-honesty guard (verify-kit-dy4).

The 13-tool MCP roster mixes 8 real tools and 4 not-yet-implemented stubs.
``describe.mcp_tools`` is the machine-readable signal of which is which. This
guard asserts that signal does not lie in EITHER direction:

  * Every tool marked ``implemented=true`` must NOT return a
    ``status == "not_implemented"`` payload  (catches "lying about a stub"
    where a real tool secretly degraded to a stub, OR the roster mislabels a
    stub as real).
  * Every tool marked ``implemented=false`` MUST be one of the 4 known stubs,
    MUST return ``status == "not_implemented"``, AND carry the honest
    ``note`` + ``tracking`` fields  (catches "regressing a real tool" — a tool
    that quietly became a stub while the roster still claims it works, and the
    old lying ``available_in_phase`` shape).

Spawns the MCP server as a subprocess via the same fixture/transport the
byte-identical contract suite uses (in-process stdio collides with pytest's
own stdio handle).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

# The 4 tools that are intentionally stubs (not yet implemented; v0.3).
EXPECTED_STUBS = {"debug_state", "debug_events", "eval_run", "eval_compare"}
_TRACKING = "verify-kit-dy4"

# Real tools that take no required args and are cheap/safe to invoke for the
# "implemented tools must not return a not_implemented payload" direction.
# ralph_run is omitted (it executes the Ralph loop / writes state); its real
# behaviour is covered by test_cat_b_ralph_run_shape. We still assert the
# roster MARKS ralph_run implemented=true via the describe.mcp_tools check.
_SAFE_IMPLEMENTED_CALLS = {
    "verify": {},
    "verify_check": {"name": "mise.toml.valid"},
    "list_checks": {},
    "smoke": {},
    "trace_last": {},
    "describe": {},
    "ralph_status": {},
    "fix_propose": {},
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


def _run_async(coro):
    return asyncio.run(coro)


def _mcp_text(result) -> str:
    if hasattr(result, "content") and result.content:
        for block in result.content:
            text = getattr(block, "text", None)
            if text is not None:
                return text
    raise AssertionError(f"no text content in MCP result: {result!r}")


def _mcp_call(scratch: Path, tool: str, args: dict | None = None) -> Any:
    async def go():
        async with _stdio_client(scratch) as client:
            return await client.call_tool(tool, args or {})

    return json.loads(_mcp_text(_run_async(go())))


def test_describe_exposes_mcp_tools_roster(mcp_installed_scratch: Path) -> None:
    """describe.mcp_tools is present and lists all 13 tools as {name,
    implemented, note}."""
    envelope = _mcp_call(mcp_installed_scratch, "describe")
    roster = envelope.get("mcp_tools")
    assert isinstance(roster, list), (
        f"describe must expose a machine-readable mcp_tools list: {type(roster)}"
    )
    names = {t["name"] for t in roster}
    assert len(roster) == 13, f"expected 13 tools, got {len(roster)}: {names}"
    for entry in roster:
        assert set(entry) >= {"name", "implemented", "note"}, entry
        assert isinstance(entry["implemented"], bool), entry
    # The implemented=false set must be EXACTLY the 4 known stubs.
    stubs = {t["name"] for t in roster if not t["implemented"]}
    assert stubs == EXPECTED_STUBS, (
        f"roster stub set drifted: expected {EXPECTED_STUBS}, got {stubs}"
    )


def test_roster_honesty_both_directions(mcp_installed_scratch: Path) -> None:
    """The implemented flag must not lie either way.

    implemented=true  -> tool must NOT return status=='not_implemented'
    implemented=false -> tool MUST return status=='not_implemented' (+honest note)
    """
    envelope = _mcp_call(mcp_installed_scratch, "describe")
    roster = {t["name"]: t for t in envelope["mcp_tools"]}

    # Direction 1: every implemented tool must really work (no stub payload).
    for tool, entry in roster.items():
        if not entry["implemented"]:
            continue
        if tool not in _SAFE_IMPLEMENTED_CALLS:
            # ralph_run: covered elsewhere; just assert the roster claim is sane.
            continue
        result = _mcp_call(mcp_installed_scratch, tool, _SAFE_IMPLEMENTED_CALLS[tool])
        status = result.get("status") if isinstance(result, dict) else None
        assert status != "not_implemented", (
            f"{tool!r} is marked implemented=true but returned a "
            f"not_implemented payload: {result!r}"
        )

    # Direction 2: every stub tool must honestly report not_implemented.
    for tool in EXPECTED_STUBS:
        assert roster[tool]["implemented"] is False, (
            f"{tool!r} is a stub but roster marks it implemented=true"
        )
        result = _mcp_call(mcp_installed_scratch, tool)
        assert result.get("status") == "not_implemented", (
            f"stub {tool!r} must return status=not_implemented: {result!r}"
        )
        # The honest shape — NOT the old lying available_in_phase field.
        assert "available_in_phase" not in result, (
            f"stub {tool!r} still carries the lying available_in_phase field: {result!r}"
        )
        assert result.get("tracking") == _TRACKING, result
        assert tool in result.get("note", ""), result
