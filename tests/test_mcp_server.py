# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""End-to-end tests for the verify-kit MCP server (Plan 03-01 T07).

Every test launches ``verify-kit mcp serve`` as a SUBPROCESS via
``fastmcp.Client`` (stdio) or ``subprocess.Popen`` (HTTP). In-process /
threaded stdio is forbidden — pytest's own stdio handle collides with the
MCP stdio transport, so the only reliable approach is to drive the server
through pipes from a child process.

Fixture strategy:
    A session-scoped ``installed_scratch`` renders the verify-kit template
    once, creates a fresh 3.13 venv inside the scaffold, and installs the
    rendered harness in editable mode (``uv pip install -e .`` from the
    scaffold root — Plan 03-01 acceptance criterion). Subsequent tests
    spawn ``<venv>/bin/verify-kit`` so the MCP server runs under the
    project's own pinned interpreter.

Skips:
    The ``installed_scratch`` fixture skips the test if ``uv`` isn't on
    ``$PATH`` (developer machines without uv shouldn't fail the suite).
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from tests._helpers import render_scratch_project


# ── canonical 13-tool roster (Plan 03-01 §2.2 of 03-RESEARCH.md) ────────────
EXPECTED_TOOL_NAMES = {
    "verify",
    "verify_check",
    "list_checks",
    "smoke",
    "trace_last",
    "debug_state",
    "debug_events",
    "eval_run",
    "eval_compare",
    "ralph_run",
    "ralph_status",
    "fix_propose",
    "describe",
}

# Annotation triples (readOnlyHint, destructiveHint, idempotentHint).
EXPECTED_ANNOTATIONS = {
    "verify":       (True,  False, True),
    "verify_check": (True,  False, True),
    "list_checks":  (True,  False, True),
    "smoke":        (True,  False, True),
    "trace_last":   (True,  False, True),
    "describe":     (True,  False, True),
    "ralph_status": (True,  False, True),
    "ralph_run":    (False, False, False),
    "fix_propose":  (True,  False, False),
    "debug_state":  (True,  False, True),
    "debug_events": (True,  False, True),
    "eval_run":     (False, False, False),
    "eval_compare": (True,  False, True),
}


def _have_uv() -> bool:
    return shutil.which("uv") is not None


def _venv_verify_kit(scratch: Path) -> Path:
    return scratch / ".venv" / "bin" / "verify-kit"


@pytest.fixture(scope="session")
def installed_scratch(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render template + install harness into a scaffold-local venv.

    Install command is ``uv pip install -e .`` from the rendered scaffold
    root — NEVER ``uv pip install -e harness/`` and NEVER
    ``uv pip install -e tmp_path/harness`` (Plan 03-01 acceptance).
    """
    if not _have_uv():
        pytest.skip("uv not available on PATH")
    root = tmp_path_factory.mktemp("mcp-scratch")
    scratch = render_scratch_project(root)
    # Fresh 3.13 venv inside the scaffold, then install editable from root.
    subprocess.run(
        ["uv", "venv", "--python", "3.13", str(scratch / ".venv")],
        cwd=scratch,
        check=True,
        capture_output=True,
    )
    env = {**os.environ, "VIRTUAL_ENV": str(scratch / ".venv")}
    subprocess.run(
        ["uv", "pip", "install", "-e", "."],
        cwd=scratch,
        check=True,
        env=env,
        capture_output=True,
    )
    return scratch


def _stdio_client(scratch: Path):
    """Build a fastmcp Client wrapping a subprocess StdioTransport."""
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command=str(_venv_verify_kit(scratch)),
        args=["mcp", "serve"],
        cwd=str(scratch),
    )
    return Client(transport)


def _run_async(coro):
    return asyncio.run(coro)


# ── T07 #1: list_tools returns the 13 canonical names ───────────────────────


def test_list_tools_returns_thirteen_names(installed_scratch: Path) -> None:
    async def go() -> set[str]:
        async with _stdio_client(installed_scratch) as client:
            tools = await client.list_tools()
            return {t.name for t in tools}

    names = _run_async(go())
    assert names == EXPECTED_TOOL_NAMES, (
        f"missing={EXPECTED_TOOL_NAMES - names} extra={names - EXPECTED_TOOL_NAMES}"
    )


# ── T07 #2: annotation triples match the §2.2 table ─────────────────────────


def test_annotations_match_table(installed_scratch: Path) -> None:
    async def go() -> dict[str, tuple[bool | None, bool | None, bool | None]]:
        async with _stdio_client(installed_scratch) as client:
            tools = await client.list_tools()
            out: dict[str, tuple] = {}
            for t in tools:
                ann = t.annotations
                out[t.name] = (
                    getattr(ann, "readOnlyHint", None),
                    getattr(ann, "destructiveHint", None),
                    getattr(ann, "idempotentHint", None),
                )
            return out

    actual = _run_async(go())
    mismatches: list[str] = []
    for name, expected in EXPECTED_ANNOTATIONS.items():
        got = actual.get(name)
        if got != expected:
            mismatches.append(f"{name}: expected {expected}, got {got}")
    assert not mismatches, "\n".join(mismatches)


# ── T07 #3: subprocess cwd flows through; process CWD is ignored ────────────


def test_stdio_serve_does_not_use_process_cwd(
    installed_scratch: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Set process CWD to tmp_path_a; spawn server with cwd=scratch (=tmp_path_b).

    The MCP ``list_checks`` tool reads from the registry, which doesn't
    touch the filesystem — but ``verify`` writes ``.verify/`` to the
    subprocess cwd. We invoke ``verify`` and assert the artifacts land in
    the scratch dir, NOT in the parent process CWD (tmp_path).
    """
    other_dir = tmp_path / "elsewhere"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    async def go() -> None:
        async with _stdio_client(installed_scratch) as client:
            # Pick the cheapest call to force a .verify/ write.
            await client.call_tool("smoke", {})

    _run_async(go())

    # `.verify/` must exist under the scratch root, not under the parent CWD.
    assert (installed_scratch / ".verify").exists(), (
        ".verify/ was not written to the scaffold root"
    )
    assert not (other_dir / ".verify").exists(), (
        f".verify/ leaked to process CWD {other_dir}"
    )


# ── T07 #4: HTTP bearer-token is required ───────────────────────────────────


def _wait_port_open(host: str, port: int, timeout_s: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            try:
                if s.connect_ex((host, port)) == 0:
                    return True
            except OSError:
                pass
        time.sleep(0.1)
    return False


def _pick_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_http_bearer_required(installed_scratch: Path) -> None:
    port = _pick_free_port()
    proc = subprocess.Popen(
        [
            str(_venv_verify_kit(installed_scratch)),
            "mcp",
            "serve",
            "--http",
            f":{port}",
            "--token=secret-t",
        ],
        cwd=installed_scratch,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        if not _wait_port_open("127.0.0.1", port, timeout_s=60.0):
            # Process crashed or is too slow. Capture stderr for diagnostics.
            try:
                stdout_b, stderr_b = proc.communicate(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout_b, stderr_b = proc.communicate()
            raise AssertionError(
                "MCP server did not open TCP socket within 20s.\n"
                f"STDOUT:\n{stdout_b.decode(errors='replace')[:2000]}\n"
                f"STDERR:\n{stderr_b.decode(errors='replace')[:2000]}"
            )
        # No header → 401.
        r_noauth = httpx.post(
            f"http://127.0.0.1:{port}/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            timeout=3.0,
        )
        assert r_noauth.status_code == 401, (
            f"expected 401 without bearer, got {r_noauth.status_code}: {r_noauth.text[:200]}"
        )
        # Wrong token → 401.
        r_wrong = httpx.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={"Authorization": "Bearer wrong"},
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            timeout=3.0,
        )
        assert r_wrong.status_code == 401
        # Correct token → forwarded (not 401). We accept any non-401 status
        # because the underlying MCP transport may demand Accept/Content-Type
        # negotiation we don't model here; 200/4xx other than 401 all mean
        # auth passed.
        r_ok = httpx.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={
                "Authorization": "Bearer secret-t",
                "Accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            timeout=3.0,
        )
        assert r_ok.status_code != 401, (
            f"correct bearer was rejected with 401: {r_ok.text[:200]}"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()


# ── T05: --http without --token exits with E_MCP_AUTH_REQUIRED ──────────────


def test_http_without_token_exits_bad_input(installed_scratch: Path) -> None:
    proc = subprocess.run(
        [str(_venv_verify_kit(installed_scratch)), "mcp", "serve", "--http", ":1"],
        cwd=installed_scratch,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2, f"expected exit 2, got {proc.returncode}"
    assert "E_MCP_AUTH_REQUIRED" in proc.stderr, proc.stderr[:500]


# ── T07 sanity: AST mutation test (deliberately fails when violated) ────────
# Verified manually in the executor session — see SUMMARY.md "Mutation testing
# notes". We do NOT mutate source in CI to keep tests hermetic.
