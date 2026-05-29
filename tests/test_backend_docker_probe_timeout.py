# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""verify-kit-32t: the backend Docker probe must not false-skip under daemon load.

`harness.checks.backend._docker_reachable` previously used a 3s `docker info`
timeout with no retry, so under daemon load (concurrent builds, a cold Docker
Desktop, image pulls) the probe timed out and the backend slice SKIPPED even
though Docker was up. That also disagreed with the conftest probe
(tests/backend/conftest.py uses 30s).

The fix raises the default timeout to 10s and retries once on TimeoutExpired
(sleep ~1s, probe again) before declaring the daemon unreachable. The
`shutil.which('docker')` fast-path is preserved.

This test renders a backend scaffold at HEAD (so it includes the working-tree
fix), then drives `_docker_reachable` inside the scratch via a subprocess that
monkeypatches `subprocess.run` / `time.sleep` — no real Docker daemon and no
heavy container startup is involved.
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from tests._helpers import _CLEAN_ENV, render_scratch_project

# Driver script executed inside the rendered scaffold (cwd=scratch) via
# `uv run -- python -c`. It exercises the rendered _docker_reachable directly,
# mocking the subprocess + sleep so no real docker is touched.
_DRIVER = textwrap.dedent(
    """
    import inspect
    import shutil
    import subprocess as sp

    import harness.checks.backend as b

    # (1) Default timeout must be >= 10s — the conftest probe uses 30s, and a 3s
    # budget false-skips under daemon load (verify-kit-32t).
    default_timeout = inspect.signature(b._docker_reachable).parameters["timeout_s"].default
    print("default_timeout=" + str(default_timeout))

    # The function does `import shutil` locally, so patch shutil.which on the
    # real module. Pretend docker IS on PATH so we exercise the probe (not the
    # fast-path).
    shutil.which = lambda name: "/usr/bin/docker"

    class _OK:
        returncode = 0
        stdout = "27.0.0\\n"

    # (2) First `docker info` times out (daemon busy), second succeeds. With the
    # retry-once fix this must return True; the old single-shot code returned False.
    calls = {"n": 0}

    def fake_run_retry(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise sp.TimeoutExpired(cmd="docker info", timeout=kwargs.get("timeout"))
        return _OK()

    b.subprocess.run = fake_run_retry
    b.time.sleep = lambda *_a, **_k: None  # don't actually back off in the test
    result_retry = b._docker_reachable()
    print("retry_result=" + str(result_retry))
    print("retry_calls=" + str(calls["n"]))

    # (3) Sanity: a missing docker binary still returns False immediately
    # (fast-path preserved — no probe, no retry).
    shutil.which = lambda name: None
    print("missing_binary_result=" + str(b._docker_reachable()))
    """
)


def test_docker_probe_default_timeout_and_retry(tmp_path: Path) -> None:
    scratch = render_scratch_project(
        tmp_path,
        has_backend=True,
        has_llm=False,
        has_db=True,
        _vcs_ref="HEAD",
    )

    proc = subprocess.run(
        ["uv", "run", "--", "python", "-c", _DRIVER],
        cwd=scratch,
        env=_CLEAN_ENV,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"driver failed:\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}"

    out = proc.stdout

    # (1) Default timeout raised to >= 10s.
    line = next(ln for ln in out.splitlines() if ln.startswith("default_timeout="))
    default_timeout = float(line.split("=", 1)[1])
    assert default_timeout >= 10.0, (
        f"_docker_reachable default timeout must be >= 10s to avoid false-skips "
        f"under daemon load; got {default_timeout}"
    )

    # (2) A single TimeoutExpired followed by success must NOT return False —
    # the retry kicks in and the second probe succeeds.
    assert "retry_result=True" in out, (
        f"a transient TimeoutExpired-then-success must be reachable (retry-once); got:\n{out}"
    )
    assert "retry_calls=2" in out, (
        f"probe must retry exactly once on TimeoutExpired (2 total attempts); got:\n{out}"
    )

    # (3) Fast-path preserved: missing docker binary returns False immediately.
    assert "missing_binary_result=False" in out, (
        f"missing docker binary must still return False (fast-path); got:\n{out}"
    )
