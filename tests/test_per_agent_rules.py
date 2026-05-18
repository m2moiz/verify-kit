"""Conditional-rendering matrix for per-agent rules + MCP snippets.

Plan 03-03 ships per-agent thin-pointer files (Cursor `.mdc` + `mcp.json`,
Windsurf rules, Copilot instructions, Continue/Zed MCP configs). Each one is
gated on a Copier prompt (`has_cursor`, `has_windsurf`, ...). These tests
render the template with each prompt flipped on/off and assert that the right
files appear/disappear and that key payload fields are correct.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from tests._helpers import render_scratch_project


def _strip_frontmatter(text: str) -> str:
    """Strip a YAML frontmatter block (delimited by --- ... ---) from the head."""
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2]


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _parse_jsonc(text: str) -> dict:
    """Minimal JSONC parser: strip // line comments, then json.loads.

    Does NOT handle /* */ block comments — none of the templates use them.
    """
    stripped = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
    return json.loads(stripped)


# --- Cursor ------------------------------------------------------------------


def test_cursor_on_off(tmp_path: Path) -> None:
    on = render_scratch_project(tmp_path / "on", has_cursor=True)
    off = render_scratch_project(tmp_path / "off", has_cursor=False)

    assert (on / ".cursor" / "rules" / "verify-kit.mdc").exists()
    assert (on / ".cursor" / "mcp.json").exists()
    assert not (off / ".cursor").exists()


def test_cursor_rule_word_count(tmp_path: Path) -> None:
    on = render_scratch_project(tmp_path, has_cursor=True)
    rule = on / ".cursor" / "rules" / "verify-kit.mdc"
    body = _strip_frontmatter(rule.read_text())
    wc = _word_count(body)
    assert wc <= 200, f"Cursor rule body is {wc} words (Cursor truncates >200)"


def test_cursor_rule_alwaysapply_true(tmp_path: Path) -> None:
    on = render_scratch_project(tmp_path, has_cursor=True)
    rule = on / ".cursor" / "rules" / "verify-kit.mdc"
    text = rule.read_text()
    assert text.startswith("---\n"), "Cursor rule must open with YAML frontmatter"
    # Frontmatter is shallow YAML; a simple regex is enough.
    m = re.search(r"^alwaysApply:\s*(\S+)\s*$", text, flags=re.MULTILINE)
    assert m is not None, "alwaysApply key missing from frontmatter"
    assert m.group(1).lower() == "true", "alwaysApply must be true"


def test_cursor_mcp_command_correct(tmp_path: Path) -> None:
    on = render_scratch_project(tmp_path, has_cursor=True)
    mcp = on / ".cursor" / "mcp.json"
    data = _parse_jsonc(mcp.read_text())
    server = data["mcpServers"]["verify-kit"]
    assert server["command"] == "verify-kit"
    assert server["args"] == ["mcp", "serve"]


# --- Windsurf ---------------------------------------------------------------


def test_windsurf_on_off(tmp_path: Path) -> None:
    on = render_scratch_project(tmp_path / "on", has_windsurf=True)
    off = render_scratch_project(tmp_path / "off", has_windsurf=False)

    rule = on / ".windsurf" / "rules" / "verify-kit.md"
    assert rule.exists()
    text = rule.read_text()
    assert "AGENTS.md" in text, "Windsurf rule must link to AGENTS.md"
    line_count = len(text.splitlines())
    assert line_count <= 80, f"Windsurf rule is {line_count} lines (target ≤80)"

    assert not (off / ".windsurf").exists()


# --- Copilot ----------------------------------------------------------------


def test_copilot_on_off(tmp_path: Path) -> None:
    on = render_scratch_project(tmp_path / "on", has_copilot=True)
    off = render_scratch_project(tmp_path / "off", has_copilot=False)

    copilot = on / ".github" / "copilot-instructions.md"
    assert copilot.exists()
    assert "AGENTS.md" in copilot.read_text()

    # When has_copilot=false, the file is absent BUT the Phase 1 unconditional
    # .github/workflows/ci.yml still ships (the collision-with-Phase-1 case
    # from RESEARCH.md §4.2).
    assert not (off / ".github" / "copilot-instructions.md").exists()
    assert (off / ".github" / "workflows" / "ci.yml").exists(), (
        "Phase 1's unconditional .github/workflows/ci.yml must survive "
        "has_copilot=false (RESEARCH.md §4.2)."
    )


# --- Continue ---------------------------------------------------------------


def test_continue_on_off(tmp_path: Path) -> None:
    on = render_scratch_project(tmp_path / "on", has_continue=True)
    off = render_scratch_project(tmp_path / "off", has_continue=False)

    cfg = on / ".continue" / "mcpServers" / "verify-kit.json"
    assert cfg.exists()
    data = json.loads(cfg.read_text())
    assert data["name"] == "verify-kit"
    assert data["command"] == "verify-kit"
    assert data["args"] == ["mcp", "serve"]

    assert not (off / ".continue").exists()


# --- Zed --------------------------------------------------------------------


def test_zed_on_off(tmp_path: Path) -> None:
    on = render_scratch_project(tmp_path / "on", has_zed=True)
    off = render_scratch_project(tmp_path / "off", has_zed=False)

    settings = on / ".zed" / "settings.json"
    assert settings.exists()
    data = _parse_jsonc(settings.read_text())
    server = data["context_servers"]["verify-kit"]
    assert server["command"] == "verify-kit"
    assert server["args"] == ["mcp", "serve"]

    assert not (off / ".zed").exists()
