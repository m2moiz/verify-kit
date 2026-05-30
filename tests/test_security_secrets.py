# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.security (security.secrets — Wave 2).

Covers:
- registry conformance: security.secrets is registered always-on with the
  correct tier/category/fixable/tool and NO forbidden @register kwargs.
- planted-failure forcing functions (the check MUST go red on a real defect):
    (a) a cwd with a git-tracked `.env`        → fail  security.secrets.env_tracked
    (b) a planted AKIA-style secret + gitleaks  → fail  security.secrets.leak
        (gitleaks monkeypatched to return a finding — hermetic, no real binary)
    (c) a clean git repo (no tracked .env, gitleaks clean) → pass
    (d) gitleaks ABSENT → the .env guard still runs, no crash, pass on clean
- offline-first: a missing gitleaks NEVER fails the check and NEVER recommends
  a network auto-fetch.
- carryover-cwd: git/gitleaks subprocesses are rooted at the supplied cwd.

Shape mirrors tests/test_phase2_checks_lint_format.py: render a scratch scaffold
once, import the check module from it, drive spec.fn(cwd=...) with monkeypatched
subprocess for the gitleaks layer and real `git init` tmp dirs for the .env layer.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


def _git_init(path: Path) -> None:
    """Initialize a quiet git repo at `path` with identity set (no global config)."""
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True
    )


def _git_commit_all(path: Path) -> None:
    """Stage and commit everything under `path`."""
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-qm", "init"], cwd=path, check=True, capture_output=True
    )


@pytest.fixture(scope="module")
def security_mod(tmp_path_factory: pytest.TempPathFactory):
    """Render a scratch scaffold and import its harness.checks.security module."""
    # _vcs_ref="HEAD": security.secrets was added after the latest release tag,
    # so render from the worktree HEAD (not the tag) to include the module.
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("sec-scratch"), _vcs_ref="HEAD"
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import security as security_mod

        yield registry, security_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


# ── Registry conformance ──────────────────────────────────────────────────────


def test_security_secrets_is_registered_always_on(security_mod) -> None:
    """security.secrets is registered unconditionally on a default (no-add-on) render."""
    registry, _ = security_mod
    ids = {s.check_id for s in registry.list_checks()}
    assert "security.secrets" in ids


def test_security_secrets_spec_metadata(security_mod) -> None:
    """Frozen metadata: tier=standard, category=security, fixable=False, tool=gitleaks."""
    registry, _ = security_mod
    spec = registry.get_check("security.secrets")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "security"
    assert spec.fixable is False
    assert spec.tool == "gitleaks"


def test_security_secrets_has_no_forbidden_register_kwargs(security_mod) -> None:
    """The @register call uses only frozen kwargs — no severity=/tags= leaked through."""
    registry, security_module = security_mod
    spec = registry.get_check("security.secrets")
    assert spec is not None
    # CheckSpec only carries the frozen surface; a forbidden kwarg would have
    # raised TypeError at import time. Belt-and-suspenders: the source must not
    # mention the banned kwargs.
    src = Path(security_module.__file__).read_text()
    assert "severity=" not in src
    assert "tags=" not in src


# ── (a) planted failure: git-tracked .env → fail env_tracked ──────────────────


def test_tracked_env_fails_env_tracked(security_mod, tmp_path: Path) -> None:
    """A git-tracked `.env` fails with code security.secrets.env_tracked."""
    registry, _ = security_mod
    spec = registry.get_check("security.secrets")
    _git_init(tmp_path)
    (tmp_path / ".env").write_text("SECRET=hunter2\n")
    _git_commit_all(tmp_path)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "security.secrets.env_tracked"
    assert ".env" in result.error.message
    assert "git rm --cached" in (result.error.hint or "")


def test_tracked_dotenv_variant_fails(security_mod, tmp_path: Path) -> None:
    """`.env.production` (a `.env.*` that is not `.env.example`) also fails."""
    registry, _ = security_mod
    spec = registry.get_check("security.secrets")
    _git_init(tmp_path)
    (tmp_path / ".env.production").write_text("PROD_SECRET=x\n")
    _git_commit_all(tmp_path)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "security.secrets.env_tracked"


