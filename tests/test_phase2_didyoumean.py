# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""Tests for harness.didyoumean (Plan 02-01, Task 3)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def didyoumean_module(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("didyoumean-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.didyoumean as d

        yield d
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def test_typo_returns_close_match(didyoumean_module) -> None:
    assert didyoumean_module.suggest("lnit", ["lint", "format"]) == ["lint"]


def test_no_close_match_returns_empty(didyoumean_module) -> None:
    assert didyoumean_module.suggest("zzz", ["lint", "format"]) == []


def test_returns_up_to_n_candidates(didyoumean_module) -> None:
    out = didyoumean_module.suggest("frmt", ["format", "frame", "frommt"], n=3)
    assert len(out) <= 3
    # "format" should be near the top because it's the closest by ratio
    assert "format" in out


def test_empty_candidates_returns_empty(didyoumean_module) -> None:
    assert didyoumean_module.suggest("anything", []) == []
