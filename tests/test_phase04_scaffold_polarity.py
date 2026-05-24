"""Phase 4 Plan 04-01 — scaffold polarity tests.

Enforces the two-guard contract for add-on path gating:
  1. Primary gate: ``_exclude`` block in ``copier.yml``.
  2. Secondary gate: Jinja path conditionals (two permitted shapes only).

Three test functions cover all required polarities and anti-patterns:

  test_has_backend_true_produces_app_tree
      has_backend=True → app/ dir + .gitkeep AND tests/backend/.gitkeep exist.

  test_has_backend_false_produces_zero_backend_files
      has_backend=False → NONE of app/, alembic/, tests/backend/, Dockerfile,
      docker-compose.yml, .dockerignore appear anywhere in the scaffold tree.

  test_has_backend_false_has_no_empty_segment_leaks
      has_backend=False → no file has an empty name, no file ends only in
      ``.jinja2``, no top-level ``backend/`` directory exists, and every
      root-level entry is in the universal-allowlist derived from the
      has_backend=True scaffold minus the backend-specific names.

REVIEW-CHECKLIST compliance:
  §1 cwd leaks: all copier invocations use ``tmp_path`` fixture directly,
     never process cwd. No subprocess calls in this file; the copier Python
     API is used throughout.
  §3 contract drift: this file is the authoritative polarity gate that all
     Phase 4 plans reference. The ``_BACKEND_NAMES`` set below is the
     canonical definition — downstream plans do NOT redefine it.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project

# ── Constants ─────────────────────────────────────────────────────────────────

# Names (at any path depth) that MUST NOT appear when has_backend=False.
# Any path segment matching one of these is a contract violation.
_BACKEND_NAMES: frozenset[str] = frozenset(
    {
        "app",
        "alembic",
        "backend",  # catches orphan top-level backend/ from empty-segment leak
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        "alembic.ini",
    }
)

# Root-level names that are permitted in any scaffold regardless of has_backend.
# Derived empirically from the universal template output and updated whenever
# the universal scaffold adds a new root-level entry.
_UNIVERSAL_ROOT_NAMES: frozenset[str] = frozenset(
    {
        ".copier-answers.yml",
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        ".github",
        ".mise.toml",
        ".pre-commit-config.yaml",
        ".vscode",
        "AGENTS.md",
        "harness",
        "justfile",
        "LICENSE",
        "Makefile",
        "pyproject.toml",
        "README.md",
        "scripts",
        "tests",
        # Optional agent-integration dirs (may or may not be present depending
        # on agent flags — they are not backend-specific so they are allowed).
        ".claude",
        ".continue",
        ".cursor",
        ".devcontainer",
        ".windsurf",
        ".zed",
        # Agent-specific files at root
        "CLAUDE.md",
    }
)

# ── Base data shared across all polarity renders ───────────────────────────────

_BASE_DATA: dict[str, object] = {
    "project_name": "PolarityTest",
    "project_description": "scaffold polarity test",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
    "has_claude_code": False,
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    "has_llm": False,
    "has_devcontainer": False,
    "llm_backend": "none",
}


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_has_backend_true_produces_app_tree(tmp_path: Path) -> None:
    """has_backend=True renders app/ with .gitkeep AND tests/backend/.gitkeep.

    The ``app`` directory is gated by the top-level unique-dir shape:
      ``template/{% if has_backend %}app{% endif %}/.gitkeep``

    The ``tests/backend`` directory is gated by the filename-level shape:
      ``template/tests/backend/{% if has_backend %}.gitkeep{% endif %}``

    Both guards (``_exclude`` block + Jinja path conditional) must agree.
    """
    scratch = render_scratch_project(
        tmp_path,
        **{**_BASE_DATA, "has_backend": True, "has_db": True, "has_logfire": False, "has_fastapi_mcp": False},  # type: ignore[arg-type]
    )

    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    app_dir = scratch / "app"
    assert app_dir.is_dir(), (
        "app/ directory must exist when has_backend=True "
        "(top-level unique-dir gate failed)"
    )
    app_gitkeep = app_dir / ".gitkeep"
    assert app_gitkeep.exists(), (
        "app/.gitkeep must exist when has_backend=True; "
        f"app/ contents: {list(app_dir.iterdir())}"
    )

    backend_dir = scratch / "tests" / "backend"
    assert backend_dir.is_dir(), (
        "tests/backend/ must exist when has_backend=True "
        "(filename-level gate failed)"
    )
    backend_gitkeep = backend_dir / ".gitkeep"
    assert backend_gitkeep.exists(), (
        "tests/backend/.gitkeep must exist when has_backend=True; "
        f"backend/ contents: {list(backend_dir.iterdir())}"
    )


def test_has_backend_true_has_db_false_no_db_files_in_scaffold(tmp_path: Path) -> None:
    """has_backend=True, has_db=False renders backend WITHOUT db layer.

    Bead verify-kit-plk: polarity matrix had cells (T,T) and (F,F); the
    (T, F) cell was missing. This test asserts that turning the DB layer
    OFF while keeping backend ON produces a clean FastAPI scaffold with
    NO sqlalchemy/alembic artifacts.

    Note: copier.yml's ``has_db`` is gated by ``when: \"{{ has_backend }}\"``,
    so it only prompts when has_backend=true and defaults to true there.
    We override explicitly with has_db=False to exercise the (T, F) cell.
    """
    scratch = render_scratch_project(
        tmp_path,
        **{**_BASE_DATA, "has_backend": True, "has_db": False, "has_logfire": False, "has_fastapi_mcp": False},  # type: ignore[arg-type]
    )

    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    # ── (a) Backend IS present ──
    app_main = scratch / "app" / "main.py"
    assert app_main.exists(), (
        "app/main.py must exist when has_backend=True (regardless of has_db)"
    )

    # ── (b) DB-specific files are ABSENT ──
    db_files = [
        scratch / "app" / "db.py",
        scratch / "app" / "schema.py",
        scratch / "alembic",
        scratch / "alembic.ini",
    ]
    leaked_db: list[str] = [str(p.relative_to(scratch)) for p in db_files if p.exists()]
    assert not leaked_db, (
        "DB-specific files leaked into has_backend=True, has_db=False scaffold:\n"
        + "\n".join(f"  {p}" for p in sorted(leaked_db))
    )

    # ── (c) app/settings.py does NOT contain DATABASE_URL ──
    settings_py = scratch / "app" / "settings.py"
    if settings_py.exists():
        settings_text = settings_py.read_text()
        assert "DATABASE_URL" not in settings_text, (
            "app/settings.py contains DATABASE_URL field when has_db=False — "
            "the Jinja gate around the DATABASE_URL field is missing or wrong."
        )

    # ── (d) pyproject.toml does NOT pull in DB deps ──
    pyproject = scratch / "pyproject.toml"
    pyproject_text = pyproject.read_text()
    forbidden_deps = ["sqlalchemy", "asyncpg", "alembic"]
    leaked_deps = [d for d in forbidden_deps if d in pyproject_text.lower()]
    assert not leaked_deps, (
        f"pyproject.toml lists DB-only deps when has_db=False: {leaked_deps}\n"
        f"Relevant pyproject content:\n{pyproject_text}"
    )


def test_has_backend_false_produces_zero_backend_files(tmp_path: Path) -> None:
    """has_backend=False renders ZERO backend-specific files or directories.

    Walks the entire scaffold tree via ``rglob('*')`` — not just the root —
    to catch accidental leaks from nested Jinja gates.  Any path whose
    components contain a name in ``_BACKEND_NAMES`` is a contract violation.
    """
    scratch = render_scratch_project(
        tmp_path,
        **{**_BASE_DATA, "has_backend": False, "has_db": False, "has_logfire": False, "has_fastapi_mcp": False},  # type: ignore[arg-type]
    )

    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    leaked: list[str] = []
    for node in scratch.rglob("*"):
        rel = node.relative_to(scratch)
        for part in rel.parts:
            if part in _BACKEND_NAMES:
                leaked.append(str(rel))
                break

    assert not leaked, (
        "Backend files leaked into has_backend=False scaffold:\n"
        + "\n".join(f"  {p}" for p in sorted(leaked))
        + "\n\nCheck the _exclude block in copier.yml and Jinja path gates."
    )


def test_has_backend_false_has_no_empty_segment_leaks(tmp_path: Path) -> None:
    """has_backend=False scaffold has no empty-segment or .jinja2-only names.

    Asserts three sub-contracts:

    (a) No file or directory in the scaffold has an empty name or a name
        that consists solely of the ``.jinja2`` suffix (which would indicate
        a Jinja conditional rendered to an empty string as the filename stem).

    (b) No top-level ``backend/`` directory exists (would indicate an
        empty-segment leak from the BANNED pattern
        ``template/{% if has_backend %}tests{% endif %}/backend/``).

    (c) Every root-level entry is in the universal allowlist
        ``_UNIVERSAL_ROOT_NAMES``. Any unexpected entry fails loudly so
        future plans cannot silently add new root-level files without
        updating the allowlist.
    """
    scratch = render_scratch_project(
        tmp_path,
        **{**_BASE_DATA, "has_backend": False, "has_db": False, "has_logfire": False, "has_fastapi_mcp": False},  # type: ignore[arg-type]
    )

    assert scratch.is_dir(), f"scaffold root missing: {scratch}"

    # ── (a) No empty or .jinja2-only names anywhere in the tree ────────────
    empty_or_jinja2: list[str] = []
    for node in scratch.rglob("*"):
        name = node.name
        if name == "" or name == ".jinja2" or (name.endswith(".jinja2") and not name[: -len(".jinja2")]):
            empty_or_jinja2.append(str(node.relative_to(scratch)))

    assert not empty_or_jinja2, (
        "Empty-named or .jinja2-only files found — Jinja conditional rendered "
        "an empty filename stem:\n"
        + "\n".join(f"  {p}" for p in sorted(empty_or_jinja2))
    )

    # ── (b) No top-level backend/ directory ────────────────────────────────
    orphan_backend = scratch / "backend"
    assert not orphan_backend.exists(), (
        "Orphan top-level backend/ directory found. This indicates an "
        "empty-segment leak from the BANNED pattern "
        "template/{% if has_backend %}tests{% endif %}/backend/ — "
        "the conditional rendered empty and 'backend' became a new root dir."
    )

    # ── (c) Root entries are a subset of the universal allowlist ───────────
    root_entries = {node.name for node in scratch.iterdir()}
    unexpected = root_entries - _UNIVERSAL_ROOT_NAMES
    assert not unexpected, (
        "Unexpected root-level entries in has_backend=False scaffold:\n"
        + "\n".join(f"  {name!r}" for name in sorted(unexpected))
        + "\n\nIf these are intentional, add them to _UNIVERSAL_ROOT_NAMES "
        "in tests/test_phase04_scaffold_polarity.py."
    )