def test_tracked_env_example_alone_does_not_fail(
    security_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tracked `.env.example` (placeholders) is allowed — it must NOT trip the guard."""
    registry, security_module = security_mod
    spec = registry.get_check("security.secrets")
    _git_init(tmp_path)
    (tmp_path / ".env.example").write_text("SECRET=changeme\n")
    _git_commit_all(tmp_path)
    # Force the gitleaks layer absent so the verdict is purely the .env guard.
    monkeypatch.setattr(security_module.shutil, "which", lambda _: None)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"


# ── (b) planted failure: AKIA secret + gitleaks finding → fail leak ───────────


def test_planted_secret_with_gitleaks_finding_fails_leak(
    security_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A planted AKIA-style key + gitleaks (monkeypatched to find it) → fail leak."""
    registry, security_module = security_mod
    spec = registry.get_check("security.secrets")
    _git_init(tmp_path)
    (tmp_path / "config.py").write_text('AWS_KEY = "AKIA1234567890ABCD12"\n')
    _git_commit_all(tmp_path)

    # Make a gitleaks binary "resolve" without needing a real install.
    fake_gitleaks = tmp_path / "fake-gitleaks"
    fake_gitleaks.write_text("#!/bin/sh\nexit 0\n")
    fake_gitleaks.chmod(0o755)
    monkeypatch.setattr(
        security_module.shutil, "which", lambda _: str(fake_gitleaks)
    )

    finding = [
        {
            "RuleID": "aws-access-token",
            "Description": "Detected an AWS Access Key",
            "StartLine": 1,
            "File": "config.py",
            "Secret": "AKIA1234567890ABCD12",
        }
    ]
    captured: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        # Let the real `git ls-files` run (the repo is real); only fake gitleaks.
        if "ls-files" in argv:
            return subprocess.run(argv, capture_output=True, text=True, **{k: v for k, v in kwargs.items() if k in {"cwd", "timeout"}})
        captured["argv"] = argv
        captured["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(
            args=argv, returncode=1, stdout=json.dumps(finding), stderr=""
        )

    monkeypatch.setattr(security_module, "proc_run", fake_run)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "security.secrets.leak"
    assert result.error.file == "config.py"
    assert result.error.line == 1
    # carryover-cwd: gitleaks must have been invoked rooted at the scratch cwd.
    assert captured["cwd"] == tmp_path


# ── (c) clean repo (no tracked .env, gitleaks clean) → pass ───────────────────


def test_clean_repo_passes(
    security_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No tracked .env + gitleaks returns clean (exit 0) → pass."""
    registry, security_module = security_mod
    spec = registry.get_check("security.secrets")
    _git_init(tmp_path)
    (tmp_path / "README.md").write_text("# hi\n")
    _git_commit_all(tmp_path)

    fake_gitleaks = tmp_path / "fake-gitleaks"
    fake_gitleaks.write_text("#!/bin/sh\nexit 0\n")
    fake_gitleaks.chmod(0o755)
    monkeypatch.setattr(
        security_module.shutil, "which", lambda _: str(fake_gitleaks)
    )

    def fake_run(argv, **kwargs):
        # First call is `git ls-files` (real-ish); only intercept gitleaks.
        if "ls-files" in argv:
            return subprocess.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(security_module, "proc_run", fake_run)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"


# ── (d) gitleaks absent → .env guard still runs, no crash ─────────────────────


def test_gitleaks_absent_still_runs_env_guard_and_passes_clean(
    security_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """gitleaks absent on a clean repo → pass via the offline .env baseline (no crash)."""
    registry, security_module = security_mod
    spec = registry.get_check("security.secrets")
    _git_init(tmp_path)
    (tmp_path / "README.md").write_text("# hi\n")
    _git_commit_all(tmp_path)
    monkeypatch.setattr(security_module.shutil, "which", lambda _: None)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert "gitleaks" in result.message.lower()


def test_gitleaks_absent_still_catches_tracked_env(
    security_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even with gitleaks absent, a tracked `.env` still fails (offline guard)."""
    registry, security_module = security_mod
    spec = registry.get_check("security.secrets")
    _git_init(tmp_path)
    (tmp_path / ".env").write_text("SECRET=hunter2\n")
    _git_commit_all(tmp_path)
    monkeypatch.setattr(security_module.shutil, "which", lambda _: None)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "security.secrets.env_tracked"


def test_gitleaks_skip_message_does_not_recommend_network_fetch(
    security_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Offline-first: the gitleaks-absent message never recommends a network fetch."""
    registry, security_module = security_mod
    spec = registry.get_check("security.secrets")
    _git_init(tmp_path)
    (tmp_path / "README.md").write_text("# hi\n")
    _git_commit_all(tmp_path)
    monkeypatch.setattr(security_module.shutil, "which", lambda _: None)

    result = spec.fn(cwd=tmp_path)
    msg = result.message.lower()
    assert "pnpm dlx" not in msg
    assert "curl" not in msg
    assert "wget" not in msg


# ── non-git directory → no crash (layer 1 no-ops) ─────────────────────────────


def test_non_git_directory_does_not_crash(
    security_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cwd not a git repo + no gitleaks → the .env guard no-ops, check passes (no crash)."""
    registry, security_module = security_mod
    spec = registry.get_check("security.secrets")
    # No git init here. A bare .env on disk is NOT tracked, so it must not fail.
    (tmp_path / ".env").write_text("SECRET=hunter2\n")
    monkeypatch.setattr(security_module.shutil, "which", lambda _: None)

    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
