# Copyright (c) 2026 Moiz
# SPDX-License-Identifier: MIT

"""Tests for harness.checks.web.check_web_api_client_fresh (web.api_client_fresh).

Covers (hermetic — the OpenAPI dump + openapi-typescript codegen subprocesses are
NEVER actually spawned; ``proc_run`` is monkeypatched to a fake that returns
canned stdout / writes canned TS):

- registry registration + spec metadata (tier=standard, category=contract,
  fixable=True, tool=openapi-typescript), no forbidden @register kwargs
- PLANTED FAILURE: regenerated TS differs from committed → fail with dotted code
  web.api_client_fresh.stale
- pass when regenerated TS is byte-identical to the committed golden
- skip when the dump reports IMPORT_ERROR (app not installed)
- skip when the local openapi-typescript bin is absent (offline-first)
- fail (codegen_failed) when openapi-typescript exits non-zero
- fail (missing_committed) when web/src/lib/api-types.ts is absent

The real end-to-end forcing function (render a has_web+has_backend scaffold →
mutate a Pydantic field → web.api_client_fresh goes RED → regen → GREEN) is
verified against a rendered scaffold during the verify-the-verifier step; these
hermetic tests guard the verdict-parsing + registration contract in CI without a
slow render+install run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._helpers import render_scratch_project

# api-types.ts is dual-gated on has_web AND has_backend, so the check only
# registers when both are true — render that combo from HEAD.


@pytest.fixture(scope="module")
def api_client_modules(tmp_path_factory: pytest.TempPathFactory):
    scratch = render_scratch_project(
        tmp_path_factory.mktemp("api-client-scratch"),
        _vcs_ref="HEAD",
        has_web=True,
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
        from harness.checks import web as web_mod

        yield registry, web_mod
    finally:
        sys.path.remove(str(scratch))
        for mod in list(sys.modules):
            if mod == "harness" or mod.startswith("harness."):
                del sys.modules[mod]


def _committed_golden(cwd: Path, contents: str) -> Path:
    """Write a committed web/src/lib/api-types.ts under cwd and return its path."""
    target = cwd / "web" / "src" / "lib" / "api-types.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(contents, encoding="utf-8")
    return target


def _install_bin(cwd: Path) -> None:
    """Materialize web/node_modules/.bin/openapi-typescript so the bin-guard passes."""
    bin_path = cwd / "web" / "node_modules" / ".bin" / "openapi-typescript"
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    bin_path.write_text("#!/bin/sh\n", encoding="utf-8")


def _fake_proc_factory(*, dump_stdout: str, regen_ts: str | None, codegen_rc: int = 0):
    """Build a proc_run double.

    The dump invocation (``uv run python -c <probe>``) returns ``dump_stdout``.
    The codegen invocation (``pnpm exec openapi-typescript <schema> -o <out>``)
    writes ``regen_ts`` to the ``-o`` target (when not None) and exits codegen_rc.
    """

    def _run(argv, **_kwargs):
        if "openapi-typescript" in argv:
            if regen_ts is not None and "-o" in argv:
                out = argv[argv.index("-o") + 1]
                Path(out).write_text(regen_ts, encoding="utf-8")
            return subprocess.CompletedProcess(
                args=argv, returncode=codegen_rc, stdout="", stderr="codegen boom"
            )
        # The OpenAPI dump probe.
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=dump_stdout, stderr=""
        )

    return _run


_SCHEMA = '{"openapi": "3.1.0", "paths": {}}'
_GOLDEN_TS = "export interface paths {}\n"


def test_api_client_fresh_registered(api_client_modules) -> None:
    registry, _ = api_client_modules
    ids = {s.check_id for s in registry.list_checks()}
    assert "web.api_client_fresh" in ids


def test_api_client_fresh_spec_metadata(api_client_modules) -> None:
    registry, _ = api_client_modules
    spec = registry.get_check("web.api_client_fresh")
    assert spec is not None
    assert spec.tier == "standard"
    assert spec.category == "contract"
    assert spec.fixable is True
    assert spec.tool == "openapi-typescript"


def test_api_client_fresh_no_forbidden_register_kwargs(api_client_modules) -> None:
    """REVIEW-CHECKLIST §4: the @register call must use no forbidden kwargs."""
    import re

    _, web_mod = api_client_modules
    src = Path(web_mod.__file__).read_text(encoding="utf-8")
    register_calls = re.findall(r"@register\((.*?)\)", src, re.DOTALL)
    for call_body in register_calls:
        for forbidden in ("severity=", "tags=", "readOnlyHint=", "destructiveHint="):
            assert forbidden not in call_body, (
                f"Found forbidden kwarg {forbidden!r} in a @register() call."
            )


def test_pass_when_regen_matches_committed(
    api_client_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, web_mod = api_client_modules
    spec = registry.get_check("web.api_client_fresh")
    _install_bin(tmp_path)
    _committed_golden(tmp_path, _GOLDEN_TS)
    monkeypatch.setattr(
        web_mod,
        "proc_run",
        _fake_proc_factory(dump_stdout=_SCHEMA, regen_ts=_GOLDEN_TS),
    )
    result = spec.fn(cwd=tmp_path)
    assert result.status == "pass", (
        f"matching TS should pass, got {result.status} / "
        f"{result.error.code if result.error else None}"
    )
    assert result.error is None


def test_stale_when_regen_differs(
    api_client_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PLANTED: regenerated TS gains a field the committed golden lacks → stale."""
    registry, web_mod = api_client_modules
    spec = registry.get_check("web.api_client_fresh")
    _install_bin(tmp_path)
    _committed_golden(tmp_path, _GOLDEN_TS)
    drifted = _GOLDEN_TS + "export interface components { schemas: { Extra: { x: string } } }\n"
    monkeypatch.setattr(
        web_mod,
        "proc_run",
        _fake_proc_factory(dump_stdout=_SCHEMA, regen_ts=drifted),
    )
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "web.api_client_fresh.stale"


