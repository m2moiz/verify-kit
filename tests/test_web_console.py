# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.web.check_web_console (web.console — runtime error guard).

The Playwright browser path is exercised end-to-end on a rendered has_web scaffold
(throw in a useEffect → pageerror captured → web.console red). These tests cover
the hermetic parts: registration/metadata and the console.json → ErrorEnvelope
parsing logic that turns a failed probe into a clickable, structured failure.

- registry registration + spec metadata (tier=standard, category=runtime, web)
- the console.spec.ts probe ships in the rendered scaffold
- _console_error_envelope builds a structured envelope from the console.json
  artifact (message + url + dotted code), and falls back to the reporter tail
  when the artifact is missing
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def web_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("webconsole-scratch"), _vcs_ref="HEAD", has_web=True
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import web as web_mod

        yield registry, web_mod, scratch
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def test_web_console_registered(web_modules) -> None:
    registry, _, _ = web_modules
    assert "web.console" in {s.check_id for s in registry.list_checks()}


def test_web_console_spec_metadata(web_modules) -> None:
    registry, _, _ = web_modules
    spec = registry.get_check("web.console")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "runtime"
    assert spec.fixable is False
    assert spec.tool == "playwright"


def test_console_spec_ships_in_scaffold(web_modules) -> None:
    _, _, scratch = web_modules
    assert (Path(scratch) / "web" / "tests" / "e2e" / "console.spec.ts").is_file()


def test_envelope_from_console_json_artifact(web_modules, tmp_path: Path) -> None:
    """A failed probe with a console.json artifact yields a structured envelope."""
    _, web_mod, _ = web_modules
    art = tmp_path / ".verify" / "web"
    art.mkdir(parents=True)
    (art / "console.json").write_text(
        json.dumps(
            [
                {
                    "type": "pageerror",
                    "message": "TypeError: Cannot read properties of undefined",
                    "url": "http://localhost:4173/",
                    "stack": "at App (App.tsx:12)",
                }
            ]
        )
    )
    fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="1 failed", stderr="")
    env = web_mod._console_error_envelope(tmp_path, fake)
    assert env.code == "web.console.pageerror"
    assert "TypeError" in env.message
    assert env.file == "http://localhost:4173/"


def test_envelope_falls_back_to_reporter_tail(web_modules, tmp_path: Path) -> None:
    """No artifact (Playwright itself failed) → fall back to the reporter output."""
    _, web_mod, _ = web_modules
    fake = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="Error: webServer did not start", stderr=""
    )
    env = web_mod._console_error_envelope(tmp_path, fake)
    assert env.code == "web.console.failed"
    assert "webServer" in env.message
