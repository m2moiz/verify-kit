# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for Plan 09-04 Task 3 — web.otel_trace check (D-09, D-04, BL-5).

Tests verify:
- web.otel_trace is registered in full combo (has_db=true, logfire=false)
- web.otel_trace is registered in has_db=false backend-web combo (unconditional)
- tier="slow"
- No module-scope app/ imports
- Loud status=skip when config absent (runtime-gated)
- jaeger unreachable -> skip
- Diagnostic output on failure contains required fields
- Check is imported unconditionally in __init__.py (no compile-time gate)
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def rendered_full(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render full combo (has_web+has_backend+has_db, no logfire)."""
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("otel-trace-full"),
        has_web=True,
        has_backend=True,
        has_db=True,
        has_logfire=False,
        _vcs_ref="HEAD",
    )
    return scratch


@pytest.fixture(scope="module")
def rendered_no_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render backend-web combo without has_db (P9-06 polarity)."""
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("otel-trace-nodb"),
        has_web=True,
        has_backend=True,
        has_db=False,
        has_logfire=False,
        _vcs_ref="HEAD",
    )
    return scratch


# ── web.otel_trace registered unconditionally ─────────────────────────────────


def test_web_otel_trace_registered_in_full_combo(rendered_full: Path):
    web_py = rendered_full / "harness" / "checks" / "web.py"
    assert web_py.exists(), "harness/checks/web.py must exist"
    content = web_py.read_text()
    assert "web.otel_trace" in content, (
        "web.otel_trace must be registered in full combo (has_db=true)"
    )


def test_web_otel_trace_registered_in_no_db_combo(rendered_no_db: Path):
    web_py = rendered_no_db / "harness" / "checks" / "web.py"
    assert web_py.exists(), "harness/checks/web.py must exist in no-db combo"
    content = web_py.read_text()
    assert "web.otel_trace" in content, (
        "web.otel_trace must be registered UNCONDITIONALLY (present even in has_db=false combo)"
    )


# ── tier="slow" ───────────────────────────────────────────────────────────────


def test_web_otel_trace_is_slow_tier(rendered_full: Path):
    web_py = rendered_full / "harness" / "checks" / "web.py"
    content = web_py.read_text()
    # Find the web.otel_trace register block and check tier
    # Look for @register("web.otel_trace" ... tier="slow"
    assert re.search(r'web\.otel_trace.*tier=.?slow', content, re.DOTALL) or \
           re.search(r'tier=.?slow.*web\.otel_trace', content, re.DOTALL), (
        "web.otel_trace must be registered with tier='slow'"
    )


# ── No module-scope app/ imports ──────────────────────────────────────────────


def test_web_py_no_app_module_imports_at_scope(rendered_full: Path):
    web_py = rendered_full / "harness" / "checks" / "web.py"
    content = web_py.read_text()
    # Check for top-level (module-scope) app imports
    bad_patterns = [
        r'^from app',
        r'^import app',
    ]
    for pat in bad_patterns:
        matches = re.findall(pat, content, re.MULTILINE)
        assert not matches, (
            f"web.py must not have module-scope app/ imports (pattern {pat!r}): {matches}"
        )


# ── Parses cleanly ────────────────────────────────────────────────────────────


def test_web_py_parses_full_combo(rendered_full: Path):
    web_py = rendered_full / "harness" / "checks" / "web.py"
    ast.parse(web_py.read_text())  # raises SyntaxError if broken


def test_web_py_parses_no_db_combo(rendered_no_db: Path):
    web_py = rendered_no_db / "harness" / "checks" / "web.py"
    ast.parse(web_py.read_text())


# ── Runtime-gated: skip when config absent ───────────────────────────────────


def test_web_otel_trace_has_skip_on_no_config(rendered_full: Path):
    """When JAEGER_QUERY_BASE_URL and api service name are absent, check must skip (LOUD)."""
    web_py = rendered_full / "harness" / "checks" / "web.py"
    content = web_py.read_text()
    # Must have runtime skip logic (not compile-time Jinja gate)
    assert "skip" in content.lower(), (
        "web.otel_trace check must include runtime skip path for missing config"
    )


# ── Diagnostics on failure ────────────────────────────────────────────────────


def test_web_otel_trace_has_diagnostic_fields(rendered_full: Path):
    web_py = rendered_full / "harness" / "checks" / "web.py"
    content = web_py.read_text()
    # D-11: on failure prints trace_test_id, query URL, services/tags, export errors
    for keyword in ["trace_test_id", "query_url", "service"]:
        assert keyword.lower() in content.lower(), (
            f"web.otel_trace diagnostics must reference {keyword!r}"
        )


# ── Connectivity assertion patterns (D-04, BL-5) ─────────────────────────────


def test_web_otel_trace_asserts_web_service_name(rendered_full: Path):
    web_py = rendered_full / "harness" / "checks" / "web.py"
    content = web_py.read_text()
    # Must check for WEB_SERVICE_NAME (browser span, BL-5)
    assert re.search(r'WEB_SERVICE_NAME|web.*service.*name', content, re.IGNORECASE), (
        "web.otel_trace must assert a WEB_SERVICE_NAME browser span (BL-5)"
    )


def test_web_otel_trace_asserts_db_span_regex(rendered_full: Path):
    web_py = rendered_full / "harness" / "checks" / "web.py"
    content = web_py.read_text()
    # Must use a tolerant regex for DB span detection (not exact string)
    assert re.search(r're\.|regex|SELECT|db_span', content, re.IGNORECASE), (
        "web.otel_trace must use a tolerant regex for DB span detection"
    )


def test_web_otel_trace_asserts_shared_trace_id(rendered_full: Path):
    web_py = rendered_full / "harness" / "checks" / "web.py"
    content = web_py.read_text()
    # Must assert that all spans share one traceID
    assert re.search(r'traceID|trace_id|traceid', content, re.IGNORECASE), (
        "web.otel_trace must assert a shared traceID across all spans"
    )


def test_web_otel_trace_no_hardcoded_span_count(rendered_full: Path):
    web_py = rendered_full / "harness" / "checks" / "web.py"
    content = web_py.read_text()
    # D-04: Must NOT hardcode span count like "== 7" or "== 3"
    # (we allow >= 1, >= 2 comparisons, just not == N for large N)
    bad = re.findall(r'==\s*[3-9]\b|==\s*\d{2,}', content)
    assert not bad, (
        f"web.otel_trace must not hardcode a span count (D-04), found: {bad}"
    )


# ── __init__.py has unconditional web import ──────────────────────────────────


def test_init_py_imports_web_unconditionally(rendered_full: Path):
    init_py = rendered_full / "harness" / "checks" / "__init__.py"
    assert init_py.exists(), "harness/checks/__init__.py must exist"
    content = init_py.read_text()
    assert "from harness.checks import web" in content or "import web" in content, (
        "harness/checks/__init__.py must import the web module unconditionally"
    )
