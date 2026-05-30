# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tier C — strict_mode toggle polarity (outer test).

The `strict_mode` copier prompt (default false) flips pyright's
`typeCheckingMode` in the rendered project's pyproject.toml between
"standard" (off) and "strict" (on). This test asserts both polarities
render the correct line, and that the preset-schema invariant still
holds (every committed preset must cover the new copier.yml key, or the
preset-schema-check CI workflow fails on interactive input).

_vcs_ref="HEAD" is required so the render picks up the strict_mode prompt
added after the v0.1.0 tag (same rationale as the Phase 7 web tests).

NOTE: strict_mode=True is opt-in by design. The default (standard) render
stays green; the strict render is NOT expected to pass `just verify` on
the template's own harness/+app/ code (pyright strict flags many missing
annotations). This test only asserts the toggle is wired correctly — it
does not run pyright.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests._helpers import render_scratch_project

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COPIER_YML = _REPO_ROOT / "copier.yml"
_PRESETS_DIR = _REPO_ROOT / "presets"

_BASE: dict[str, object] = {
    "project_name": "StrictPolarity",
    "project_description": "strict_mode polarity test",
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


@pytest.mark.parametrize(
    "strict_mode,expected_line",
    [
        (False, 'typeCheckingMode = "standard"'),
        (True, 'typeCheckingMode = "strict"'),
    ],
)
def test_strict_mode_toggles_pyright(
    tmp_path: Path,
    strict_mode: bool,
    expected_line: str,
) -> None:
    """strict_mode flips the rendered [tool.pyright] typeCheckingMode line."""
    scratch = render_scratch_project(
        tmp_path,
        _vcs_ref="HEAD",
        **{**_BASE, "strict_mode": strict_mode},  # type: ignore[arg-type]
    )
    pyproject = (scratch / "pyproject.toml").read_text()

    assert expected_line in pyproject, (
        f"expected {expected_line!r} in rendered pyproject.toml "
        f"when strict_mode={strict_mode}"
    )
    # The opposite polarity must NOT leak.
    wrong_mode = "standard" if strict_mode else "strict"
    assert f'typeCheckingMode = "{wrong_mode}"' not in pyproject, (
        f'typeCheckingMode = "{wrong_mode}" leaked when strict_mode={strict_mode}'
    )


def test_strict_mode_covered_by_every_preset() -> None:
    """Every committed preset must declare strict_mode (preset-schema invariant).

    Mirrors the coverage assertion in .github/workflows/preset-schema-check.yml:
    a new non-computed copier.yml prompt key that any committed preset omits
    would make the CI self-test prompt for interactive input and fail.
    """
    assert "strict_mode" in yaml.safe_load(_COPIER_YML.read_text()), (
        "strict_mode prompt missing from copier.yml"
    )

    preset_files = [
        p
        for p in sorted(_PRESETS_DIR.glob("*.yml"))
        if not p.name.endswith(".local.yml")
    ]
    assert preset_files, "no committed presets found under presets/"

    for preset_path in preset_files:
        preset_data = yaml.safe_load(preset_path.read_text())
        assert "strict_mode" in preset_data, (
            f"{preset_path.name} is missing strict_mode — preset-schema-check would fail"
        )
