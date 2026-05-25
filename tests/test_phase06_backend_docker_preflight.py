# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Phase 6 follow-up (verify-kit-d1o): assert the harness `backend` check
skips with a clear hint when the Docker daemon is unreachable, instead of
hanging Testcontainers and timing out the umbrella `just verify` at 600s.

Renders a backend scaffold, then invokes the rendered `harness.checks.backend`
module via subprocess with a stripped PATH so the `docker` binary is hidden.
Asserts `_docker_reachable()` returns False and the check returns status="skip"
with an actionable message.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from tests._helpers import _CLEAN_ENV, render_scratch_project


def _path_without_docker() -> dict[str, str]:
    """Build env with uv reachable but `docker` deliberately hidden.

    Creates a tmp directory containing a symlink to `uv` only, then sets PATH
    to that dir + /usr/bin:/bin. Docker (which lives in /usr/local/bin or
    /opt/homebrew/bin) is not on this PATH, so `shutil.which('docker')` in
    the harness preflight returns None.
    """
    uv_src = shutil.which("uv")
    assert uv_src is not None, "uv must be installed to run this test"
    bin_dir = tempfile.mkdtemp(prefix="vk-test-bin-")
    os.symlink(uv_src, os.path.join(bin_dir, "uv"))
    # Python interpreter the test subprocess will use must also be reachable.
    py_src = shutil.which("python3") or shutil.which("python")
    if py_src is not None and not os.path.exists(os.path.join(bin_dir, "python3")):
        os.symlink(py_src, os.path.join(bin_dir, "python3"))
    return {**_CLEAN_ENV, "PATH": f"{bin_dir}:/usr/bin:/bin"}


def test_backend_check_skips_when_docker_unreachable(tmp_path: Path) -> None:
    scratch = render_scratch_project(
        tmp_path,
        has_backend=True,
        has_llm=False,
        has_db=True,
    )

    # Probe-only: confirm the helper returns False without docker on PATH.
    probe = subprocess.run(
        ["uv", "run", "--", "python", "-c",
         "from harness.checks.backend import _docker_reachable; "
         "print('reachable=' + str(_docker_reachable(timeout_s=2.0)))"],
        cwd=scratch,
        env=_path_without_docker(),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert probe.returncode == 0, f"probe failed: {probe.stderr}"
    assert "reachable=False" in probe.stdout, (
        f"_docker_reachable should return False when docker missing from PATH; got {probe.stdout!r}"
    )

    # Full check: run() returns a skip CheckResult, no Testcontainers hang.
    check = subprocess.run(
        ["uv", "run", "--", "python", "-c",
         "from pathlib import Path; "
         "from harness.checks.backend import run; "
         f"r = run(Path('{scratch}')); "
         "print('status=' + r.status); "
         "print('msg_has_docker_hint=' + str('Docker daemon' in r.message))"],
        cwd=scratch,
        env=_path_without_docker(),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert check.returncode == 0, f"check exec failed: {check.stderr}"
    assert "status=skip" in check.stdout, (
        f"backend check must skip (not fail/hang) when docker unreachable; got {check.stdout!r}"
    )
    assert "msg_has_docker_hint=True" in check.stdout, (
        f"skip message must mention Docker so user knows how to fix; got {check.stdout!r}"
    )
