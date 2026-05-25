# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for Plan 02-06 Task 3 — Jaeger client + justfile recipes + pyproject deps."""
from __future__ import annotations

import io
import sys
import tomllib
from pathlib import Path
from unittest import mock

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def jaeger_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(tmp_path_factory.mktemp("jaeger-scratch"))
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.jaeger as jaeger
        yield {"scratch": scratch, "jaeger": jaeger}
    finally:
        sys.path.remove(str(scratch))


# ── (a) fetch_latest_trace returns None on network error ─────────────────────


def test_fetch_latest_trace_returns_none_on_connection_error(jaeger_modules):
    jaeger = jaeger_modules["jaeger"]
    import httpx

    with mock.patch.object(httpx, "get", side_effect=httpx.ConnectError("boom")):
        result = jaeger.fetch_latest_trace()
    assert result is None


# ── (b) fetch_latest_trace returns first trace on valid response ─────────────


def test_fetch_latest_trace_returns_first_trace(jaeger_modules):
    jaeger = jaeger_modules["jaeger"]
    import httpx

    fake_payload = {
        "data": [
            {
                "traceID": "abc123",
                "spans": [
                    {
                        "operationName": "check:mise.toml.valid",
                        "duration": 12345,
                        "startTime": 1000,
                    },
                ],
            }
        ]
    }

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return fake_payload

    with mock.patch.object(httpx, "get", return_value=FakeResp()):
        result = jaeger.fetch_latest_trace()

    assert result is not None
    assert result["traceID"] == "abc123"


def test_fetch_latest_trace_returns_none_on_empty_data(jaeger_modules):
    jaeger = jaeger_modules["jaeger"]
    import httpx

    class EmptyResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": []}

    with mock.patch.object(httpx, "get", return_value=EmptyResp()):
        result = jaeger.fetch_latest_trace()
    assert result is None


# ── (c) render_trace_waterfall prints something containing operationName ─────


def test_render_trace_waterfall_prints_operation_name(jaeger_modules):
    from rich.console import Console

    jaeger = jaeger_modules["jaeger"]
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    trace = {
        "traceID": "abc",
        "spans": [
            {
                "operationName": "check:mise.toml.valid",
                "duration": 12345,
                "startTime": 1000,
                "references": [],
            },
            {
                "operationName": "check:lint.ruff",
                "duration": 7000,
                "startTime": 2000,
                "references": [],
            },
        ],
    }
    jaeger.render_trace_waterfall(trace, console)
    output = buf.getvalue()
    assert "mise.toml.valid" in output
    assert "lint.ruff" in output


# ── (d) `just --list` in rendered scratch project lists all 8 recipes ────────


def test_justfile_lists_expected_recipes(tmp_path: Path):
    """Render scratch project, run `just --list`, expect 8 recipes."""
    import shutil
    import subprocess

    if shutil.which("just") is None:
        pytest.skip("`just` not installed on this host")

    scratch = render_scratch_project(tmp_path)
    proc = subprocess.run(
        ["just", "--list", "--unsorted"],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    for recipe in [
        "verify",
        "lint",
        "format",
        "shell",
        "verify-clean",
        "trace-up",
        "trace-down",
        "trace",
    ]:
        assert recipe in out, f"missing recipe {recipe!r} in:\n{out}"


# ── (e) pyproject.toml after Copier render parses + has expected deps ────────


def test_pyproject_has_expected_dependencies(tmp_path: Path):
    scratch = render_scratch_project(tmp_path)
    pyproject = scratch / "pyproject.toml"
    assert pyproject.exists()
    data = tomllib.loads(pyproject.read_text())
    deps = data["project"]["dependencies"]
    needed = [
        "pydantic>=2",
        "typer>=0.12",
        "rich>=13",
        "pyyaml>=6",
        "structlog>=25",
        "httpx>=0.27",
        "opentelemetry-api==1.41.1",
        "opentelemetry-sdk==1.41.1",
        "opentelemetry-exporter-otlp-proto-grpc==1.41.1",
    ]
    for entry in needed:
        assert entry in deps, f"missing dep {entry!r} in {deps!r}"
    scripts = data["project"]["scripts"]
    assert scripts["verify-kit"] == "harness.cli:app_entry"
    dev = data["project"]["optional-dependencies"]["dev"]
    assert any(d.startswith("hypothesis") for d in dev)
    assert any(d.startswith("jsonschema") for d in dev)
