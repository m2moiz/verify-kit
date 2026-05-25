# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Logfire opt-in contract tests at the verify-kit repo level.

These tests render scratch projects and assert source-level properties of
the rendered app/main.py. They complement the scaffold-internal logfire
opt-in test at template/tests/backend/test_logfire_opt_in.py.jinja2 (which
runs INSIDE the rendered project once it boots).

Bead verify-kit-c5a (Phase 4 GAP-02): the rendered template must NOT call
``logfire.configure()`` unconditionally when has_logfire=True — calling it
without LOGFIRE_TOKEN set emits a noisy "no token" warning every cold
start. The template should wrap the configure call in an env-var guard so
the no-token path is silent.
"""
from __future__ import annotations

from pathlib import Path

from tests._helpers import render_scratch_project


def test_logfire_not_imported_when_has_logfire_false(tmp_path: Path) -> None:
    """has_backend=True, has_logfire=False: app/main.py must NOT mention logfire."""
    scratch = render_scratch_project(
        tmp_path,
        has_backend=True,
        has_logfire=False,
        has_fastapi_mcp=False,
        has_db=True,
    )
    main_py = (scratch / "app" / "main.py").read_text()
    assert "import logfire" not in main_py
    assert "logfire.configure" not in main_py


def test_logfire_token_guard_present_when_has_logfire_true(tmp_path: Path) -> None:
    """Bead verify-kit-c5a: when has_logfire=True the rendered app/main.py
    MUST wrap logfire.configure() in a LOGFIRE_TOKEN env-var guard so that
    the no-token cold-start path is silent (no noisy "send_to_logfire"
    warning on import).

    Accepted shapes (any ONE must be present):
      (a) explicit if-token guard around configure():
            if os.environ.get("LOGFIRE_TOKEN"):
                logfire.configure()
            else:
                logfire.configure(send_to_logfire=False)
      (b) configure() always called with send_to_logfire=False fallback
          AND a LOGFIRE_TOKEN check on the conditional branch.

    The contract: LOGFIRE_TOKEN appears, os.environ.get / os.getenv reads
    it, and send_to_logfire=False appears as the fallback.
    """
    scratch = render_scratch_project(
        tmp_path,
        has_backend=True,
        has_logfire=True,
        has_fastapi_mcp=False,
        has_db=True,
    )
    main_py = (scratch / "app" / "main.py").read_text()

    # Sanity: logfire is wired in at all.
    assert "import logfire" in main_py, (
        "expected 'import logfire' in rendered app/main.py when has_logfire=True"
    )
    assert "logfire.configure" in main_py, (
        "expected logfire.configure(...) call in rendered app/main.py"
    )

    # Bead c5a contract: env-var guard pattern.
    assert "LOGFIRE_TOKEN" in main_py, (
        "LOGFIRE_TOKEN env var name missing from rendered app/main.py — "
        "logfire.configure() is being called unconditionally; that emits a "
        "noisy 'no token' warning on every cold start when the user hasn't "
        "set up Logfire yet."
    )
    has_env_read = (
        'os.environ.get("LOGFIRE_TOKEN")' in main_py
        or "os.environ.get('LOGFIRE_TOKEN')" in main_py
        or 'os.getenv("LOGFIRE_TOKEN")' in main_py
        or "os.getenv('LOGFIRE_TOKEN')" in main_py
    )
    assert has_env_read, (
        "LOGFIRE_TOKEN env-var READ missing (os.environ.get / os.getenv) — "
        "the token must be read at runtime, not import-time only."
    )
    assert "send_to_logfire=False" in main_py, (
        "send_to_logfire=False fallback missing — the no-token branch must "
        "explicitly disable network shipping so logfire emits no warning."
    )
