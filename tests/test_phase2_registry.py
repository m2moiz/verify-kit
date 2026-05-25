# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.registry (Plan 02-01, Task 2)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture
def harness_registry(tmp_path: Path):
    scratch = render_scratch_project(tmp_path)
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.registry as reg

        reg._checks.clear()
        yield reg
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def test_register_returns_original_function(harness_registry) -> None:
    reg = harness_registry

    @reg.register("foo.bar", tier="quick", category="test", inputs=[".x"])
    def my_check():
        return "value"

    assert my_check() == "value"
    spec = reg.get_check("foo.bar")
    assert spec is not None
    assert spec.check_id == "foo.bar"
    assert spec.tier == "quick"
    assert spec.category == "test"
    assert spec.inputs == [".x"]
    assert spec.fn is my_check


def test_list_checks_preserves_registration_order(harness_registry) -> None:
    reg = harness_registry

    @reg.register("a.one")
    def a():
        pass

    @reg.register("b.two")
    def b():
        pass

    @reg.register("c.three")
    def c():
        pass

    ids = [s.check_id for s in reg.list_checks()]
    assert ids == ["a.one", "b.two", "c.three"]


def test_reregistration_overwrites(harness_registry) -> None:
    reg = harness_registry

    @reg.register("dup")
    def first():
        return 1

    @reg.register("dup", category="overwritten")
    def second():
        return 2

    spec = reg.get_check("dup")
    assert spec is not None
    assert spec.category == "overwritten"
    assert spec.fn is second
    # No duplicate entries in list.
    assert sum(1 for s in reg.list_checks() if s.check_id == "dup") == 1


def test_get_check_returns_none_on_miss(harness_registry) -> None:
    assert harness_registry.get_check("nope.nope") is None


def test_checks_module_dict_is_public_for_reset(harness_registry) -> None:
    reg = harness_registry

    @reg.register("x")
    def x():
        pass

    assert "x" in reg._checks
    reg._checks.clear()
    assert reg.get_check("x") is None
