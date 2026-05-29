# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Surrogate-safe 422 handler polarity tests (Lane A).

A schema-INVALID request body can carry a lone surrogate (e.g. "\\ud800"), which
is not UTF-8 encodable. FastAPI's *default* RequestValidationError handler echoes
the offending input via ``jsonable_encoder(exc.errors())``; Starlette's
JSONResponse then does ``.encode("utf-8")``, which raises UnicodeEncodeError on
the surrogate — turning a 422 into an uncaught 500. A fuzzer (schemathesis) hits
this on any validated route.

The fix (app/main.py): a global ``@app.exception_handler(RequestValidationError)``
that runs the echoed errors through ``_strip_surrogates`` (replace -> U+FFFD)
before serialization, keeping the response a clean 422 on every backend combo.

Companion field-level strips (app/models.py EchoRequest, app/api.py
SummarizeRequest) add ``.encode("utf-8", "ignore").decode()`` to the existing
control-char strip. NOTE (verified empirically): pydantic v2's ``str`` core type
*itself* rejects a lone surrogate (``type=string_unicode``) BEFORE an after-mode
``@field_validator`` runs, so for lone surrogates the global handler is the
load-bearing fix and the field strip is a defensive idiom matching papertrail-ref
(idempotent on clean input). The field strip is still asserted present as a
forcing function so the papertrail-ref STRIP idiom does not silently regress.

Static assertions render with has_backend (the global handler is unconditional)
and additionally with has_llm=True to cover the /summarize validator.

