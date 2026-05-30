# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.deploy.check_deploy_image_boots (deploy.image_boots).

Covers (hermetic — NO real Docker is touched; ``_docker_reachable`` and the
``proc_run`` docker calls are monkeypatched to fakes that script build / run /
inspect / logs outcomes):
- registry registration + spec metadata (tier=slow, category=deploy, tool=docker)
- skip when the Docker daemon is unreachable
- pass when build + run succeed and the container reports healthy
- PLANTED FAILURE: container exits before healthy → fail deploy.image_boots.unhealthy
- fail deploy.image_boots.build_failed when `docker build` exits non-zero
- cleanup: `docker rm -f` is invoked on every exit path (finally)

The real end-to-end forcing function (build the real image, plant a broken CMD →
the container exits → deploy.image_boots goes red) is a slow-tier check verified
against a rendered scaffold + live Docker during verify-the-verifier; it runs in
CI via `verify --full` (live-full) per rule-14 (slow-tier ≠ never-run).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def deploy_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("deploy-img-scratch"),
        _vcs_ref="HEAD",
        has_backend=True,
        has_db=False,
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import deploy as deploy_mod

        yield registry, deploy_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _docker_fake(deploy_mod, monkeypatch, *, build_rc=0, run_rc=0, inspect_outputs=None, logs="boom"):
    """Install fakes for _docker_reachable + proc_run; return the call log.

    inspect_outputs: list of "state|health" strings returned by successive
    `docker inspect` calls (the last one repeats if the poll outlives the list).
    """
    calls: list[list[str]] = []
    inspect_seq = list(inspect_outputs or ["running|healthy"])

    monkeypatch.setattr(deploy_mod, "_docker_reachable", lambda *a, **k: True)
    monkeypatch.setattr(deploy_mod.time, "sleep", lambda *_: None)

    def _fake_proc_run(argv, **kwargs):
        calls.append(list(argv))
        sub = argv[1] if len(argv) > 1 else ""
        if sub == "build":
            return subprocess.CompletedProcess(argv, build_rc, "built", "build-err")
        if sub == "run":
            return subprocess.CompletedProcess(argv, run_rc, "container-id", "run-err")
        if sub == "inspect":
            out = inspect_seq.pop(0) if len(inspect_seq) > 1 else inspect_seq[0]
            return subprocess.CompletedProcess(argv, 0, out, "")
        if sub == "logs":
            return subprocess.CompletedProcess(argv, 0, logs, "")
        if sub == "rm":
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(deploy_mod, "proc_run", _fake_proc_run)
    return calls


def test_image_boots_registered(deploy_modules) -> None:
    registry, _ = deploy_modules
    ids = {s.check_id for s in registry.list_checks()}
    assert "deploy.image_boots" in ids


def test_image_boots_spec_metadata(deploy_modules) -> None:
    registry, _ = deploy_modules
    spec = registry.get_check("deploy.image_boots")
    assert spec is not None
    assert spec.tier == "slow"
    assert spec.category == "deploy"
    assert spec.fixable is False
    assert spec.tool == "docker"


def test_skip_when_docker_unreachable(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.image_boots")
    monkeypatch.setattr(deploy_mod, "_docker_reachable", lambda *a, **k: False)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"


def test_pass_when_container_boots_healthy(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.image_boots")
    calls = _docker_fake(
        deploy_mod, monkeypatch, inspect_outputs=["starting|starting", "running|healthy"]
    )
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None
    # Cleanup ran: `docker rm -f` invoked at least once (pre-build + finally).
    assert any(c[:3] == ["docker", "rm", "-f"] for c in calls)


def test_fail_unhealthy_when_container_exits(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PLANTED: a broken CMD makes the container exit before becoming healthy."""
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.image_boots")
    _docker_fake(deploy_mod, monkeypatch, inspect_outputs=["exited|"], logs="ModuleNotFoundError: nope")
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deploy.image_boots.unhealthy"


def test_fail_when_build_fails(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.image_boots")
    _docker_fake(deploy_mod, monkeypatch, build_rc=1)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deploy.image_boots.build_failed"


def test_container_cleaned_up_on_failure(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`docker rm -f` must run even when the boot fails (finally block)."""
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.image_boots")
    calls = _docker_fake(deploy_mod, monkeypatch, inspect_outputs=["exited|"])
    spec.fn(cwd=tmp_path)
    assert any(c[:3] == ["docker", "rm", "-f"] for c in calls)
