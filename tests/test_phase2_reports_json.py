"""Tests for harness.reports.json_emit and harness.reports.jsonl (Plan 02-05, Task 2).

Covers:
- json_emit produces Decision 1.1 inline-error envelope shape
- Optional fields (hint, fix_command, docs_url) are omitted when None
- jsonl produces N+1 lines (one per check + summary)
- jsonl summary line has type=="summary"
"""
from __future__ import annotations

import io
import json
import sys

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def json_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("reports-json-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.reports.json_emit as json_emit
        import harness.reports.jsonl as jsonl
        import harness.models as models

        yield json_emit, jsonl, models
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _failing_report(models):
    err = models.ErrorEnvelope(
        code="lint.ruff.E501",
        message="line too long",
        hint="reformat the line",
        # docs_url intentionally None to test exclude_none
    )
    fail = models.CheckResult(
        check_id="lint.ruff",
        status="fail",
        message="1 issue",
        duration_ms=15,
        error=err,
    )
    return models.VerifyReport.from_checks([fail], total_duration_ms=15)


def test_json_inline_error_envelope(json_modules) -> None:
    json_emit, _jsonl, models = json_modules
    report = _failing_report(models)
    buf = io.StringIO()
    json_emit.emit(report, buf)
    data = json.loads(buf.getvalue())
    assert data["checks"][0]["error"]["code"] == "lint.ruff.E501"
    assert data["checks"][0]["error"]["message"] == "line too long"
    assert data["format_version"] == "1"
    assert data["exit_code"] == 1


def test_json_omits_none_optional_fields(json_modules) -> None:
    json_emit, _jsonl, models = json_modules
    report = _failing_report(models)
    buf = io.StringIO()
    json_emit.emit(report, buf)
    data = json.loads(buf.getvalue())
    err = data["checks"][0]["error"]
    assert "hint" in err  # present
    assert "docs_url" not in err  # excluded as None
    assert "fix_command" not in err  # excluded as None
    assert "file" not in err
    assert "snippet" not in err


def test_jsonl_line_count_and_summary(json_modules) -> None:
    _json_emit, jsonl, models = json_modules
    checks = [
        models.CheckResult(check_id="a", status="pass"),
        models.CheckResult(check_id="b", status="pass"),
        models.CheckResult(check_id="c", status="pass"),
    ]
    report = models.VerifyReport.from_checks(checks, total_duration_ms=10)
    buf = io.StringIO()
    jsonl.emit(report, buf)
    lines = [line for line in buf.getvalue().splitlines() if line]
    assert len(lines) == 4  # 3 checks + 1 summary
    final = json.loads(lines[-1])
    assert final["type"] == "summary"
    assert final["exit_code"] == 0
    assert final["pass_count"] == 3


def test_jsonl_each_check_parseable(json_modules) -> None:
    _json_emit, jsonl, models = json_modules
    report = _failing_report(models)
    buf = io.StringIO()
    jsonl.emit(report, buf)
    lines = [line for line in buf.getvalue().splitlines() if line]
    assert len(lines) == 2
    check = json.loads(lines[0])
    assert check["check_id"] == "lint.ruff"
    assert check["error"]["code"] == "lint.ruff.E501"
