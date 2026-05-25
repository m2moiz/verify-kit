# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.reports.pretty (Plan 02-05, Task 1).

Covers:
- emit on a passing report produces "1/1 passed" line
- emit on a failing report with error envelope produces multi-line miette block
- emit with NO_COLOR=1 has no ANSI sequences
- emit with CI=1 has no spinner
- run_with_spinner without TTY returns results in same order as input specs
- FORMATTERS dict exposes all 6 names
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@pytest.fixture(scope="module")
def pretty_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("reports-pretty-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.reports as reports
        import harness.reports.pretty as pretty
        import harness.models as models

        yield reports, pretty, models
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _make_report(models, *, with_failure: bool = False, with_cached: bool = False):
    checks = [
        models.CheckResult(
            check_id="lint.ruff",
            status="pass",
            message="no issues",
            duration_ms=12,
            cached=with_cached,
        )
    ]
    if with_failure:
        checks.append(
            models.CheckResult(
                check_id="lint.eslint",
                status="fail",
                message="3 issues",
                duration_ms=20,
                error=models.ErrorEnvelope(
                    code="lint.eslint.E501",
                    message="line too long",
                    hint="run --fix",
                    fix_command="just fix",
                    docs_url="https://example.com/E501",
                ),
            )
        )
    return models.VerifyReport.from_checks(checks, total_duration_ms=32)


def test_formatters_dict_complete(pretty_modules) -> None:
    reports, _pretty, _models = pretty_modules
    assert hasattr(reports, "FORMATTERS")
    assert set(reports.FORMATTERS.keys()) == {
        "pretty",
        "json",
        "jsonl",
        "junit",
        "sarif",
        "otlp",
    }
    for fn in reports.FORMATTERS.values():
        assert callable(fn)


def test_emit_pass_summary_line(pretty_modules, monkeypatch) -> None:
    _reports, pretty, models = pretty_modules
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("CI", raising=False)
    report = _make_report(models)
    buf = io.StringIO()
    pretty.emit(report, buf)
    text = buf.getvalue()
    assert "1/1 passed" in text
    assert "lint.ruff" in text


def test_emit_failure_renders_miette_block(pretty_modules, monkeypatch) -> None:
    _reports, pretty, models = pretty_modules
    monkeypatch.setenv("NO_COLOR", "1")
    report = _make_report(models, with_failure=True)
    buf = io.StringIO()
    pretty.emit(report, buf)
    text = buf.getvalue()
    # header + hint + fix + docs at minimum
    assert "error[lint.eslint.E501]" in text
    assert "line too long" in text
    assert "hint" in text and "run --fix" in text
    assert "fix" in text and "just fix" in text
    assert "docs" in text and "https://example.com/E501" in text


def test_emit_no_color_strips_ansi(pretty_modules, monkeypatch) -> None:
    _reports, pretty, models = pretty_modules
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("CI", raising=False)
    report = _make_report(models, with_failure=True)
    buf = io.StringIO()
    pretty.emit(report, buf)
    text = buf.getvalue()
    assert not _ANSI.search(text), f"ANSI sequence found in output: {text!r}"


def test_emit_cached_indicator(pretty_modules, monkeypatch) -> None:
    _reports, pretty, models = pretty_modules
    monkeypatch.setenv("NO_COLOR", "1")
    report = _make_report(models, with_cached=True)
    buf = io.StringIO()
    pretty.emit(report, buf)
    text = buf.getvalue()
    assert "cached" in text


def test_run_with_spinner_no_tty_preserves_order(pretty_modules, monkeypatch) -> None:
    _reports, pretty, models = pretty_modules
    # Force CI=1 so spinner-gate is OFF
    monkeypatch.setenv("CI", "1")
    specs = ["a", "b", "c"]

    def _runner(spec):
        return models.CheckResult(check_id=spec, status="pass")

    out = pretty.run_with_spinner(specs, _runner)
    assert [r.check_id for r in out] == ["a", "b", "c"]
