# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""Tests for harness.models (Plan 02-01, Task 1).

These tests import from the rendered scratch project, not from the template
source directly — `harness/` only exists as `template/harness/*.py.jinja2`
files in the repo. We render once per session and add the scratch path to
sys.path so the Pydantic models can be imported as real Python modules.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def harness_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("models-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        # Force fresh import (in case prior test imported a stale harness.*).
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.models as models

        yield models
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def test_exit_code_constants(harness_modules) -> None:
    m = harness_modules
    assert m.EXIT_OK == 0
    assert m.EXIT_CHECK_FAIL == 1
    assert m.EXIT_BAD_INPUT == 2
    assert m.EXIT_CACHE_CORRUPT == 10
    assert m.EXIT_TOOL_MISSING == 11
    assert m.EXIT_WRITE_FAILED == 12
    assert m.EXIT_OTEL_UNREACHABLE == 13


@pytest.mark.parametrize("status", ["pass", "fail", "skip"])
def test_check_result_roundtrip(harness_modules, status: str) -> None:
    r = harness_modules.CheckResult(
        check_id="example.x",
        status=status,
        message="hello",
        duration_ms=42,
    )
    blob = r.model_dump_json()
    r2 = harness_modules.CheckResult.model_validate_json(blob)
    assert r2 == r


def test_error_envelope_optional_fields_omitted(harness_modules) -> None:
    e = harness_modules.ErrorEnvelope(code="E1", message="bad")
    dumped = e.model_dump(exclude_none=True)
    assert dumped == {"code": "E1", "message": "bad"}


def test_error_envelope_carries_location_fields(harness_modules) -> None:
    e = harness_modules.ErrorEnvelope(
        code="LINT",
        message="trailing whitespace",
        file="src/foo.py",
        line=10,
        column=80,
        snippet="    x = 1   ",
    )
    blob = e.model_dump_json()
    e2 = harness_modules.ErrorEnvelope.model_validate_json(blob)
    assert e2 == e
    assert e2.file == "src/foo.py"
    assert e2.line == 10
    assert e2.column == 80


def test_report_summary_from_checks(harness_modules) -> None:
    m = harness_modules
    checks = [
        m.CheckResult(check_id="a", status="pass"),
        m.CheckResult(check_id="b", status="pass"),
        m.CheckResult(check_id="c", status="fail"),
        m.CheckResult(check_id="d", status="skip"),
    ]
    s = m.ReportSummary.from_checks(checks, total_duration_ms=123)
    assert s.pass_count == 2
    assert s.fail_count == 1
    assert s.skip_count == 1
    assert s.total == 4
    assert s.duration_ms == 123


def test_verify_report_exit_code_derivation(harness_modules) -> None:
    m = harness_modules
    ok_checks = [m.CheckResult(check_id="a", status="pass"), m.CheckResult(check_id="b", status="skip")]
    r_ok = m.VerifyReport.from_checks(ok_checks, total_duration_ms=10)
    assert r_ok.exit_code == m.EXIT_OK

    fail_checks = [m.CheckResult(check_id="a", status="pass"), m.CheckResult(check_id="b", status="fail")]
    r_bad = m.VerifyReport.from_checks(fail_checks, total_duration_ms=10)
    assert r_bad.exit_code == m.EXIT_CHECK_FAIL


def test_verify_report_roundtrip(harness_modules) -> None:
    m = harness_modules
    checks = [
        m.CheckResult(check_id="a", status="pass", duration_ms=1),
        m.CheckResult(
            check_id="b",
            status="fail",
            error=m.ErrorEnvelope(code="X", message="oops", file="a.py", line=3),
        ),
    ]
    r = m.VerifyReport.from_checks(checks, total_duration_ms=5)
    blob = r.model_dump_json()
    r2 = m.VerifyReport.model_validate_json(blob)
    assert r2 == r
    assert r2.format_version == "1"


def test_check_spec_internal_with_callable(harness_modules) -> None:
    m = harness_modules

    def my_check() -> None:
        return None

    spec = m.CheckSpec(check_id="x.y", fn=my_check, tier="quick", category="test")
    assert spec.fn is my_check
    assert spec.tier == "quick"
    assert spec.inputs == []
    assert spec.fixable is False
    assert spec.skip_if_unavailable is False


def test_check_catalog_entry_excludes_fn_and_serializes(harness_modules) -> None:
    m = harness_modules

    def my_check() -> None:
        return None

    spec = m.CheckSpec(
        check_id="x.y",
        fn=my_check,
        tier="quick",
        category="test",
        description="desc",
        inputs=[".a", ".b"],
        fixable=True,
        tool="ruff",
    )
    entry = m.CheckCatalogEntry.from_spec(spec)
    assert not hasattr(entry, "fn") or "fn" not in entry.model_fields
    blob = entry.model_dump_json()
    parsed = json.loads(blob)
    assert "fn" not in parsed
    assert parsed["check_id"] == "x.y"
    assert parsed["tool"] == "ruff"

    # Schema must build cleanly (no Callable shape).
    schema = m.CheckCatalogEntry.model_json_schema()
    assert "properties" in schema
    assert "fn" not in schema["properties"]
