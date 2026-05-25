# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Phase 3 cross-cutting template smoke (Plan 03-05 T01).

Renders the verify-kit template across an agent-flag matrix and asserts
the union of conditional-file-presence invariants from Plans 03-01..04.

This test is intentionally a *presence* check, not a contract check —
the per-tool MCP↔CLI byte-identical matrix lives in
``tests/test_mcp_cli_byte_identical.py`` (Plan 03-01 T08), and the
file-content scans live in ``tests/test_p3_review_checklist.py``
(Plan 03-05 T03). This file just answers: "for every supported flag
combo, does the right set of files exist on disk?"

Every ``subprocess.run`` carries ``cwd=`` explicitly (REVIEW-CHECKLIST §3).
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


# Matrix rows: (has_claude_code, has_cursor, has_windsurf, has_copilot,
#               has_continue, has_zed, has_backend)
_MATRIX = [
    pytest.param(True, True, True, True, True, True, True, id="all-on"),
    pytest.param(True, False, False, False, False, False, True, id="claude-backend"),
    pytest.param(False, False, False, False, False, False, True, id="bare-backend"),
    pytest.param(True, True, True, True, True, True, False, id="all-agents-no-backend"),
]


@pytest.mark.parametrize(
    "has_claude_code,has_cursor,has_windsurf,has_copilot,has_continue,has_zed,has_backend",
    _MATRIX,
)
def test_template_renders_with_matrix(
    tmp_path: Path,
    has_claude_code: bool,
    has_cursor: bool,
    has_windsurf: bool,
    has_copilot: bool,
    has_continue: bool,
    has_zed: bool,
    has_backend: bool,
) -> None:
    """Render the template with the given agent-flag combo and assert
    that conditional files appear iff their flag is enabled."""
    scratch = render_scratch_project(
        tmp_path,
        has_claude_code=has_claude_code,
        has_cursor=has_cursor,
        has_windsurf=has_windsurf,
        has_copilot=has_copilot,
        has_continue=has_continue,
        has_zed=has_zed,
        has_backend=has_backend,
    )

    # --- Conditional file presence (REVIEW-CHECKLIST: each flag gates its own dir).
    _assert_exists_iff(scratch / ".claude/hooks/post-tool-use.sh", has_claude_code)
    _assert_exists_iff(scratch / ".claude/hooks/stop.sh", has_claude_code)
    _assert_exists_iff(scratch / ".claude/settings.json.example", has_claude_code)
    _assert_exists_iff(
        scratch / ".claude/skills/verify-kit-verify/SKILL.md", has_claude_code
    )

    _assert_exists_iff(scratch / ".cursor/rules/verify-kit.mdc", has_cursor)
    _assert_exists_iff(scratch / ".cursor/mcp.json", has_cursor)

    _assert_exists_iff(scratch / ".windsurf/rules/verify-kit.md", has_windsurf)

    _assert_exists_iff(scratch / ".github/copilot-instructions.md", has_copilot)

    _assert_exists_iff(
        scratch / ".continue/mcpServers/verify-kit.json", has_continue
    )

    _assert_exists_iff(scratch / ".zed/settings.json", has_zed)

    # --- Unconditional presence (Phase 1 invariants).
    assert (scratch / ".github/workflows/ci.yml").exists(), (
        ".github/workflows/ci.yml must exist regardless of agent flags"
    )
    for vscode_file in ("extensions.json", "settings.json", "tasks.json", "launch.json"):
        assert (scratch / ".vscode" / vscode_file).exists(), (
            f".vscode/{vscode_file} must exist regardless of agent flags"
        )
    assert (scratch / "scripts/ralph.sh").exists(), (
        "scripts/ralph.sh must exist regardless of agent flags"
    )

    # --- Executable bit on shipped shell scripts.
    shell_paths = [scratch / "scripts/ralph.sh"]
    if has_claude_code:
        shell_paths.append(scratch / ".claude/hooks/post-tool-use.sh")
        shell_paths.append(scratch / ".claude/hooks/stop.sh")
    for sh in shell_paths:
        mode = sh.stat().st_mode
        assert mode & stat.S_IXUSR, f"{sh} is not executable (mode={oct(mode)})"

    # --- launch.json shape mirrors has_backend.
    launch = json.loads((scratch / ".vscode/launch.json").read_text())
    configs = launch.get("configurations", [])
    if has_backend:
        assert len(configs) == 2, (
            f"launch.json should have 2 configurations when has_backend=True, "
            f"got {len(configs)}"
        )
        assert "compounds" in launch and len(launch["compounds"]) == 1, (
            "launch.json should include a compound entry when has_backend=True"
        )
    else:
        assert len(configs) == 1, (
            f"launch.json should have 1 configuration when has_backend=False, "
            f"got {len(configs)}"
        )
        assert not launch.get("compounds"), (
            "launch.json should not include compounds when has_backend=False"
        )

    # --- `verify-kit mcp serve --help` (skip when verify-kit is not on PATH).
    if shutil.which("verify-kit") is None:
        pytest.skip("verify-kit not on PATH in this environment")
    proc = subprocess.run(
        ["verify-kit", "mcp", "serve", "--help"],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"verify-kit mcp serve --help exited {proc.returncode}: "
        f"stderr={proc.stderr[:300]}"
    )


def _assert_exists_iff(path: Path, expected: bool) -> None:
    """Assert ``path`` exists if and only if ``expected`` is True."""
    if expected:
        assert path.exists(), f"expected {path} to exist (flag enabled), but it is missing"
    else:
        assert not path.exists(), (
            f"expected {path} to NOT exist (flag disabled), but it is present"
        )
