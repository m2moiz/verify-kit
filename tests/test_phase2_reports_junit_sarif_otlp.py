# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.reports.{junit,sarif,otlp} (Plan 02-05, Task 3).

Covers:
- junit emits well-formed XML round-trippable through ET.fromstring
- junit <testsuites> time attr derives from report.summary.duration_ms / 1000
- sarif top-level $schema and tool.driver.name correct
- sarif results contain only non-pass checks
- otlp gracefully degrades when OTEL_EXPORTER_OTLP_ENDPOINT is unset
"""
from __future__ import annotations

import io
import json
import sys
import xml.etree.ElementTree as ET

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def emit_modules(tmp_path_factory: pytest.TempPathFactory, monkeypatch_module):
    # Ensure OTel is disabled at import time for predictable otlp test
    monkeypatch_module.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    scratch = render_scratch_project(tmp_path_factory.mktemp("reports-jso-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.reports.junit as junit
        import harness.reports.sarif as sarif
        import harness.reports.otlp as otlp
        import harness.registry as registry
        import harness.models as models

        # Pre-register a couple of checks so SARIF tool.driver.rules is non-empty
        registry._checks.clear()

        @registry.register("lint.ruff", category="lint", description="ruff lint")
        def _ruff(cwd):
            return models.CheckResult(check_id="lint.ruff", status="pass")

        @registry.register("lint.eslint", category="lint", description="eslint lint")
        def _eslint(cwd):
            return models.CheckResult(check_id="lint.eslint", status="pass")

        yield junit, sarif, otlp, models
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest's MonkeyPatch is function-scoped)."""
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def _mixed_report(models):
    checks = [
        models.CheckResult(
            check_id="lint.ruff",
            status="pass",
            duration_ms=10,
        ),
        models.CheckResult(
            check_id="lint.eslint",
            status="fail",
            message="3 issues",
            duration_ms=22,
            error=models.ErrorEnvelope(
                code="lint.eslint.E1",
                message="bad code",
                hint="run --fix",
                docs_url="https://example.com/E1",
            ),
        ),
        models.CheckResult(
            check_id="format.biome",
            status="skip",
            message="no JS files",
            duration_ms=1,
        ),
    ]
    return models.VerifyReport.from_checks(checks, total_duration_ms=33)


def test_junit_round_trips(emit_modules) -> None:
    junit, _sarif, _otlp, models = emit_modules
    report = _mixed_report(models)
    buf = io.StringIO()
    junit.emit(report, buf)
    text = buf.getvalue()
    assert text.startswith("<?xml")
    root = ET.fromstring(text[text.index("<testsuites") :])
    assert root.tag == "testsuites"
    assert root.attrib["tests"] == "3"
    assert root.attrib["failures"] == "1"
    assert root.attrib["skipped"] == "1"


def test_junit_time_from_summary_duration(emit_modules) -> None:
    junit, _sarif, _otlp, models = emit_modules
    report = _mixed_report(models)
    buf = io.StringIO()
    junit.emit(report, buf)
    text = buf.getvalue()
    root = ET.fromstring(text[text.index("<testsuites") :])
    # 33ms / 1000 = 0.033
    assert root.attrib["time"] == "0.033"


def test_junit_failure_element_has_type_and_message(emit_modules) -> None:
    junit, _sarif, _otlp, models = emit_modules
    report = _mixed_report(models)
    buf = io.StringIO()
    junit.emit(report, buf)
    text = buf.getvalue()
    root = ET.fromstring(text[text.index("<testsuites") :])
    failures = root.findall(".//failure")
    assert len(failures) == 1
    assert failures[0].attrib["type"] == "lint.eslint.E1"
    assert failures[0].attrib["message"] == "bad code"


def test_sarif_schema_and_driver(emit_modules) -> None:
    _junit, sarif, _otlp, models = emit_modules
    report = _mixed_report(models)
    buf = io.StringIO()
    sarif.emit(report, buf)
    data = json.loads(buf.getvalue())
    assert data["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
    assert data["version"] == "2.1.0"
    assert data["runs"][0]["tool"]["driver"]["name"] == "verify-kit"
    rule_ids = {r["id"] for r in data["runs"][0]["tool"]["driver"]["rules"]}
    assert "lint.ruff" in rule_ids
    assert "lint.eslint" in rule_ids


def test_sarif_results_omit_passes(emit_modules) -> None:
    _junit, sarif, _otlp, models = emit_modules
    report = _mixed_report(models)
    buf = io.StringIO()
    sarif.emit(report, buf)
    data = json.loads(buf.getvalue())
    results = data["runs"][0]["results"]
    rule_ids = [r["ruleId"] for r in results]
    assert "lint.ruff" not in rule_ids  # pass excluded
    assert "lint.eslint" in rule_ids  # fail included
    assert "format.biome" in rule_ids  # skip included as level=note
    # levels
    levels = {r["ruleId"]: r["level"] for r in results}
    assert levels["lint.eslint"] == "error"
    assert levels["format.biome"] == "note"


def test_otlp_disabled_writes_warning(emit_modules) -> None:
    _junit, _sarif, otlp, models = emit_modules
    report = _mixed_report(models)
    buf = io.StringIO()
    otlp.emit(report, buf)
    text = buf.getvalue()
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in text
    assert "spans were not exported" in text