The runtime test reconstructs the pre-fix behaviour by popping the registered
RequestValidationError handler off the rendered app (restoring FastAPI's default)
and asserts RED=500 -> GREEN=422 on the SAME rendered ``create_app`` — so the test
proves the mechanism, not just a string match.

Lives at tests/ top-level per REVIEW-CHECKLIST §7 (avoids harness recursion).
All scratch subprocesses pass env=_CLEAN_ENV per REVIEW-CHECKLIST §8.
"""
from __future__ import annotations

import re
import subprocess
import textwrap
from pathlib import Path

import pytest

from tests._helpers import _CLEAN_ENV, render_scratch_project

_BASE: dict[str, object] = {
    "project_name": "PolaritySurrogate",
    "project_description": "surrogate-safe 422 handler polarity test",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "license": "MIT",
    "has_claude_code": False,
    "has_cursor": False,
    "has_windsurf": False,
    "has_copilot": False,
    "has_zed": False,
    "has_continue": False,
    "has_devcontainer": False,
    "has_db": False,
    "has_logfire": False,
    "has_fastapi_mcp": False,
}


def _render(tmp_path: Path, *, has_llm: bool) -> Path:
    # vcs_ref="HEAD" so the render includes Lane A's uncommitted/post-tag edits
    # (mirrors the Phase 7+ convention documented in tests/_helpers.py).
    return render_scratch_project(
        tmp_path,
        _vcs_ref="HEAD",
        **{
            **_BASE,
            "has_backend": True,
            "has_llm": has_llm,
            "llm_backend": "langfuse-cloud" if has_llm else "none",
        },  # type: ignore[arg-type]
    )


# ── Static template-shape assertions ─────────────────────────────────────────


def test_rendered_main_has_global_surrogate_handler(tmp_path: Path) -> None:
    """Rendered app/main.py registers the surrogate-safe RequestValidationError
    handler unconditionally (no has_llm / has_db gate on the handler itself)."""
    scratch = _render(tmp_path, has_llm=False)
    main = (scratch / "app" / "main.py").read_text()

    # Imports the handler needs.
    assert "from fastapi.encoders import jsonable_encoder" in main
    assert "from fastapi.exceptions import RequestValidationError" in main
    assert re.search(r"from fastapi\.responses import .*\bJSONResponse\b", main), (
        "JSONResponse must be imported for the 422 handler"
    )

    # The recursive sanitizer + the handler registration.
    assert "def _strip_surrogates(" in main
    assert re.search(
        r"@app\.exception_handler\(\s*RequestValidationError\s*\)", main
    ), "global RequestValidationError handler must be registered"
    assert "_strip_surrogates(jsonable_encoder(exc.errors()))" in main, (
        "handler must sanitize the echoed validation errors before serialization"
    )
    # Sanitizer uses the papertrail-ref 'replace' strategy (U+FFFD), not 'ignore'.
    assert 'encode("utf-8", "replace")' in main


def test_rendered_models_field_strip_drops_surrogates(tmp_path: Path) -> None:
    """EchoRequest's validator adds the lone-surrogate strip to the existing
    control-char strip (papertrail-ref STRIP idiom)."""
    scratch = _render(tmp_path, has_llm=False)
    models = (scratch / "app" / "models.py").read_text()
    assert "_CONTROL_CHARS_ECHO" in models  # control-char strip preserved
    assert 'encode("utf-8", "ignore").decode("utf-8")' in models, (
        "EchoRequest validator must drop lone surrogates via encode(ignore)"
    )


def test_rendered_summarize_field_strip_drops_surrogates(tmp_path: Path) -> None:
    """SummarizeRequest's validator (has_llm only) also drops lone surrogates,
    layered before the injection-marker denylist."""
    scratch = _render(tmp_path, has_llm=True)
    api = (scratch / "app" / "api.py").read_text()
    assert "_INJECTION_MARKERS" in api  # denylist preserved
    assert 'encode("utf-8", "ignore").decode("utf-8")' in api, (
        "SummarizeRequest validator must drop lone surrogates via encode(ignore)"
    )


# ── Runtime behaviour: RED (default handler) -> GREEN (fix) on rendered app ───


@pytest.fixture(scope="module")
def scratch_backend(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render once + install scratch venv. Reused across runtime assertions."""
    tmp = tmp_path_factory.mktemp("surrogate-rt")
    scratch = _render(tmp, has_llm=False)
    subprocess.run(
        ["uv", "venv", "--python", "3.13"],
        cwd=scratch,
        check=True,
        env=_CLEAN_ENV,
        capture_output=True,
    )
    subprocess.run(
        ["uv", "sync", "--no-dev"],
        cwd=scratch,
        check=True,
        env=_CLEAN_ENV,
        capture_output=True,
        timeout=600,
    )
    return scratch


def _runtime_script(scratch: Path) -> str:
    return textwrap.dedent(f"""
        import json
        from pathlib import Path
        from app.main import create_app
        from app.auth import require_auth
        from fastapi.exceptions import RequestValidationError
        from fastapi.testclient import TestClient

        scratch = Path({str(scratch)!r})
        (scratch / ".env").write_text("ENV=dev\\nPROFILE_ENABLED=true\\n")
        (scratch / ".verify").mkdir(exist_ok=True)

        # Schema-INVALID body (exceeds max_length=5000) carrying a lone surrogate,
        # sent as RAW bytes (the way a fuzzer sends it — surrogatepass-encoded).
        bad = "\\ud800" + ("A" * 5001)
        raw = json.dumps({{"message": bad}}).encode("utf-8", "surrogatepass")
        headers = {{"Content-Type": "application/json"}}

        # GREEN: fix as shipped.
        app_green = create_app(cwd=scratch)
        app_green.dependency_overrides[require_auth] = lambda: None
        with TestClient(app_green, raise_server_exceptions=False) as c:
            green = c.post("/echo", content=raw, headers=headers).status_code

        # RED: pop the registered handler to restore FastAPI's default handler,
        # reproducing the pre-fix 500 on the SAME rendered create_app.
        app_red = create_app(cwd=scratch)
        app_red.dependency_overrides[require_auth] = lambda: None
        app_red.exception_handlers.pop(RequestValidationError, None)
        with TestClient(app_red, raise_server_exceptions=False) as c:
            red = c.post("/echo", content=raw, headers=headers).status_code

        print(json.dumps({{"red_default": red, "green_fix": green}}))
    """).strip()


def test_surrogate_invalid_body_is_clean_422_not_500(scratch_backend: Path) -> None:
    """A lone-surrogate, schema-invalid body returns 500 with FastAPI's default
    handler (RED) and a clean 422 with the shipped surrogate-safe handler (GREEN)."""
    script = _runtime_script(scratch_backend)
    r = subprocess.run(
        ["uv", "run", "--no-dev", "python", "-c", script],
        cwd=scratch_backend,
        env=_CLEAN_ENV,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, f"scratch runtime failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    import json

    result = next(
        json.loads(ln.strip())
        for ln in r.stdout.splitlines()
        if ln.strip().startswith("{") and ln.strip().endswith("}")
    )
    assert result["red_default"] == 500, (
        f"default RequestValidationError handler must 500 on a lone surrogate, got {result}"
    )
    assert result["green_fix"] == 422, (
        f"surrogate-safe handler must return a clean 422, got {result}"
    )
