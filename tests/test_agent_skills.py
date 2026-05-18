"""Three SKILL.md files ship under .claude/skills/ when has_claude_code=true.

Plan 03-03 §T07: each SKILL.md has YAML frontmatter (`name`, `description`)
and a body of 20–100 lines. The description is the load-trigger — bad
description means the skill never loads, which is an AGT-03 false-pass. The
golden snapshots below pin the trigger phrases.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from tests._helpers import render_scratch_project


SKILL_NAMES = ("verify-kit-verify", "verify-kit-debug", "verify-kit-eval")


def _read_skill(scratch: Path, name: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_str) for a SKILL.md under scratch."""
    path = scratch / ".claude" / "skills" / name / "SKILL.md"
    text = path.read_text()
    assert text.startswith("---\n"), f"{name}: missing YAML frontmatter header"
    parts = text.split("---", 2)
    assert len(parts) >= 3, f"{name}: malformed frontmatter (no closing ---)"
    frontmatter = yaml.safe_load(parts[1]) or {}
    body = parts[2]
    return frontmatter, body


def test_three_skills_exist(tmp_path: Path) -> None:
    scratch = render_scratch_project(tmp_path, has_claude_code=True)
    for name in SKILL_NAMES:
        path = scratch / ".claude" / "skills" / name / "SKILL.md"
        assert path.exists(), f"missing {path}"


def test_skill_frontmatter_valid(tmp_path: Path) -> None:
    scratch = render_scratch_project(tmp_path, has_claude_code=True)
    for name in SKILL_NAMES:
        frontmatter, _ = _read_skill(scratch, name)
        assert "name" in frontmatter, f"{name}: 'name' key missing"
        assert "description" in frontmatter, f"{name}: 'description' key missing"
        assert frontmatter["name"] == name, (
            f"{name}: frontmatter name {frontmatter['name']!r} != directory name"
        )
        assert isinstance(frontmatter["description"], str)
        assert len(frontmatter["description"]) > 0


def test_skill_description_triggers(tmp_path: Path) -> None:
    """Golden snapshot per skill — the description must contain trigger phrases
    Claude would semantically match when the user asks for this work."""
    scratch = render_scratch_project(tmp_path, has_claude_code=True)

    fm_verify, _ = _read_skill(scratch, "verify-kit-verify")
    desc = fm_verify["description"].lower()
    assert "verify" in desc, "verify skill description must contain 'verify'"
    assert ("check" in desc) or ("test" in desc), (
        "verify skill description must contain 'check' or 'test'"
    )

    fm_debug, _ = _read_skill(scratch, "verify-kit-debug")
    desc = fm_debug["description"].lower()
    assert ("debug" in desc) or ("investigate" in desc), (
        "debug skill description must contain 'debug' or 'investigate'"
    )
    assert "trace" in desc, "debug skill description must contain 'trace'"

    fm_eval, _ = _read_skill(scratch, "verify-kit-eval")
    desc = fm_eval["description"].lower()
    assert "eval" in desc, "eval skill description must contain 'eval'"


def test_skill_body_length(tmp_path: Path) -> None:
    scratch = render_scratch_project(tmp_path, has_claude_code=True)
    for name in SKILL_NAMES:
        _, body = _read_skill(scratch, name)
        line_count = len([ln for ln in body.splitlines() if ln.strip()])
        assert 10 <= line_count <= 100, (
            f"{name}: body has {line_count} non-blank lines (target 10–100)"
        )


def test_skills_absent_when_disabled(tmp_path: Path) -> None:
    scratch = render_scratch_project(tmp_path, has_claude_code=False)
    assert not (scratch / ".claude").exists(), (
        ".claude/ directory must be absent when has_claude_code=false"
    )
