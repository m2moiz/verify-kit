# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""REVIEW-CHECKLIST-driven static scans (Plan 03-05 T03).

Three scans, all against the *rendered* harness sources (not the raw
``.jinja2`` files — see "why render-first matters" below):

    Scan 1 (REVIEW-CHECKLIST §1) — no bare relative ``Path("…")``
        constructor calls in ``harness/mcp/**`` or ``harness/ralph.py``
        or ``harness/fix*.py``. Bare relatives leak the parent process's
        CWD; the fix shape is to thread ``cwd`` from the caller.

    Scan 2 (REVIEW-CHECKLIST §2) — no statements after ``return`` at any
        block level inside any function in the rendered harness sources.
        Statements after ``return`` are dead code surfacing a narrative-
        ordering bug.

    Scan 3 (REVIEW-CHECKLIST §3) — every ``subprocess.run`` /
        ``subprocess.Popen`` call inside the **Phase 3 wave-1** harness
        sources (``harness/mcp/**``, ``harness/ralph.py``,
        ``harness/fix*.py``) passes ``cwd=`` explicitly. Same failure
        mode as §1, one level deeper. Scope matches Scan 1 because the
        Phase 3 cwd-leak risk is concentrated in the wave-1 modules
        (MCP server, ralph driver, fix tool). Phase 2 sources have
        their own subprocess discipline and are out of scope; if a
        Phase 2 ``subprocess.run`` is missing ``cwd=`` it is logged as
        a deferred item, not a Phase 3 blocker.

Why render-first matters:
    Jinja-templated Python (``template/harness/runner.py.jinja2`` may
    legitimately contain ``{% if has_backend %}from .backend import …
    {% endif %}`` at module top-level) is not valid Python until
    rendered. A previous iteration tried to strip Jinja with naive
    ``.replace()`` calls; that silently mis-parses or skips real
    conditionals and produces false passes. Rendering once into a tmp
    project, then running AST against the produced ``.py`` files, gives
    a correct and stable surface to parse.

Scan scope is ``harness/**`` only — positive-example test code under
``tests/`` that itself calls ``subprocess.run(... cwd=tmp_path …)`` is
intentionally excluded.

Every ``subprocess.run`` in this file carries ``cwd=`` explicitly.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


# Module top-level dotted attribute path that resolves to a subprocess call we care about.
_SUBPROCESS_CALL_NAMES: set[str] = {
    "subprocess.run",
    "subprocess.Popen",
}


@pytest.fixture(scope="module")
def rendered_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Session-ish (module-scoped) render with the broadest flag combo.

    Rendering with every agent + backend flag flipped on maximises the
    Python surface area we get to scan (more Jinja conditionals expand
    to real code). The scans run against ``<scratch>/harness/`` only.
    """
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("p3-review-checklist"),
        has_claude_code=True,
        has_cursor=True,
        has_windsurf=True,
        has_copilot=True,
        has_continue=True,
        has_zed=True,
        has_backend=True,
    )
    return scratch


def _harness_py_files(scratch: Path) -> list[Path]:
    """All rendered .py files under harness/, excluding caches."""
    return [
        p
        for p in (scratch / "harness").rglob("*.py")
        if "__pycache__" not in p.parts
    ]


def _scan1_targets(scratch: Path) -> list[Path]:
    """Files in scope for Scan 1 — narrower than the others per the plan."""
    targets: list[Path] = []
    mcp_dir = scratch / "harness" / "mcp"
    if mcp_dir.exists():
        targets.extend(mcp_dir.glob("*.py"))
    ralph = scratch / "harness" / "ralph.py"
    if ralph.exists():
        targets.append(ralph)
    for fix in (scratch / "harness").glob("fix*.py"):
        targets.append(fix)
    return targets


# ── Scan 1: bare relative Path() ─────────────────────────────────────────────

# Match Path("foo/bar/...") where the first character of the literal is NOT
# a '/' (absolute) or a recognized template marker. We rely on AST to skip
# docstrings/comments and to scope to call arguments.
_RELATIVE_LITERAL_RE = re.compile(r"^[^/].")


def _path_call_first_arg(node: ast.Call) -> ast.Constant | None:
    """Return the first positional arg if it's a string literal and the
    call is ``Path(...)``. Else return None."""
    func = node.func
    if not isinstance(func, ast.Name) or func.id != "Path":
        return None
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first
    return None


def test_scan1_no_bare_relative_path(rendered_harness: Path) -> None:
    """Scan 1 — REVIEW-CHECKLIST §1: no bare relative Path('…') in scope."""
    violations: list[str] = []
    for src in _scan1_targets(rendered_harness):
        try:
            tree = ast.parse(src.read_text(), filename=str(src))
        except SyntaxError as exc:  # pragma: no cover — rendering should be clean
            pytest.fail(f"failed to parse rendered {src}: {exc}")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            literal = _path_call_first_arg(node)
            if literal is None:
                continue
            value = literal.value
            if not value:
                continue
            if value.startswith("/"):
                continue  # absolute path is fine
            # Bare relative literal — flag it.
            violations.append(f"{src}:{literal.lineno}: Path({value!r})")
    assert not violations, (
        "REVIEW-CHECKLIST §1 violations — bare relative Path():\n  "
        + "\n  ".join(violations)
    )


# ── Scan 2: no statements after return ───────────────────────────────────────


class _DeadAfterReturnVisitor(ast.NodeVisitor):
    """Collect (file, lineno) for any Return that is not the last statement
    in its sibling block."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.offenders: list[str] = []

    def _walk_block(self, body: list[ast.stmt]) -> None:
        for idx, stmt in enumerate(body):
            if isinstance(stmt, ast.Return) and idx != len(body) - 1:
                self.offenders.append(f"{self.filename}:{stmt.lineno}: statement after return")
            for field, value in ast.iter_fields(stmt):
                if isinstance(value, list) and value and all(
                    isinstance(v, ast.stmt) for v in value
                ):
                    self._walk_block(value)  # type: ignore[arg-type]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._walk_block(node.body)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._walk_block(node.body)
        self.generic_visit(node)


def test_scan2_no_statements_after_return(rendered_harness: Path) -> None:
    """Scan 2 — REVIEW-CHECKLIST §2: no dead code after `return`."""
    violations: list[str] = []
    for src in _harness_py_files(rendered_harness):
        try:
            tree = ast.parse(src.read_text(), filename=str(src))
        except SyntaxError as exc:  # pragma: no cover
            pytest.fail(f"failed to parse rendered {src}: {exc}")
        visitor = _DeadAfterReturnVisitor(str(src))
        visitor.visit(tree)
        violations.extend(visitor.offenders)
    assert not violations, (
        "REVIEW-CHECKLIST §2 violations — statement after return:\n  "
        + "\n  ".join(violations)
    )


# ── Scan 3: subprocess.run / Popen requires cwd= ─────────────────────────────


def _resolve_dotted(func: ast.expr) -> str | None:
    """Best-effort dotted-name resolution for ``a.b.c`` style attributes."""
    parts: list[str] = []
    cur: ast.expr | None = func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def test_scan3_subprocess_run_has_cwd(rendered_harness: Path) -> None:
    """Scan 3 — REVIEW-CHECKLIST §3: every Phase 3 subprocess.run/Popen has cwd=.

    Scoped to the same wave-1 file set as Scan 1 (MCP, ralph, fix). Phase 2
    sources are out of scope — see module docstring.
    """
    violations: list[str] = []
    for src in _scan1_targets(rendered_harness):
        try:
            tree = ast.parse(src.read_text(), filename=str(src))
        except SyntaxError as exc:  # pragma: no cover
            pytest.fail(f"failed to parse rendered {src}: {exc}")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _resolve_dotted(node.func)
            if name not in _SUBPROCESS_CALL_NAMES:
                continue
            kwarg_names = {kw.arg for kw in node.keywords if kw.arg is not None}
            if "cwd" not in kwarg_names:
                violations.append(f"{src}:{node.lineno}: {name}(...) missing cwd=")
    assert not violations, (
        "REVIEW-CHECKLIST §3 violations — subprocess call missing cwd=:\n  "
        + "\n  ".join(violations)
    )
