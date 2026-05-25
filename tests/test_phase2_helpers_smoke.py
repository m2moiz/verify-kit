# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Smoke tests for the Phase 2 shared test helpers (Plan 02-01, Task 0)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


def test_render_scratch_project_produces_pyproject_and_harness(tmp_path: Path) -> None:
    scratch = render_scratch_project(tmp_path)
    assert scratch.is_dir()
    assert (scratch / "pyproject.toml").is_file()
    assert (scratch / "harness").is_dir()


def test_scratch_project_fixture_works(scratch_project: Path) -> None:
    assert (scratch_project / "pyproject.toml").is_file()


@pytest.mark.slow
def test_install_scratch_harness_exits_zero(tmp_path: Path) -> None:
    if not os.environ.get("RUN_SLOW_TESTS"):
        pytest.skip("RUN_SLOW_TESTS not set")
    from tests._helpers import render_and_install

    scratch = render_and_install(tmp_path)
    assert (scratch / "pyproject.toml").is_file()
