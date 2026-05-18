"""Tests for verify-kit DX convention templates and Copier env-detection extension."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


# ─── Fixtures ────────────────────────────────────────────────────────────────

COMMON_DATA = {
    "project_name": "test-project",
    "project_description": "A test project",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
}


def _render(template_root: Path, dest: Path, extra_data: dict | None = None) -> Path:
    """Run copier.run_copy with COMMON_DATA merged with extra_data."""
    import copier

    data = {**COMMON_DATA, **(extra_data or {})}
    copier.run_copy(
        str(template_root),
        str(dest),
        data=data,
        defaults=True,
        unsafe=True,
        overwrite=True,
    )
    return dest


# ─── Test 1: Conditional devcontainer ────────────────────────────────────────


def test_devcontainer_emitted_only_when_opted_in(
    template_root: Path, tmp_path: Path
) -> None:
    """devcontainer.json is created only when has_devcontainer=True."""
    # False case: no .devcontainer directory in output
    scratch_false = tmp_path / "dc-false"
    _render(template_root, scratch_false, {"has_devcontainer": False})
    assert not (scratch_false / ".devcontainer").exists(), (
        ".devcontainer/ should NOT be created when has_devcontainer=False"
    )

    # True case: .devcontainer/devcontainer.json is created and is valid JSON
    scratch_true = tmp_path / "dc-true"
    _render(template_root, scratch_true, {"has_devcontainer": True})
    dc_file = scratch_true / ".devcontainer" / "devcontainer.json"
    assert dc_file.exists(), (
        ".devcontainer/devcontainer.json should be created when has_devcontainer=True"
    )
    with dc_file.open() as f:
        content = json.load(f)  # raises if not valid JSON
    assert "mise" in str(content), "devcontainer.json should reference mise Feature"


# ─── Test 2: Biome pre-commit gate ───────────────────────────────────────────


def _biome_present(scratch: Path) -> bool:
    """Return True if any pre-commit repo entry references biomejs."""
    pre_commit = scratch / ".pre-commit-config.yaml"
    assert pre_commit.exists(), ".pre-commit-config.yaml should always be generated"
    with pre_commit.open() as f:
        data = yaml.safe_load(f)
    return any("biomejs" in (repo.get("repo") or "") for repo in data.get("repos", []))


def test_pre_commit_biome_gated_on_has_llm(
    template_root: Path, tmp_path: Path
) -> None:
    """Biome is present only when has_llm=True; backend alone does NOT enable it."""
    # Permutation 1: has_llm=False, has_backend=False → biome absent
    scratch1 = tmp_path / "no-llm-no-backend"
    _render(template_root, scratch1, {"has_llm": False, "has_backend": False})
    assert not _biome_present(scratch1), (
        "biomejs should NOT appear when has_llm=False and has_backend=False"
    )

    # Permutation 2: has_llm=False, has_backend=True → biome absent
    # (backend add-on in Phase 4 will inject its own pre-commit entry when it lands)
    scratch2 = tmp_path / "no-llm-yes-backend"
    _render(template_root, scratch2, {"has_llm": False, "has_backend": True})
    assert not _biome_present(scratch2), (
        "biomejs should NOT appear when has_llm=False, even with has_backend=True"
    )

    # Permutation 3: has_llm=True → biome present
    scratch3 = tmp_path / "yes-llm-no-backend"
    _render(template_root, scratch3, {"has_llm": True, "has_backend": False})
    assert _biome_present(scratch3), (
        "biomejs SHOULD appear when has_llm=True"
    )


# ─── Test 3: env_detect filter unit test ─────────────────────────────────────


def test_env_detect_filter_works(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """env_detect returns True/False based on home-dir filesystem state."""
    from template_extensions.env_detect import env_detect

    monkeypatch.setenv("HOME", str(tmp_path))

    # Create ~/.claude so claude_code detection triggers
    (tmp_path / ".claude").mkdir()
    assert env_detect("claude_code") is True
    assert env_detect("cursor") is False  # no ~/.cursor

    # Unknown tool returns False cleanly
    assert env_detect("nonexistent_tool_xyz") is False


# ─── Test 4: Real-render extension integration ───────────────────────────────


def test_env_detect_renders_via_copier(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    template_root: Path,
) -> None:
    """Extension loads through Copier's render pipeline; boolean types are correct."""
    import copier

    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    # Create ~/.claude so claude_code detects as True; leave cursor absent
    (fake_home / ".claude").mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    scratch = tmp_path / "scratch"
    # Do NOT pass has_claude_code in data — let the env_detect default apply
    copier.run_copy(
        str(template_root),
        str(scratch),
        data={
            "project_name": "env-test",
            "project_description": "Env detect test",
            "author_name": "Tester",
            "author_email": "tester@example.com",
            "license": "MIT",
        },
        defaults=True,
        unsafe=True,
        overwrite=True,
    )

    answers_file = scratch / ".copier-answers.yml"
    assert answers_file.exists(), ".copier-answers.yml should be generated"
    with answers_file.open() as f:
        data = yaml.safe_load(f)

    # Strict identity checks — NOT string equality
    assert data["has_claude_code"] is True, (
        f"has_claude_code should be True (bool), got {data['has_claude_code']!r}"
    )
    assert data["has_cursor"] is False, (
        f"has_cursor should be False (bool), got {data['has_cursor']!r}"
    )
    # Explicit type check to catch silent string-coercion in future Copier bumps
    assert type(data["has_claude_code"]) is bool, (
        f"has_claude_code must be bool, got {type(data['has_claude_code'])}"
    )
