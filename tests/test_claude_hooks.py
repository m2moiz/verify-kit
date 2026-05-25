# Copyright (c) 2026 Moiz Hussain
# SPDX-License-Identifier: MIT

"""Tests for Claude Code hook scripts (plan 03-02 T07).

The .jinja2 hook files contain no Jinja syntax (pure bash), so we copy
the source verbatim to a tmp dir, drop a fake `just` shim on PATH that
either succeeds, fails, or records its invocation, and assert exit code
+ side effects. This avoids the cost of a full copier-render per test.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOK_DIR = (
    _REPO_ROOT
    / "template"
    / "{% if has_claude_code %}.claude{% endif %}"
    / "hooks"
)
_POST_TOOL_USE_SRC = _HOOK_DIR / "post-tool-use.sh.jinja2"
_STOP_SRC = _HOOK_DIR / "stop.sh.jinja2"


def _copy_hook(src: Path, dst_dir: Path, name: str) -> Path:
    """Copy a .jinja2 hook to dst_dir/name; mark executable."""
    dst = dst_dir / name
    shutil.copy(src, dst)
    dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return dst


def _write_fake_just(
    bin_dir: Path,
    *,
    exit_code: int = 0,
    marker: Path | None = None,
) -> None:
    """Write `bin_dir/just` that exits `exit_code` and optionally touches a marker."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    just = bin_dir / "just"
    marker_line = f'echo called >> "{marker}"' if marker is not None else ""
    just.write_text(
        "#!/usr/bin/env bash\n"
        f"{marker_line}\n"
        f"exit {exit_code}\n"
    )
    just.chmod(0o755)


# ── post-tool-use ────────────────────────────────────────────────────────────


def test_post_tool_use_passes_on_clean_project(tmp_path: Path) -> None:
    """Both `just lint` and `just typecheck` succeed -> exit 0."""
    hook = _copy_hook(_POST_TOOL_USE_SRC, tmp_path, "post-tool-use.sh")
    bin_dir = tmp_path / "bin"
    _write_fake_just(bin_dir, exit_code=0)

    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = subprocess.run([str(hook)], cwd=tmp_path, env=env)
    assert proc.returncode == 0


def test_post_tool_use_blocks_on_lint_failure(tmp_path: Path) -> None:
    """`just lint` fails -> hook exits 2 (blocks tool result)."""
    hook = _copy_hook(_POST_TOOL_USE_SRC, tmp_path, "post-tool-use.sh")
    bin_dir = tmp_path / "bin"
    _write_fake_just(bin_dir, exit_code=1)

    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = subprocess.run([str(hook)], cwd=tmp_path, env=env)
    assert proc.returncode == 2


# ── stop hook ────────────────────────────────────────────────────────────────


def test_stop_hook_passes_when_verify_passes(tmp_path: Path) -> None:
    """`just verify --quick` returns 0 -> hook exits 0."""
    hook = _copy_hook(_STOP_SRC, tmp_path, "stop.sh")
    bin_dir = tmp_path / "bin"
    _write_fake_just(bin_dir, exit_code=0)

    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    # Strip both bypass vars so the hook ACTUALLY runs verify.
    env.pop("VERIFY_KIT_SKIP", None)
    env.pop("stop_hook_active", None)
    proc = subprocess.run([str(hook)], cwd=tmp_path, env=env)
    assert proc.returncode == 0


def test_stop_hook_blocks_when_verify_fails(tmp_path: Path) -> None:
    """`just verify --quick` fails -> hook exits 2; stderr explains."""
    hook = _copy_hook(_STOP_SRC, tmp_path, "stop.sh")
    bin_dir = tmp_path / "bin"
    _write_fake_just(bin_dir, exit_code=1)

    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    env.pop("VERIFY_KIT_SKIP", None)
    env.pop("stop_hook_active", None)
    proc = subprocess.run([str(hook)], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert proc.returncode == 2
    assert "refusing stop" in proc.stderr


def test_stop_hook_recursion_guard(tmp_path: Path) -> None:
    """stop_hook_active=1 -> hook exits 0; `just` is NOT called."""
    hook = _copy_hook(_STOP_SRC, tmp_path, "stop.sh")
    bin_dir = tmp_path / "bin"
    marker = tmp_path / "just-called"
    # Stub `just` so failing it would still exit 2 -- proves the hook didn't call it.
    _write_fake_just(bin_dir, exit_code=1, marker=marker)

    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "stop_hook_active": "1"}
    proc = subprocess.run([str(hook)], cwd=tmp_path, env=env)
    assert proc.returncode == 0
    assert not marker.exists(), "stop hook called `just` despite stop_hook_active=1"


def test_stop_hook_skip_env(tmp_path: Path) -> None:
    """VERIFY_KIT_SKIP=1 -> hook exits 0; `just` is NOT called."""
    hook = _copy_hook(_STOP_SRC, tmp_path, "stop.sh")
    bin_dir = tmp_path / "bin"
    marker = tmp_path / "just-called"
    _write_fake_just(bin_dir, exit_code=1, marker=marker)

    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "VERIFY_KIT_SKIP": "1"}
    proc = subprocess.run([str(hook)], cwd=tmp_path, env=env)
    assert proc.returncode == 0
    assert not marker.exists(), "stop hook called `just` despite VERIFY_KIT_SKIP=1"
