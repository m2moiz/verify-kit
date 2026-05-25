# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Phase 4 Plan 04-06 — opt-in flag polarity matrix (outer test).

Exercises all four (has_logfire x has_fastapi_mcp) combinations from
the OUTSIDE using the copier Python API (same pattern as test_phase04_scaffold_polarity.py).

Four cells:
  (False, False) — neither opt-in flag: no logfire, no mcp in rendered project
  (True,  False) — logfire only
  (False, True ) — mcp only
  (True,  True ) — both opt-in flags active

REVIEW-CHECKLIST compliance:
  §1 cwd: render_scratch_project uses tmp_path fixture; no subprocess calls
     that could drift cwd. The copier Python API resolves paths from the repo
     root, not process cwd.
  §3 contract drift: assertions are keyed to the exact strings produced by
     Plan 04-02 T07 (main.py shape) and Plan 04-06 T01 (pyproject.toml deps).
     If either plan renames the relevant identifiers, these tests break loudly.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


# ── Shared base data ─────────────────────────────────────────────────────────

_BASE: dict[str, object] = {
    "project_name": "OptinPolarity",
    "project_description": "opt-in polarity test",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
    "has_backend": True,
    "has_db": False,
    "has_llm": False,
    "has_claude_code": False,
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    "has_devcontainer": False,
    "llm_backend": "none",
}


# ── Parametrized polarity matrix ─────────────────────────────────────────────


@pytest.mark.parametrize("has_logfire,has_fastapi_mcp", [
    (False, False),
    (True, False),
    (False, True),
    (True, True),
])
def test_optin_polarity_matrix(
    tmp_path: Path,
    has_logfire: bool,
    has_fastapi_mcp: bool,
) -> None:
    """All four (logfire x fastapi_mcp) combinations render without leaks."""
    scratch = render_scratch_project(
        tmp_path,
        **{**_BASE, "has_logfire": has_logfire, "has_fastapi_mcp": has_fastapi_mcp},  # type: ignore[arg-type]
    )

    main_py = (scratch / "app" / "main.py").read_text()
    pyproject = (scratch / "pyproject.toml").read_text()

    if has_logfire:
        assert "import logfire" in main_py, (
            "import logfire missing from main.py when has_logfire=true"
        )
        assert "logfire.configure()" in main_py, (
            "logfire.configure() missing from main.py when has_logfire=true"
        )
        assert "logfire[" in pyproject, (
            "logfire>= dep missing from pyproject.toml when has_logfire=true"
        )
    else:
        assert "import logfire" not in main_py, (
            "import logfire leaked into main.py when has_logfire=false"
        )
        assert "logfire[" not in pyproject, (
            "logfire>= dep leaked into pyproject.toml when has_logfire=false"
        )

    if has_fastapi_mcp:
        assert "FastApiMCP" in main_py, (
            "FastApiMCP missing from main.py when has_fastapi_mcp=true"
        )
        assert "fastapi-mcp>=" in pyproject, (
            "fastapi-mcp>= dep missing from pyproject.toml when has_fastapi_mcp=true"
        )
    else:
        assert "FastApiMCP" not in main_py, (
            "FastApiMCP leaked into main.py when has_fastapi_mcp=false"
        )
        assert "fastapi-mcp>=" not in pyproject, (
            "fastapi-mcp>= dep leaked into pyproject.toml when has_fastapi_mcp=false"
        )
