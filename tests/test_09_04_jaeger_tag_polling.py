# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for Plan 09-04 Task 1 — jaeger.py tag-filtered polling, F5/D-02/F-05.

Tests verify:
- poll_trace_by_tag() uses json.dumps for tags param (never hand-concat)
- Returns a structured result distinguishing:
  (a) unreachable -> TraceResult with status="unreachable"
  (b) not-found within timeout -> TraceResult with status="not_found"
  (c) found -> TraceResult with status="found" + trace data
- __all__ exports the new symbol
- No hand-concatenated tags query strings in rendered jaeger.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def jaeger_mod(tmp_path_factory: pytest.TempPathFactory):
    """Render full combo (has_web+has_backend+has_db, no logfire) and import jaeger."""
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("jaeger-tag-scratch"),
        has_web=True,
        has_backend=True,
        has_db=True,
        has_logfire=False,
        _vcs_ref="HEAD",
    )
    sys.path.insert(0, str(scratch))
    try:
        # Clear any cached modules from prior tests
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.jaeger as jaeger
        yield {"scratch": scratch, "jaeger": jaeger}
    finally:
        sys.path.remove(str(scratch))


# ── F5: poll_trace_by_tag exists and is callable ─────────────────────────────


def test_poll_trace_by_tag_callable(jaeger_mod):
    jaeger = jaeger_mod["jaeger"]
    assert callable(getattr(jaeger, "poll_trace_by_tag", None)), (
        "poll_trace_by_tag must be defined in harness.jaeger"
    )


def test_poll_trace_by_tag_in_all(jaeger_mod):
    jaeger = jaeger_mod["jaeger"]
    assert "poll_trace_by_tag" in jaeger.__all__, (
        "poll_trace_by_tag must be in jaeger.__all__"
    )


# ── F5: structured return — status="unreachable" when Jaeger is unreachable ──


def test_poll_trace_by_tag_unreachable_returns_structured(jaeger_mod):
    jaeger = jaeger_mod["jaeger"]
    import httpx

    with mock.patch.object(httpx, "get", side_effect=httpx.ConnectError("boom")):
        result = jaeger.poll_trace_by_tag("some-test-uuid", timeout=0.1)

    # Must return a structured result, not None
    assert result is not None, "poll_trace_by_tag must not return None"
    # Must have a 'status' field indicating unreachable
    status = getattr(result, "status", None) or (result.get("status") if isinstance(result, dict) else None)
    assert status == "unreachable", (
        f"Expected status='unreachable' when Jaeger is unreachable, got {status!r}"
    )


# ── F5: not found within timeout → status="not_found" ────────────────────────


def test_poll_trace_by_tag_not_found_returns_structured(jaeger_mod):
    jaeger = jaeger_mod["jaeger"]
    import httpx

    # Simulate Jaeger reachable but returns empty data (no trace for this tag)
    class EmptyResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [], "total": 0, "limit": 20, "offset": 0, "errors": None}

    with mock.patch.object(httpx, "get", return_value=EmptyResp()):
        result = jaeger.poll_trace_by_tag("no-match-uuid", timeout=0.1)

    assert result is not None, "poll_trace_by_tag must not return None"
    status = getattr(result, "status", None) or (result.get("status") if isinstance(result, dict) else None)
    assert status == "not_found", (
        f"Expected status='not_found' when trace not found within timeout, got {status!r}"
    )


# ── D-02: uses json.dumps for tags, never hand-concatenated ──────────────────


