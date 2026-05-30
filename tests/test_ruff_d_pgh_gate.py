# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tier B — ruff D (docstring) + PGH (ban blanket ignore) strictness gate.

Decision 1 (operator, 2026-05-30): full pydocstyle-google ``D`` in the default
``just verify`` gate (presence + content), plus ``PGH`` so the typed-ignore
escape hatch must carry a rule code, plus ``ASYNC``. ``S``/``SIM``/``RET`` are a
separate ruleset-expansion follow-up. This module asserts the rendered project's
``[tool.ruff.lint]`` config carries the gate, and that ``tests/`` are exempt from
``D`` (tests self-document via their names).

The real planted-failure forcing function — render a scaffold, plant an
undocumented public function + a blanket ``# type: ignore``, run ruff, and assert
``D103`` + ``PGH003`` fire while a scoped ``# type: ignore[code]`` does NOT — is
exercised by the orchestrator against a rendered scaffold (same convention as
``test_web_typecheck`` / ``test_strict_mode``). These tests guard the config
contract hermetically in CI without a slow render+ruff run.

NOTE: pydocstyle exempts private modules (``_name.py``), so ``D`` enforces
"public-API only" by construction — which matches the intended scope.

``_vcs_ref="HEAD"`` is required: the D/PGH/ASYNC select was added after the
v0.1.0 tag (same rationale as the strict_mode / web tests).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from tests._helpers import render_scratch_project

_BASE: dict[str, object] = {
    "project_name": "RuffGate",
    "project_description": "ruff D/PGH gate config test",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
    "has_backend": False,
    "has_db": False,
    "has_llm": False,
    "has_web": False,
    "has_claude_code": False,
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    "has_devcontainer": False,
    "llm_backend": "none",
}


def _render_ruff_lint(tmp_path: Path, **overrides: object) -> dict:
    scratch = render_scratch_project(
        tmp_path,
        _vcs_ref="HEAD",
        **{**_BASE, **overrides},  # type: ignore[arg-type]
    )
    data = tomllib.loads((scratch / "pyproject.toml").read_text())
    return data["tool"]["ruff"]["lint"]


def test_ruff_select_carries_d_pgh_async(tmp_path: Path) -> None:
    """The default verify gate selects D (docstrings), PGH (ignore-ban), ASYNC."""
    lint = _render_ruff_lint(tmp_path)
    select = lint["select"]
    for code in ("D", "PGH", "ASYNC"):
        assert code in select, f"ruff select must carry {code!r}; got {select!r}"


def test_ruff_pydocstyle_convention_is_google(tmp_path: Path) -> None:
    """Google convention disables the conflicting D203/D211 + D212/D213 pairs."""
    lint = _render_ruff_lint(tmp_path)
    assert lint["pydocstyle"]["convention"] == "google"


def test_tests_dir_is_exempt_from_d(tmp_path: Path) -> None:
    """tests/* must ignore D — tests self-document via descriptive names."""
    lint = _render_ruff_lint(tmp_path)
    assert "D" in lint["per-file-ignores"]["tests/*"], (
        "tests/* per-file-ignores must include 'D'"
    )


def test_alembic_migrations_exempt_from_d_when_db(tmp_path: Path) -> None:
    """has_db: auto-generated Alembic migrations are exempt from D."""
    lint = _render_ruff_lint(tmp_path, has_backend=True, has_db=True)
    pfi = lint["per-file-ignores"]
    assert "D" in pfi["alembic/versions/*"], "alembic migrations must ignore D"
    assert "D" in pfi["alembic/env.py"], "alembic env.py must ignore D"
