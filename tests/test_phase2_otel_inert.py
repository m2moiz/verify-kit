# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""OBS-01 verification gate: ``harness.observability`` imports zero OTel modules
when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is unset.

Implements CONTEXT.md Decision 3.1's verification clause: "Phase 2 includes
an import-time test asserting that running
``python -X importtime -c 'import harness.observability'`` with
``OTEL_EXPORTER_OTLP_ENDPOINT`` unset produces ZERO ``opentelemetry.*``
lines on stderr."

Runs against a freshly-rendered + installed scratch project.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests._helpers import render_and_install, venv_python


@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("RUN_SLOW_TESTS"),
    reason="set RUN_SLOW_TESTS=1 to run scratch-render gate tests",
)
def test_observability_import_is_inert_without_endpoint(tmp_path: Path) -> None:
    """No ``opentelemetry.*`` or ``grpc.`` lines on importtime stderr."""
    scratch = render_and_install(tmp_path)

    env = os.environ.copy()
    env.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)

    result = subprocess.run(
        [venv_python(scratch), "-X", "importtime", "-c",
         "import harness.observability"],
        cwd=scratch,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"importtime run exited non-zero ({result.returncode})\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    # Walk importtime stderr; assert zero opentelemetry.* or grpc.* import lines.
    bad_lines = [
        line for line in result.stderr.splitlines()
        if "opentelemetry." in line or "grpc." in line
    ]
    assert not bad_lines, (
        "expected zero opentelemetry.*/grpc.* import lines when "
        "OTEL_EXPORTER_OTLP_ENDPOINT is unset; got:\n  "
        + "\n  ".join(bad_lines)
    )
