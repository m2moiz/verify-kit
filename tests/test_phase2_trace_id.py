# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.trace_id (Plan 02-01, Task 3).

contextvars-based; ASGI middleware lives in Phase 4 (FastAPI addon).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture
def trace_id_module(tmp_path: Path):
    scratch = render_scratch_project(tmp_path)
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.trace_id as t

        yield t
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def test_default_is_empty_string(trace_id_module) -> None:
    assert trace_id_module.get_trace_id() == ""


def test_set_and_get(trace_id_module) -> None:
    t = trace_id_module
    token = t.set_trace_id("req-abc")
    try:
        assert t.get_trace_id() == "req-abc"
    finally:
        t.reset_trace_id(token)


def test_reset_restores_prior_value(trace_id_module) -> None:
    t = trace_id_module
    token1 = t.set_trace_id("first")
    try:
        token2 = t.set_trace_id("second")
        assert t.get_trace_id() == "second"
        t.reset_trace_id(token2)
        assert t.get_trace_id() == "first"
    finally:
        t.reset_trace_id(token1)
    assert t.get_trace_id() == ""


def test_trace_id_scope_context_manager(trace_id_module) -> None:
    t = trace_id_module
    assert t.get_trace_id() == ""
    with t.trace_id_scope("scoped"):
        assert t.get_trace_id() == "scoped"
    assert t.get_trace_id() == ""


def test_thread_isolation(trace_id_module) -> None:
    """Different threads have independent contextvar values (default behaviour)."""
    t = trace_id_module
    t.set_trace_id("main-thread")
    observed: list[str] = []

    def worker():
        observed.append(t.get_trace_id())
        t.set_trace_id("worker-thread")
        observed.append(t.get_trace_id())

    th = threading.Thread(target=worker)
    th.start()
    th.join()
    # Worker thread sees default "" (contextvars do not propagate across raw threads).
    assert observed == ["", "worker-thread"]
    # Main thread value unaffected.
    assert t.get_trace_id() == "main-thread"
