"""Phase 3 + Phase 5 contract: harness.mcp must work under fastmcp 3.x.

Phase 5's dep bump changed fastmcp from 2.x to ``>=3.3,<4``. The Phase 3
harness/mcp/ code was authored against fastmcp 2.x. These tests render a
scratch with has_backend=True so the rendered project picks up the 3.x
fastmcp from its own venv, then exercises the actual import + construction
surface used by harness.mcp.server.serve() and harness.mcp.tools.register_tools().

Bead verify-kit-xw4. If either test fails, the failure tells the executor
WHAT moved in fastmcp 3.x; the fix belongs in a follow-up phase, not in
the backlog-closeout plan that filed this test.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tests._helpers import _CLEAN_ENV, render_scratch_project


pytestmark = [
    pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed"),
]


def _render_and_sync(tmp_path: Path) -> Path:
    """Render a has_backend=True, has_llm=True scratch and uv-sync its venv.

    The sync materializes fastmcp 3.x (per pyproject's ``fastmcp>=3.3,<4``
    pin from Phase 5) inside the scratch's own .venv, so subsequent
    ``uv run`` invocations against this cwd resolve fastmcp from there.
    """
    scratch = render_scratch_project(
        tmp_path,
        has_backend=True,
        has_llm=True,
        llm_backend="langfuse-cloud",
        has_db=True,
        has_logfire=False,
        has_fastapi_mcp=False,
    )
    subprocess.run(
        ["uv", "sync", "--group", "dev"],
        cwd=scratch, check=True, timeout=600, env=_CLEAN_ENV,
        capture_output=True,
    )
    return scratch


def test_harness_mcp_serve_importable_under_fastmcp_3x(tmp_path: Path) -> None:
    """harness.mcp.server.serve + harness.mcp.tools.register_tools must
    import cleanly under fastmcp 3.x (no AttributeError, no missing symbol).
    """
    scratch = _render_and_sync(tmp_path)
    result = subprocess.run(
        ["uv", "run", "--", "python", "-c",
         "from harness.mcp.server import serve; "
         "from harness.mcp.tools import register_tools; "
         "from fastmcp import FastMCP; "
         "mcp = FastMCP(name='probe'); "
         "from pathlib import Path; "
         "register_tools(mcp, cwd=Path('.')); "
         "print('OK')"],
        cwd=scratch, env=_CLEAN_ENV, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        f"harness.mcp import/register failed under fastmcp 3.x:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK" in result.stdout


def test_tool_annotations_constructible_under_fastmcp_3x(tmp_path: Path) -> None:
    """mcp.types.ToolAnnotations(readOnlyHint=..., destructiveHint=...,
    idempotentHint=...) must still construct under the mcp version pulled
    by fastmcp 3.x. If the field names moved, harness.mcp.tools will
    TypeError at import time.
    """
    scratch = _render_and_sync(tmp_path)
    result = subprocess.run(
        ["uv", "run", "--", "python", "-c",
         "from mcp.types import ToolAnnotations; "
         "a = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True); "
         "print(repr(a))"],
        cwd=scratch, env=_CLEAN_ENV, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        f"ToolAnnotations construction failed under fastmcp 3.x's mcp pin:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "ToolAnnotations" in result.stdout or "readOnlyHint" in result.stdout
