# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.deploy.check_deploy_config (deploy.config).

Covers (hermetic — the prod-readiness probe subprocess is NEVER actually spawned;
``subprocess.run`` is monkeypatched to a fake that returns a verdict token):
- registry registration + spec metadata (tier=standard, category=deploy)
- pass when the probe reports CLOSED (prod/no-token rejected — fails closed)
- PLANTED FAILURE: probe reports OPEN → fail with dotted code deploy.config.fail_open
- PLANTED FAILURE: probe reports NO_GUARD → fail with deploy.config.no_validator
- skip when the probe reports IMPORT_ERROR (app not installed)
- fail (not silent pass) on unrecognized probe output
- fail with tool-missing when uv is absent
- the probe env force-sets ENV=prod and SCRUBS VERIFYKIT_AUTH_TOKEN
- carryover-cwd: subprocess.run receives cwd=cwd

The real end-to-end forcing function (render a has_backend scaffold → delete
Settings.assert_deploy_ready() → deploy.config goes red) is verified against a
rendered scaffold during the verify-the-verifier step; these hermetic tests guard
the verdict-parsing + registration contract in CI without a slow render+sync run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def deploy_modules(tmp_path_factory: pytest.TempPathFactory):
    # _vcs_ref="HEAD": deploy.config was added after the latest release tag, so
    # render from the worktree HEAD (not the tag) to include it. has_backend is
    # required (deploy.py is has_backend-gated and imports harness.checks.backend).
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("deploy-cfg-scratch"),
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


def _fake_run(stdout: str, *, returncode: int = 0, stderr: str = ""):
    def _run(argv, **kwargs):
        return subprocess.CompletedProcess(
            args=argv, returncode=returncode, stdout=stdout, stderr=stderr
        )

    return _run


# The check routes its probe through harness.proc.run (imported as proc_run);
# monkeypatch that symbol on the deploy module so no real `uv run` is spawned.


def test_deploy_config_registered(deploy_modules) -> None:
    registry, _ = deploy_modules
    ids = {s.check_id for s in registry.list_checks()}
    assert "deploy.config" in ids


def test_deploy_config_spec_metadata(deploy_modules) -> None:
    registry, _ = deploy_modules
    spec = registry.get_check("deploy.config")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "deploy"
    assert spec.fixable is False
    assert spec.tool == "uv"


def test_pass_when_probe_reports_closed(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.config")
    monkeypatch.setattr(deploy_mod, "proc_run", _fake_run("CLOSED\n"))
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_fail_open_is_flagged_with_dotted_code(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PLANTED: the guard exists but does not raise → prod ships auth-open."""
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.config")
    monkeypatch.setattr(deploy_mod, "proc_run", _fake_run("OPEN\n"))
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deploy.config.fail_open"


def test_missing_guard_is_flagged(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PLANTED: Settings.assert_deploy_ready() removed entirely → no_validator."""
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.config")
    monkeypatch.setattr(deploy_mod, "proc_run", _fake_run("NO_GUARD\n"))
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deploy.config.no_validator"


def test_skip_when_app_not_importable(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.config")
    monkeypatch.setattr(deploy_mod, "proc_run", _fake_run("IMPORT_ERROR\n"))
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"


def test_unrecognized_output_fails_not_passes(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A garbled / empty probe output must FAIL (venv unsynced), never silently pass."""
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.config")
    monkeypatch.setattr(
        deploy_mod, "proc_run", _fake_run("", returncode=1, stderr="ModuleNotFoundError")
    )
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deploy.config.probe_error"


def test_fail_when_uv_missing(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.config")

    def _raise(argv, **kwargs):
        raise FileNotFoundError("uv")

    monkeypatch.setattr(deploy_mod, "proc_run", _raise)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "deploy.config.tool-missing"


def test_probe_env_scrubs_token_and_sets_prod(
    deploy_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The probe must run with ENV=prod and NO VERIFYKIT_AUTH_TOKEN, even when the
    ambient environment exports a token (selftest CI does)."""
    registry, deploy_mod = deploy_modules
    spec = registry.get_check("deploy.config")
    # Simulate an ambient token the way CI exports one.
    monkeypatch.setenv("VERIFYKIT_AUTH_TOKEN", "ambient-token-from-ci")
    monkeypatch.setenv("ENV", "dev")
    captured: dict[str, object] = {}

    def _run(argv, **kwargs):
        captured["env"] = kwargs.get("env")
        captured["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="CLOSED\n", stderr="")

    monkeypatch.setattr(deploy_mod, "proc_run", _run)
    spec.fn(cwd=tmp_path)

    env = captured["env"]
    assert isinstance(env, dict)
    assert env.get("ENV") == "prod"
    assert "VERIFYKIT_AUTH_TOKEN" not in env, "ambient token must be scrubbed from the probe env"
    # carryover-cwd: subprocess is rooted at the explicit cwd (REVIEW-CHECKLIST §1).
    assert captured["cwd"] == tmp_path
