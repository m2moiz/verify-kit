# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Static check: no statements after `return` in any function body.

Plan 03-01 T07 — REVIEW-CHECKLIST §2 (dead code via narrative ordering).

Walks every ``template/harness/mcp/*.py.jinja2`` and ``template/harness/
ralph.py.jinja2`` source file (the files Plan 03-01 + 03-02 produce or
modify) and asserts that within every function body, every ``return``
statement is the LAST statement on its sibling list.

The jinja2 templates in scope happen to contain no jinja control flow
inside Python function bodies — the only jinja markers in these files are
top-level imports/conditionals — so they parse as plain Python with
``ast.parse``. If a future task introduces ``{% if %}`` inside a function
body, this test will start raising ``SyntaxError`` and must be updated.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]
_TARGETS = [
    _REPO_ROOT / "template" / "harness" / "mcp" / "__init__.py.jinja2",
    _REPO_ROOT / "template" / "harness" / "mcp" / "server.py.jinja2",
    _REPO_ROOT / "template" / "harness" / "mcp" / "auth.py.jinja2",
    _REPO_ROOT / "template" / "harness" / "mcp" / "tools.py.jinja2",
    _REPO_ROOT / "template" / "harness" / "mcp" / "_describe.py.jinja2",
    _REPO_ROOT / "template" / "harness" / "ralph.py.jinja2",
    _REPO_ROOT / "template" / "harness" / "fix.py.jinja2",
]


class _ReturnPositionVisitor(ast.NodeVisitor):
    """Record any `Return` node that is not the last entry in its parent body."""

    def __init__(self) -> None:
        self.offenders: list[tuple[str, int]] = []
        self._fn_stack: list[str] = []

    def _check_body(self, fn_name: str, body: list[ast.stmt]) -> None:
        for idx, stmt in enumerate(body):
            if isinstance(stmt, ast.Return) and idx != len(body) - 1:
                self.offenders.append((fn_name, stmt.lineno))

    def _walk_block(self, fn_name: str, body: list[ast.stmt]) -> None:
        # First: any Return at THIS body level must be the last statement.
        self._check_body(fn_name, body)
        # Then: recurse into compound statements' inner blocks (if/for/while/
        # try/with). Each inner block is independently checked.
        for stmt in body:
            for field, value in ast.iter_fields(stmt):
                if isinstance(value, list):
                    if value and all(isinstance(v, ast.stmt) for v in value):
                        self._walk_block(fn_name, value)  # type: ignore[arg-type]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._fn_stack.append(node.name)
        self._walk_block(self._qualname(), node.body)
        self.generic_visit(node)
        self._fn_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._fn_stack.append(node.name)
        self._walk_block(self._qualname(), node.body)
        self.generic_visit(node)
        self._fn_stack.pop()

    def _qualname(self) -> str:
        return ".".join(self._fn_stack)


@pytest.mark.parametrize("target", _TARGETS, ids=lambda p: p.name)
def test_no_statements_after_return(target: Path) -> None:
    assert target.exists(), f"target source missing: {target}"
    source = target.read_text()
    tree = ast.parse(source)
    visitor = _ReturnPositionVisitor()
    visitor.visit(tree)
    assert not visitor.offenders, (
        f"{target.name}: statements found after `return` in: "
        + ", ".join(f"{fn}@line {ln}" for fn, ln in visitor.offenders)
    )
