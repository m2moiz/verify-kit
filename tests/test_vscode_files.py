# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""
Smoke tests for the verify-kit `.vscode/` files (plan 03-04).

Each test renders the template via the shared `scratch_project` /
`render_scratch_project` helpers, then parses the resulting JSONC file with
comments stripped and asserts structural invariants.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from tests._helpers import render_scratch_project


EXPECTED_RECOMMENDATIONS = {
    "charliermarsh.ruff",
    "ms-pyright.pyright",
    "ms-python.python",
    "ms-python.debugpy",
    "biomejs.biome",
    "vitest.explorer",
    "editorconfig.editorconfig",
    "skellock.just",
    "tamasfe.even-better-toml",
    "redhat.vscode-yaml",
}


def _load_jsonc(path: Path) -> dict:
    """Parse a JSONC file by stripping `//` line comments before json.loads."""
    text = path.read_text()
    # Strip `//` comments (not inside strings — fixtures here are simple enough)
    stripped = re.sub(r"//.*", "", text)
    return json.loads(stripped)


def test_extensions_json_has_ten_recommendations(scratch_project: Path) -> None:
    d = _load_jsonc(scratch_project / ".vscode" / "extensions.json")
    recs = d["recommendations"]
    assert isinstance(recs, list)
    assert len(recs) == 10
    assert set(recs) == EXPECTED_RECOMMENDATIONS


def test_settings_json_pytest_enabled(scratch_project: Path) -> None:
    d = _load_jsonc(scratch_project / ".vscode" / "settings.json")
    assert d["python.testing.pytestEnabled"] is True
    assert d["editor.formatOnSave"] is True
    assert d["[python]"]["editor.defaultFormatter"] == "charliermarsh.ruff"
    assert d["files.exclude"]["**/__pycache__"] is True


def test_settings_json_no_personal_prefs(scratch_project: Path) -> None:
    text = (scratch_project / ".vscode" / "settings.json").read_text()
    forbidden = re.compile(r"workbench\.colorTheme|editor\.fontFamily|editor\.fontSize")
    assert forbidden.search(text) is None, "Personal preference key leaked into project settings"


def test_tasks_json_verify_is_default_build(scratch_project: Path) -> None:
    d = _load_jsonc(scratch_project / ".vscode" / "tasks.json")
    tasks = d["tasks"]
    labels = [t["label"] for t in tasks]
    for required in ("verify", "verify --quick", "lint", "typecheck"):
        assert required in labels, f"Missing task: {required}"
    default_build = [
        t for t in tasks
        if t.get("group", {}).get("kind") == "build" and t.get("group", {}).get("isDefault") is True
    ]
    assert len(default_build) == 1
    assert default_build[0]["label"] == "verify"
    assert default_build[0]["command"] == "just verify"

    # Custom matcher names registered at top level
    matcher_names = {m["name"] for m in d["problemMatchers"]}
    assert {"verify-kit-ruff", "verify-kit-pyright", "verify-kit-biome"} <= matcher_names


def test_launch_json_has_backend_true(tmp_path: Path) -> None:
    scratch = render_scratch_project(tmp_path, has_backend=True)
    d = _load_jsonc(scratch / ".vscode" / "launch.json")
    config_names = [c["name"] for c in d["configurations"]]
    assert config_names == ["Pytest: Current File", "FastAPI: uvicorn"]
    assert "compounds" in d
    assert len(d["compounds"]) == 1
    assert d["compounds"][0]["configurations"] == ["Pytest: Current File", "FastAPI: uvicorn"]
    pytest_cfg = d["configurations"][0]
    assert pytest_cfg["module"] == "pytest"
    assert pytest_cfg["args"][0] == "${file}"


def test_launch_json_has_backend_false(tmp_path: Path) -> None:
    scratch = render_scratch_project(tmp_path, has_backend=False)
    d = _load_jsonc(scratch / ".vscode" / "launch.json")
    config_names = [c["name"] for c in d["configurations"]]
    assert config_names == ["Pytest: Current File"]
    assert "compounds" not in d


def test_readme_documents_other_editors(scratch_project: Path) -> None:
    readme = (scratch_project / "README.md").read_text()
    assert "## Other editors (JetBrains, Zed, Neovim)" in readme
    for editor in ("JetBrains", "Zed", "Neovim"):
        assert editor in readme, f"README missing editor: {editor}"
