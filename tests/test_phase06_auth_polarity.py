# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Phase 6 auth-scaffold polarity tests (Plan 06-02).

Forcing-function tests that lock the auth contract:
- Root .env.example carries the VERIFYKIT_AUTH_TOKEN slot (NOT app/.env.example).
- require_auth gates every route except /healthz (in-dependency path short-circuit).
- Dev fallback allows missing token when ENV=dev; non-dev returns 503.
- Mismatched header returns 401; matching header returns 200.
- has_backend=false renders ship no app/ directory.

Lives at repo top-level per REVIEW-CHECKLIST §7 (avoids harness recursion).
All scratch subprocesses pass env=_CLEAN_ENV per REVIEW-CHECKLIST §8.
"""
from __future__ import annotations

import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tests._helpers import _CLEAN_ENV, render_scratch_project

# Forbidden internal planning identifiers that must never leak into rendered
# consumer-facing template output (REVIEW-CHECKLIST Pattern 6).
_FORBIDDEN_META_IDS = [
    r"\bD-1[0-9]\b",
    r"verify-kit-[a-z0-9]{3}",
    r"\bPlan 06-0[0-9]\b",
    r"\bPhase 6\b",
    r"cycle-[0-9]",
    r"Codex HIGH",
]

_BASE: dict[str, object] = {
    "project_name": "PolarityP6",
    "project_description": "phase 6 auth polarity test",
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


def _render(tmp_path: Path, *, has_backend: bool, has_llm: bool = False,
            llm_backend: str = "none") -> Path:
    return render_scratch_project(
        tmp_path,
        **{
            **_BASE,
            "has_backend": has_backend,
            "has_llm": has_llm,
            "llm_backend": llm_backend,
        },  # type: ignore[arg-type]
    )


# ── Render-shape assertions ───────────────────────────────────────────────────


def test_has_backend_false_has_no_app_dir(tmp_path: Path) -> None:
    """has_backend=false polarity: no app/ directory, no backend root .env.example."""
    scratch = _render(tmp_path, has_backend=False, has_llm=False)
    assert not (scratch / "app").exists()
    # The new root .env.example is gated has_backend; absent under has_backend=false.
    assert not (scratch / ".env.example").exists()


@pytest.mark.parametrize("has_llm", [False, True])
def test_root_env_example_contains_auth_slot(tmp_path: Path, has_llm: bool) -> None:
    """Test 1 + 1d: ROOT .env.example exists with VERIFYKIT_AUTH_TOKEN slot,
    across both backend cells (has_llm in {False, True}).
    Catches the copier.yml _exclude regression class (cycle-6).
    """
    scratch = _render(
        tmp_path,
        has_backend=True,
        has_llm=has_llm,
        llm_backend="langfuse-cloud" if has_llm else "none",
    )
    root_env = scratch / ".env.example"
    assert root_env.exists(), f"root .env.example missing for has_llm={has_llm}"
    text = root_env.read_text()
    assert "VERIFYKIT_AUTH_TOKEN=" in text


def test_root_env_example_has_no_planning_meta_ids(tmp_path: Path) -> None:
    """Test 1b: ROOT .env.example must not leak internal planning IDs
    (REVIEW-CHECKLIST Pattern 6 forcing function)."""
    scratch = _render(tmp_path, has_backend=True, has_llm=False)
    text = (scratch / ".env.example").read_text()
    for pat in _FORBIDDEN_META_IDS:
        assert not re.search(pat, text), (
            f"forbidden planning identifier matching /{pat}/ leaked into root .env.example"
        )


def test_auth_slot_not_at_wrong_path(tmp_path: Path) -> None:
    """Negative assertion: VERIFYKIT_AUTH_TOKEN must NOT live under app/.env.example
    (Settings.load(cwd) reads cwd/.env, not cwd/app/.env)."""
    scratch = _render(tmp_path, has_backend=True, has_llm=False)
    app_env = scratch / "app" / ".env.example"
    if app_env.exists():
        assert "VERIFYKIT_AUTH_TOKEN" not in app_env.read_text(), (
            "auth slot must NOT live at app/.env.example — runtime loader reads root"
        )


def test_main_py_wires_global_dependency(tmp_path: Path) -> None:
    """Producer-contract test: rendered app/main.py registers require_auth globally."""
    scratch = _render(tmp_path, has_backend=True, has_llm=False)
    main = (scratch / "app" / "main.py").read_text()
    assert "from app.auth import require_auth" in main
    assert re.search(
        r"FastAPI\([^)]*dependencies\s*=\s*\[\s*Depends\(require_auth\)\s*\]",
        main,
        re.DOTALL,
    ), "global FastAPI(dependencies=[Depends(require_auth)]) not wired"


def test_auth_module_uses_canonical_primitives(tmp_path: Path) -> None:
    """Producer-contract test: app/auth.py uses APIKeyHeader + compare_digest
    + reads settings via request.app.state.settings + has in-dependency /healthz
    short-circuit."""
    scratch = _render(tmp_path, has_backend=True, has_llm=False)
    auth = (scratch / "app" / "auth.py").read_text()
    assert "X-VerifyKit-Token" in auth
    assert "APIKeyHeader" in auth
    assert "auto_error=False" in auth
    assert "secrets.compare_digest" in auth
    assert "request.app.state.settings" in auth
    assert "/healthz" in auth and "request.url.path" in auth


# ── Runtime behavior assertions (subprocess against scratch project) ──────────


def _build_runtime_script(scratch: Path) -> str:
    """Build the in-process Python script the subprocess executes inside the
    scratch project. Uses create_app(cwd=scratch) and TestClient as a context
    manager to trigger the lifespan (binds app.state.settings)."""
    return textwrap.dedent(f"""
        import sys, json
        from pathlib import Path
        from fastapi.testclient import TestClient
        from app.main import create_app

        scratch = Path({str(scratch)!r})
        application = create_app(cwd=scratch)
        with TestClient(application) as client:
            results = {{}}
            # /healthz must be reachable regardless of token state
            results["healthz"] = client.get("/healthz").status_code
            # /echo behavior depends on env state
            results["echo_no_header"] = client.post(
                "/echo", json={{"message": "hi"}}
            ).status_code
            results["echo_with_header"] = client.post(
                "/echo",
                json={{"message": "hi"}},
                headers={{"X-VerifyKit-Token": "dev-token"}},
            ).status_code
            results["echo_wrong_header"] = client.post(
                "/echo",
                json={{"message": "hi"}},
                headers={{"X-VerifyKit-Token": "WRONG"}},
            ).status_code
            print(json.dumps(results))
    """).strip()


def _run_scratch(scratch: Path, env_file: str, extra_env: dict[str, str]) -> dict[str, int]:
    """Write the .env file at scratch root, then invoke the runtime script in a
    subprocess with a clean env merged with extra_env."""
    (scratch / ".env").write_text(env_file)
    script = _build_runtime_script(scratch)
    env = {**_CLEAN_ENV, **extra_env}
    r = subprocess.run(
        ["uv", "run", "--project", str(scratch), "python", "-c", script],
        cwd=scratch,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if r.returncode != 0:
        raise AssertionError(
            f"scratch runtime script failed (rc={r.returncode}):\n"
            f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )
    import json
    # The last line should be the JSON; tolerate noise from uv before it.
    last_json_line = None
    for ln in r.stdout.splitlines():
        ln = ln.strip()
        if ln.startswith("{") and ln.endswith("}"):
            last_json_line = ln
    assert last_json_line, f"no JSON result in stdout:\n{r.stdout}"
    return json.loads(last_json_line)


@pytest.fixture(scope="module")
def scratch_backend(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render once per module and install the scratch venv. Reused across
    runtime test cases — they only differ by .env contents + env vars."""
    tmp = tmp_path_factory.mktemp("p6-auth-rt")
    scratch = _render(tmp, has_backend=True, has_llm=False)
    # Install scratch venv so `uv run` inside the subprocess resolves deps.
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
        timeout=300,
    )
    return scratch


