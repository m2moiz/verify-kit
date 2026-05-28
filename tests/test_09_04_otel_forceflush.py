# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for Plan 09-04 Task 2 — otel.ts force-flush + UUID span attribute.

Tests verify:
- Rendered otel.ts exposes window.__verifyKitOtelForceFlush
- otel.ts reads trace_test_id from URL params and sets it as a span attribute
- trace-demo.spec.ts exists in the rendered project
- trace-demo.spec.ts contains the required patterns:
  trace_test_id, forceFlush, VITE_OTEL_EXPORTER_OTLP_ENDPOINT, click
- No Jinja2 syntax in otel.ts or trace-demo.spec.ts (plain .ts files)
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def rendered_full(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render full combo (has_web+has_backend+has_db, no logfire)."""
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("otel-flush-scratch"),
        has_web=True,
        has_backend=True,
        has_db=True,
        has_logfire=False,
        _vcs_ref="HEAD",
    )
    return scratch


# ── otel.ts: window.__verifyKitOtelForceFlush is exposed ─────────────────────


def test_otel_ts_exposes_force_flush(rendered_full: Path):
    otel_ts = rendered_full / "web" / "src" / "otel.ts"
    assert otel_ts.exists(), "web/src/otel.ts must exist in rendered project"
    content = otel_ts.read_text()
    assert "__verifyKitOtelForceFlush" in content, (
        "otel.ts must expose window.__verifyKitOtelForceFlush"
    )


def test_otel_ts_force_flush_is_window_assignment(rendered_full: Path):
    otel_ts = rendered_full / "web" / "src" / "otel.ts"
    content = otel_ts.read_text()
    # Must be assigned to window — allow TypeScript cast patterns like
    # (window as unknown as Record<string, unknown>).__verifyKitOtelForceFlush =
    # OR the simple window.__verifyKitOtelForceFlush =
    assert re.search(
        r'__verifyKitOtelForceFlush\s*=\s*',
        content,
    ) and "window" in content, (
        "window.__verifyKitOtelForceFlush must be assigned on window"
    )


def test_otel_ts_force_flush_awaits_provider(rendered_full: Path):
    otel_ts = rendered_full / "web" / "src" / "otel.ts"
    content = otel_ts.read_text()
    # Must call forceFlush() (provider.forceFlush or similar)
    assert "forceFlush" in content, (
        "otel.ts must call provider.forceFlush() in the window handle"
    )


# ── otel.ts: per-run UUID span attribute (BL-5) ──────────────────────────────


def test_otel_ts_sets_trace_test_id_attribute(rendered_full: Path):
    otel_ts = rendered_full / "web" / "src" / "otel.ts"
    content = otel_ts.read_text()
    # Must reference trace_test_id (to attach it as a span attribute)
    assert "trace_test_id" in content, (
        "otel.ts must read trace_test_id from URL and set it as a span attribute"
    )


def test_otel_ts_has_setAttribute_call(rendered_full: Path):
    otel_ts = rendered_full / "web" / "src" / "otel.ts"
    content = otel_ts.read_text()
    assert "setAttribute" in content, (
        "otel.ts must call setAttribute to attach the per-run UUID as a span attribute"
    )


# ── otel.ts is inert when VITE_OTEL_EXPORTER_OTLP_ENDPOINT unset ─────────────


def test_otel_ts_guard_on_endpoint_env(rendered_full: Path):
    otel_ts = rendered_full / "web" / "src" / "otel.ts"
    content = otel_ts.read_text()
    # The existing inert-by-default guard must remain
    assert "VITE_OTEL_EXPORTER_OTLP_ENDPOINT" in content, (
        "otel.ts must remain inert when VITE_OTEL_EXPORTER_OTLP_ENDPOINT is unset"
    )


def test_otel_ts_force_flush_absent_when_no_endpoint(rendered_full: Path):
    """window.__verifyKitOtelForceFlush must only be set inside the active-path block."""
    otel_ts = rendered_full / "web" / "src" / "otel.ts"
    content = otel_ts.read_text()
    # The assignment must come AFTER the endpoint guard (inside active path)
    endpoint_guard_pos = content.find("VITE_OTEL_EXPORTER_OTLP_ENDPOINT")
    flush_pos = content.find("window.__verifyKitOtelForceFlush")
    assert flush_pos > endpoint_guard_pos, (
        "window.__verifyKitOtelForceFlush must be assigned INSIDE the active-path block "
        "(after the VITE_OTEL_EXPORTER_OTLP_ENDPOINT guard)"
    )


# ── No Jinja2 in otel.ts ──────────────────────────────────────────────────────


def test_otel_ts_no_jinja2_syntax(rendered_full: Path):
    otel_ts = rendered_full / "web" / "src" / "otel.ts"
    content = otel_ts.read_text()
    assert "{%" not in content and "{{" not in content, (
        "otel.ts must be plain TypeScript — no Jinja2 syntax"
    )


# ── trace-demo.spec.ts exists in the rendered project ────────────────────────


def test_trace_demo_spec_exists(rendered_full: Path):
    spec = rendered_full / "web" / "tests" / "e2e" / "trace-demo.spec.ts"
    assert spec.exists(), "web/tests/e2e/trace-demo.spec.ts must exist in rendered project"


def test_trace_demo_spec_has_trace_test_id(rendered_full: Path):
    spec = rendered_full / "web" / "tests" / "e2e" / "trace-demo.spec.ts"
    content = spec.read_text()
    assert "trace_test_id" in content, (
        "trace-demo.spec.ts must use trace_test_id (per-run UUID)"
    )


def test_trace_demo_spec_has_force_flush(rendered_full: Path):
    spec = rendered_full / "web" / "tests" / "e2e" / "trace-demo.spec.ts"
    content = spec.read_text()
    assert re.search(r"forceFlush|__verifyKitOtelForceFlush", content), (
        "trace-demo.spec.ts must await forceFlush/__verifyKitOtelForceFlush"
    )


def test_trace_demo_spec_has_real_click(rendered_full: Path):
    spec = rendered_full / "web" / "tests" / "e2e" / "trace-demo.spec.ts"
    content = spec.read_text()
    assert "click" in content.lower(), (
        "trace-demo.spec.ts must perform a real click on the trace button"
    )


def test_trace_demo_spec_references_otel_endpoint_env(rendered_full: Path):
    spec = rendered_full / "web" / "tests" / "e2e" / "trace-demo.spec.ts"
    content = spec.read_text()
    assert "VITE_OTEL_EXPORTER_OTLP_ENDPOINT" in content, (
        "trace-demo.spec.ts must reference VITE_OTEL_EXPORTER_OTLP_ENDPOINT "
        "to indicate the SDK must be enabled for this test to work"
    )


def test_trace_demo_spec_no_jinja2(rendered_full: Path):
    spec = rendered_full / "web" / "tests" / "e2e" / "trace-demo.spec.ts"
    content = spec.read_text()
    assert "{%" not in content and "{{" not in content, (
        "trace-demo.spec.ts must be plain TypeScript — no Jinja2 syntax"
    )