def test_poll_trace_by_tag_uses_json_dumps_for_tags(jaeger_mod):
    jaeger = jaeger_mod["jaeger"]
    import httpx

    captured_calls = []

    class FoundResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": [
                    {
                        "traceID": "abc123def",
                        "spans": [
                            {
                                "operationName": "GET /trace-demo",
                                "duration": 5000,
                                "startTime": 1000,
                                "process": {"serviceName": "test-api"},
                                "tags": [
                                    {"key": "verify_kit.trace_test_id", "value": "test-uuid-123"}
                                ],
                                "spanID": "s001",
                                "references": [],
                            }
                        ],
                        "processes": {"p1": {"serviceName": "test-api"}},
                    }
                ]
            }

    def capture_get(url, **kwargs):
        captured_calls.append({"url": url, "kwargs": kwargs})
        return FoundResp()

    with mock.patch.object(httpx, "get", side_effect=capture_get):
        result = jaeger.poll_trace_by_tag("test-uuid-123", timeout=5.0)

    assert captured_calls, "httpx.get should have been called"
    call = captured_calls[0]
    params = call["kwargs"].get("params", {})

    # tags must be in params as json.dumps (dict), not hand-concatenated in URL
    assert "tags" in params, f"params should contain 'tags' key, got params={params!r}"
    tags_value = params["tags"]
    # Must be a JSON string, not a plain string concatenation
    try:
        parsed = json.loads(tags_value)
    except (json.JSONDecodeError, TypeError):
        pytest.fail(
            f"tags param must be json.dumps(dict), got {tags_value!r} which is not valid JSON"
        )
    assert "verify_kit.trace_test_id" in parsed, (
        f"json-encoded tags must contain 'verify_kit.trace_test_id', got {parsed!r}"
    )
    assert parsed["verify_kit.trace_test_id"] == "test-uuid-123"


# ── found: returns trace data with status="found" ────────────────────────────


def test_poll_trace_by_tag_found_returns_trace(jaeger_mod):
    jaeger = jaeger_mod["jaeger"]
    import httpx

    fake_trace = {
        "traceID": "deadbeef1234",
        "spans": [
            {
                "operationName": "GET /trace-demo",
                "duration": 7000,
                "startTime": 1000,
                "process": {"serviceName": "test-api"},
                "tags": [
                    {"key": "verify_kit.trace_test_id", "value": "found-uuid"}
                ],
                "spanID": "span001",
                "references": [],
            },
            {
                "operationName": "fetch",
                "duration": 3000,
                "startTime": 500,
                "process": {"serviceName": "scratch-web"},
                "tags": [
                    {"key": "verify_kit.trace_test_id", "value": "found-uuid"}
                ],
                "spanID": "span002",
                "references": [],
            },
        ],
        "processes": {
            "p1": {"serviceName": "test-api"},
            "p2": {"serviceName": "scratch-web"},
        },
    }

    class FoundResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [fake_trace]}

    with mock.patch.object(httpx, "get", return_value=FoundResp()):
        result = jaeger.poll_trace_by_tag("found-uuid", timeout=5.0)

    assert result is not None
    status = getattr(result, "status", None) or (result.get("status") if isinstance(result, dict) else None)
    assert status == "found", f"Expected status='found', got {status!r}"

    # Result must expose enough to assert per-service spans + traceID
    # It should carry the trace data
    traces = getattr(result, "traces", None) or (result.get("traces") if isinstance(result, dict) else None)
    assert traces is not None, "result must expose 'traces' attribute when found"
    assert len(traces) >= 1


# ── F-05: rendered jaeger.py has no hand-concatenated tags query strings ──────


def test_rendered_jaeger_no_hand_concat_tags(jaeger_mod):
    scratch = jaeger_mod["scratch"]
    jaeger_src = scratch / "harness" / "jaeger.py"
    assert jaeger_src.exists(), "harness/jaeger.py must be rendered"
    content = jaeger_src.read_text()
    # Must NOT have patterns like: f"...tags={..." or "tags=" + or "?tags="
    import re
    bad_patterns = [
        r'params\s*=\s*["\'].*tags=',  # params="service=x&tags=..."
        r'f["\'].*tags=\{',             # f-string with tags= and {
        r'"tags"\s*:\s*["\'].*\+',      # "tags": "..." + something
    ]
    for pat in bad_patterns:
        matches = re.findall(pat, content)
        assert not matches, (
            f"Hand-concatenated tags found in jaeger.py (pattern {pat!r}): {matches}"
        )
    # Must have json.dumps
    assert "json.dumps" in content, "jaeger.py must use json.dumps for tags encoding"


# ── F-05: rendered jaeger.py parses cleanly ──────────────────────────────────


def test_rendered_jaeger_parses(jaeger_mod):
    import ast
    scratch = jaeger_mod["scratch"]
    jaeger_src = scratch / "harness" / "jaeger.py"
    content = jaeger_src.read_text()
    ast.parse(content)  # raises SyntaxError if broken