def test_runtime_dev_no_token_allows(scratch_backend: Path) -> None:
    """Test 4 (dev,no,no)→200: dev fallback when token unset."""
    res = _run_scratch(
        scratch_backend,
        env_file="ENV=dev\n",
        extra_env={"ENV": "dev"},
    )
    assert res["healthz"] == 200
    assert res["echo_no_header"] == 200, "dev fallback should allow when token unset"


def test_runtime_prod_no_token_returns_503(scratch_backend: Path) -> None:
    """Test 4 (prod,no,no)→503: non-dev with unset token is config error."""
    res = _run_scratch(
        scratch_backend,
        env_file="ENV=prod\n",
        extra_env={"ENV": "prod"},
    )
    assert res["healthz"] == 200, "/healthz must be reachable even in misconfigured prod"
    assert res["echo_no_header"] == 503
    assert res["echo_with_header"] == 503, "503 (config error) precedes 401 (auth)"


def test_runtime_dev_with_token(scratch_backend: Path) -> None:
    """Test 4 (dev,yes,no)→401 + (dev,yes,yes)→200."""
    res = _run_scratch(
        scratch_backend,
        env_file="ENV=dev\nVERIFYKIT_AUTH_TOKEN=dev-token\n",
        extra_env={"ENV": "dev", "VERIFYKIT_AUTH_TOKEN": "dev-token"},
    )
    assert res["healthz"] == 200, "/healthz exempt regardless"
    assert res["echo_no_header"] == 401, "missing header with token configured → 401"
    assert res["echo_wrong_header"] == 401, "wrong header → 401"
    assert res["echo_with_header"] == 200, "matching header → 200"


def test_runtime_loader_reads_root_env_file(scratch_backend: Path) -> None:
    """Test 1c: copy .env.example → .env at scratch root, then verify
    Settings.load(scratch).VERIFYKIT_AUTH_TOKEN matches the file contents.
    Catches the env-example-at-wrong-path bug class (cycle-5)."""
    src = scratch_backend / ".env.example"
    assert src.exists()
    # Overwrite the example value so we can detect the loader actually read it
    text = src.read_text().replace("VERIFYKIT_AUTH_TOKEN=", "VERIFYKIT_AUTH_TOKEN=loader-probe-token")
    (scratch_backend / ".env").write_text(text)
    script = textwrap.dedent(f"""
        from pathlib import Path
        from app.settings import load
        s = load(Path({str(scratch_backend)!r}))
        print(s.VERIFYKIT_AUTH_TOKEN)
    """).strip()
    r = subprocess.run(
        ["uv", "run", "--project", str(scratch_backend), "python", "-c", script],
        cwd=scratch_backend,
        env=_CLEAN_ENV,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, f"loader probe failed:\nSTDOUT:{r.stdout}\nSTDERR:{r.stderr}"
    assert "loader-probe-token" in r.stdout, (
        f"Settings.load(cwd) did not pick up cwd/.env — got: {r.stdout!r}"
    )
