# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""beartype runtime type-checking hook (check_id types.runtime.hook).

The has_backend scaffold installs a beartype claw hook as the first statements
of ``app/__init__.py``. Two things must hold and are asserted here:

1. WIRING (fast, always runs): the rendered ``app/__init__.py`` calls
   ``beartype_this_package`` behind an ``os.getenv("ENV")`` gate that drops to
   the ``BeartypeStrategy.O0`` no-op in prod — and does NOT use ``APP_ENV``
   (a known BUILD-PLAN sketch bug; the live settings field is ``ENV``).

2. BEHAVIOUR (slow, uv-gated): a planted ``needs_int('x')`` call must raise
   ``BeartypeCallHintParamViolation`` under dev, and be a silent no-op under
   ``ENV=prod`` — proving the hook actually *catches* the class of bug pyright
   cannot see at runtime, not merely that it imports. Without this, a mis-wired
   hook (installed after the submodule import, or reading the wrong env var)
   would pass the wiring test while doing nothing.

``_vcs_ref="HEAD"`` is required so the render includes this hook (added after
the v0.1.0 tag), per the Phase 7+ render-test convention.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._helpers import render_and_install, render_scratch_project, venv_python

_BASE: dict[str, object] = {
    "project_name": "BeartypeHook",
    "project_description": "beartype runtime hook test",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
    "has_backend": True,
    "has_db": False,
    "has_llm": False,
    "has_web": False,
    "has_claude_code": False,
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    "has_devcontainer": False,
    "llm_backend": "none",
    "strict_mode": False,
}


def test_beartype_hook_wired_into_app_init(tmp_path: Path) -> None:
    """Rendered app/__init__.py installs the claw hook with the ENV prod gate."""
    scratch = render_scratch_project(tmp_path, _vcs_ref="HEAD", **_BASE)  # type: ignore[arg-type]
    init = (scratch / "app" / "__init__.py").read_text()

    assert "beartype_this_package" in init
    assert "from beartype.claw import beartype_this_package" in init
    # Prod gate keys off ENV (the live settings field), NOT the BUILD-PLAN's APP_ENV.
    assert 'os.getenv("ENV"' in init
    assert "APP_ENV" not in init
    # Prod path must be the O0 no-op strategy.
    assert "BeartypeStrategy.O0" in init


@pytest.mark.slow
def test_beartype_catches_param_violation_dev_noop_prod(tmp_path: Path) -> None:
    """A planted type violation raises in dev and is a no-op under ENV=prod."""
    if shutil.which("uv") is None:
        pytest.skip("uv not available on PATH")

    scratch = render_and_install(tmp_path, _vcs_ref="HEAD", **_BASE)  # type: ignore[arg-type]
    # Plant a beartyped function whose call site passes a wrongly-typed argument.
    (scratch / "app" / "_planted_bt.py").write_text(
        "def needs_int(x: int) -> int:\n    return x\n"
    )
    python = venv_python(scratch)
    snippet = "import app; from app._planted_bt import needs_int; print(needs_int('x'))"

    # dev (ENV unset): the str-for-int param must raise the beartype violation.
    dev_env = {k: v for k, v in os.environ.items() if k != "ENV"}
    dev = subprocess.run(  # noqa: S603
        [python, "-c", snippet],
        cwd=scratch,
        capture_output=True,
        text=True,
        env=dev_env,
    )
    assert dev.returncode != 0, "dev run should raise on the planted violation"
    assert "BeartypeCallHintParamViolation" in dev.stderr, dev.stderr

    # prod (ENV=prod): O0 no-op — the bad value passes straight through, exit 0.
    prod = subprocess.run(  # noqa: S603
        [python, "-c", snippet],
        cwd=scratch,
        capture_output=True,
        text=True,
        env={**dev_env, "ENV": "prod"},
    )
    assert prod.returncode == 0, prod.stderr
    assert prod.stdout.strip() == "x", prod.stdout
