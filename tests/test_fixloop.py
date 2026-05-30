# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.fixloop (fixloop.oracle_preserved — anti-cheat guard).

This is the user's G2 keystone: catch a "fix" that goes green by DELETING the
test that proves the defect. The check is git-state-based, so these tests are
hermetic — git is never actually invoked; `fixloop.subprocess.run` is
monkeypatched to feed canned `git rev-parse` + `git diff` output for each
scenario:

- registry registration + spec metadata (tier=standard, category=fixloop,
  fixable=False, tool="git")
- fail (code .test_deleted) when a test is deleted AND non-test source is edited
- pass when ONLY a test is deleted (legitimate test removal, no source edit)
- pass when no test is deleted (ordinary source change)
- skip when git is missing (FileNotFoundError on the rev-parse probe)
- skip when cwd is not a git repo (rev-parse returns non-zero)

The planted-failure forcing function (render scratch → delete a test + edit a
source file in the working tree → `fixloop.oracle_preserved` goes red) is what
the orchestrator exercises end-to-end; these hermetic tests guard the
classification + git-parse contract in CI without a slow render+git run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project


@pytest.fixture(scope="module")
def fl_modules(tmp_path_factory: pytest.TempPathFactory):
    # _vcs_ref="HEAD": fixloop was added after the latest release tag, so render
    # from the worktree HEAD (not the tag) to include it.
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("fl-scratch"), _vcs_ref="HEAD"
    )
    sys.path.insert(0, str(scratch))
    try:
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]
        import harness.checks as checks  # noqa: F401
        import harness.registry as registry
        from harness.checks import fixloop as fixloop_mod

        yield registry, fixloop_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _make_fake_run(
    *,
    is_git: bool = True,
    deleted: list[str] | None = None,
    changed: list[str] | None = None,
    git_missing: bool = False,
):
    """Build a fake subprocess.run that answers the check's git invocations.

    The check issues three git calls: a `rev-parse --git-dir` probe, then a
    `diff ... --diff-filter=D` (deletions) and a `--diff-filter=AM` (added/mod).
    We dispatch on the argv to return the right canned output for each.
    """
    deleted = deleted or []
    changed = changed or []

    def fake_run(argv, **kwargs):
        if git_missing:
            raise FileNotFoundError("git")
        if "rev-parse" in argv:
            return subprocess.CompletedProcess(
                args=argv,
                returncode=0 if is_git else 128,
                stdout=".git\n" if is_git else "",
                stderr="" if is_git else "fatal: not a git repository",
            )
        # diff invocation — pick the bucket by the --diff-filter token.
        if any(a == "--diff-filter=D" for a in argv):
            out = "\n".join(deleted)
        elif any(a == "--diff-filter=AM" for a in argv):
            out = "\n".join(changed)
        else:
            out = ""
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=out + "\n", stderr=""
        )

    return fake_run


def test_fixloop_registered(fl_modules) -> None:
    registry, _ = fl_modules
    ids = {s.check_id for s in registry.list_checks()}
    assert "fixloop.oracle_preserved" in ids


def test_fixloop_spec_metadata(fl_modules) -> None:
    registry, _ = fl_modules
    spec = registry.get_check("fixloop.oracle_preserved")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "fixloop"
    assert spec.fixable is False
    assert spec.tool == "git"


def test_fixloop_fail_when_test_deleted_and_source_edited(
    fl_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The headline cheat: delete the oracle, edit the code, call it fixed."""
    registry, fl_mod = fl_modules
    spec = registry.get_check("fixloop.oracle_preserved")

    fake_run = _make_fake_run(
        deleted=["tests/test_widget.py"],
        changed=["harness/widget.py"],
    )
    monkeypatch.setattr(fl_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "fixloop.oracle_preserved.test_deleted"
    # Both the deleted test and the edited source should be named for the agent.
    assert "test_widget.py" in result.error.message
    assert "harness/widget.py" in result.error.message


def test_fixloop_pass_when_only_test_deleted(
    fl_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A test removal with NO source edit is a legitimate cleanup → pass."""
    registry, fl_mod = fl_modules
    spec = registry.get_check("fixloop.oracle_preserved")

    fake_run = _make_fake_run(deleted=["tests/test_obsolete.py"], changed=[])
    monkeypatch.setattr(fl_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_fixloop_pass_when_no_test_deleted(
    fl_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ordinary source change with no deletions → pass."""
    registry, fl_mod = fl_modules
    spec = registry.get_check("fixloop.oracle_preserved")

    fake_run = _make_fake_run(deleted=[], changed=["harness/widget.py"])
    monkeypatch.setattr(fl_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_fixloop_pass_when_non_test_file_deleted(
    fl_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deleting a NON-test file (e.g. dead code) while editing source is fine."""
    registry, fl_mod = fl_modules
    spec = registry.get_check("fixloop.oracle_preserved")

    fake_run = _make_fake_run(
        deleted=["harness/legacy.py"],
        changed=["harness/widget.py"],
    )
    monkeypatch.setattr(fl_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass"
    assert result.error is None


def test_fixloop_skip_when_git_missing(
    fl_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """git absent (FileNotFoundError on the probe) → skip (offline-safe)."""
    registry, fl_mod = fl_modules
    spec = registry.get_check("fixloop.oracle_preserved")

    fake_run = _make_fake_run(git_missing=True)
    monkeypatch.setattr(fl_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"
    assert result.error is None


def test_fixloop_skip_when_not_a_git_repo(
    fl_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rev-parse non-zero (not a git repo) → skip, never fail."""
    registry, fl_mod = fl_modules
    spec = registry.get_check("fixloop.oracle_preserved")

    fake_run = _make_fake_run(is_git=False)
    monkeypatch.setattr(fl_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"
    assert result.error is None


def test_fixloop_spec_detects_ts_spec_files(
    fl_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deleted `.spec.ts` test + edited `.ts` source must fail too (polyglot)."""
    registry, fl_mod = fl_modules
    spec = registry.get_check("fixloop.oracle_preserved")

    fake_run = _make_fake_run(
        deleted=["web/src/widget.spec.ts"],
        changed=["web/src/widget.ts"],
    )
    monkeypatch.setattr(fl_mod.subprocess, "run", fake_run)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "fixloop.oracle_preserved.test_deleted"