def test_skip_when_app_not_importable(
    api_client_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, web_mod = api_client_modules
    spec = registry.get_check("web.api_client_fresh")
    _install_bin(tmp_path)
    _committed_golden(tmp_path, _GOLDEN_TS)
    monkeypatch.setattr(
        web_mod,
        "proc_run",
        _fake_proc_factory(dump_stdout="IMPORT_ERROR", regen_ts=None),
    )
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"


def test_skip_when_local_bin_absent(
    api_client_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No web/node_modules/.bin/openapi-typescript → skip, never fail."""
    registry, web_mod = api_client_modules
    spec = registry.get_check("web.api_client_fresh")
    # Deliberately do NOT install the bin.
    proc_called = {"v": False}

    def _fake(*_a, **_k):
        proc_called["v"] = True
        return subprocess.CompletedProcess(args=["x"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(web_mod, "proc_run", _fake)
    result = spec.fn(cwd=tmp_path)
    assert result.status == "skip"
    assert proc_called["v"] is False, "no subprocess should run when the bin is absent"


def test_codegen_failure_is_flagged(
    api_client_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, web_mod = api_client_modules
    spec = registry.get_check("web.api_client_fresh")
    _install_bin(tmp_path)
    _committed_golden(tmp_path, _GOLDEN_TS)
    monkeypatch.setattr(
        web_mod,
        "proc_run",
        _fake_proc_factory(dump_stdout=_SCHEMA, regen_ts=None, codegen_rc=1),
    )
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "web.api_client_fresh.codegen_failed"


def test_missing_committed_golden_is_flagged(
    api_client_modules, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, web_mod = api_client_modules
    spec = registry.get_check("web.api_client_fresh")
    _install_bin(tmp_path)
    # No _committed_golden call → web/src/lib/api-types.ts is absent.
    monkeypatch.setattr(
        web_mod,
        "proc_run",
        _fake_proc_factory(dump_stdout=_SCHEMA, regen_ts=_GOLDEN_TS),
    )
    result = spec.fn(cwd=tmp_path)
    assert result.status == "fail"
    assert result.error is not None
    assert result.error.code == "web.api_client_fresh.missing_committed"
