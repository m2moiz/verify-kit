"""
Tests for `template/harness/observability.py.jinja2` (Plan 02-02 Task 1).

Verifies:
- (a) `tracer` is `_NullTracer`-shaped when OTEL_EXPORTER_OTLP_ENDPOINT is unset.
- (b) The span context-manager pattern works as a no-op (set_attribute,
  record_exception, set_status return None and don't raise).
- (c) `shutdown()` is callable in both states.
- (d) `force_flush()` is callable in both states.
- (e) IMPORT-TIME GATE (OBS-01 / Decision 3.1): subprocess `python -X importtime
  -c "import harness.observability"` with OTEL_EXPORTER_OTLP_ENDPOINT cleared
  produces ZERO `opentelemetry` lines on stderr.
- (f) When OTEL_EXPORTER_OTLP_ENDPOINT is set, `tracer` is a real OTel tracer
  and `_otel_enabled` is True.

Strategy: render the template once (session-scoped) and install OTel deps into
the scratch project's venv, then run all behavioural assertions inside subprocess
shells so each call gets a clean import state for env-var dispatch.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from _helpers import _REPO_ROOT, _DEFAULT_ANSWERS  # type: ignore[attr-defined]
from copier import run_copy


# Pinned per Plan 02-02 must-haves and RESEARCH.md §12.
_OTEL_DEPS = [
    "opentelemetry-api==1.41.1",
    "opentelemetry-sdk==1.41.1",
    "opentelemetry-exporter-otlp-proto-grpc==1.41.1",
    "structlog>=25",
]


def _have_uv() -> bool:
    return shutil.which("uv") is not None


@pytest.fixture(scope="module")
def installed_scratch(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render the template, install harness + OTel deps into a project venv."""
    if not _have_uv():
        pytest.skip("uv binary not available")

    tmp = tmp_path_factory.mktemp("p2-obs")

    # Copy the template to a clean source dir, excluding noise that breaks
    # Copier's git-submodule walk (Claude Code worktrees under .claude/ have
    # gitfiles that git treats as gitlinks — see Rule-3 environment fix).
    clean_src = tmp / "src"
    def _ignore(_dir: str, names: list[str]) -> list[str]:
        skip = {".claude", ".venv", ".pytest_cache", ".ruff_cache",
                "__pycache__", "node_modules", ".planning"}
        return [n for n in names if n in skip]
    shutil.copytree(_REPO_ROOT, clean_src, ignore=_ignore, dirs_exist_ok=False)

    scratch = tmp / "scratch"
    run_copy(
        src_path=str(clean_src),
        dst_path=str(scratch),
        data=dict(_DEFAULT_ANSWERS),
        defaults=True,
        unsafe=True,
        quiet=True,
        vcs_ref="HEAD",
    )

    # Plan 02-01 (parallel) creates harness/trace_id.py. Until it merges, stub it
    # so harness.logging's lazy `from harness.trace_id import get_trace_id` works
    # when other tests in this suite (logging) trigger it. Observability does NOT
    # depend on trace_id, but a co-installed scratch must still import cleanly.
    trace_id_path = scratch / "harness" / "trace_id.py"
    if not trace_id_path.exists():
        trace_id_path.write_text(
            textwrap.dedent(
                """\
                \"\"\"Stub trace_id module for tests when Plan 02-01 has not merged yet.\"\"\"
                from __future__ import annotations
                def get_trace_id() -> str | None:
                    return None
                """
            )
        )

    # Create an isolated venv inside the scratch project.
    venv = scratch / ".venv"
    subprocess.run(
        ["uv", "venv", str(venv)], cwd=scratch, check=True, capture_output=True
    )
    # Install the rendered harness package + OTel + structlog into the venv.
    env = {**os.environ, "VIRTUAL_ENV": str(venv)}
    subprocess.run(
        ["uv", "pip", "install", "-e", ".", *_OTEL_DEPS],
        cwd=scratch,
        check=True,
        env=env,
        capture_output=True,
    )
    return scratch


def _venv_python(scratch: Path) -> str:
    return str(scratch / ".venv" / "bin" / "python")


def _run_in_venv(
    scratch: Path, code: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [_venv_python(scratch), "-c", code],
        cwd=scratch,
        env=env,
        capture_output=True,
        text=True,
    )


def test_tracer_is_null_when_env_unset(installed_scratch: Path) -> None:
    """With OTEL_EXPORTER_OTLP_ENDPOINT unset, tracer is _NullTracer-shaped."""
    code = textwrap.dedent(
        """
        from harness import observability as obs
        assert obs._otel_enabled is False, obs._otel_enabled
        assert type(obs.tracer).__name__ == "_NullTracer"
        with obs.tracer.start_as_current_span("x") as span:
            span.set_attribute("k", "v")
            span.record_exception(RuntimeError("hi"))
            span.set_status("ok")
        print("OK")
        """
    )
    cp = _run_in_venv(installed_scratch, code)
    assert cp.returncode == 0, f"stdout={cp.stdout!r} stderr={cp.stderr!r}"
    assert "OK" in cp.stdout


def test_shutdown_and_force_flush_callable_when_disabled(installed_scratch: Path) -> None:
    code = textwrap.dedent(
        """
        from harness import observability as obs
        obs.shutdown()
        assert obs.force_flush() is True
        assert obs.force_flush(timeout_millis=500) is True
        print("OK")
        """
    )
    cp = _run_in_venv(installed_scratch, code)
    assert cp.returncode == 0, f"stdout={cp.stdout!r} stderr={cp.stderr!r}"
    assert "OK" in cp.stdout


def test_zero_opentelemetry_imports_when_disabled(installed_scratch: Path) -> None:
    """OBS-01 verification gate (Decision 3.1).

    Running `python -X importtime -c "import harness.observability"` with
    OTEL_EXPORTER_OTLP_ENDPOINT unset MUST NOT cause any `opentelemetry.*`
    module to be imported.
    """
    env = {k: v for k, v in os.environ.items() if k != "OTEL_EXPORTER_OTLP_ENDPOINT"}
    cp = subprocess.run(
        [
            _venv_python(installed_scratch),
            "-X",
            "importtime",
            "-c",
            "import harness.observability",
        ],
        cwd=installed_scratch,
        env=env,
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, f"stderr={cp.stderr!r}"
    # `python -X importtime` writes to stderr. Count any line referencing the
    # opentelemetry namespace — there should be zero when the gate is closed.
    otel_lines = [
        ln for ln in cp.stderr.splitlines() if "opentelemetry" in ln.lower()
    ]
    assert otel_lines == [], (
        "OBS-01 GATE FAILED: opentelemetry was imported at module load with "
        f"OTEL_EXPORTER_OTLP_ENDPOINT unset.\nOffending lines:\n"
        + "\n".join(otel_lines)
    )


def test_tracer_is_real_when_env_set(installed_scratch: Path) -> None:
    """When OTEL_EXPORTER_OTLP_ENDPOINT is set, tracer is a real OTel tracer.

    We don't run an exporter; setting the env var just needs to flip the gate
    and construct the provider. BatchSpanProcessor is async and won't crash
    even if the endpoint isn't reachable until shutdown/flush.
    """
    code = textwrap.dedent(
        """
        from harness import observability as obs
        assert obs._otel_enabled is True
        assert type(obs.tracer).__name__ != "_NullTracer"
        # Real OTel tracer accepts span ops without erroring.
        with obs.tracer.start_as_current_span("test-span") as span:
            span.set_attribute("k", "v")
        # force_flush is safe to call (returns bool from OTel API).
        result = obs.force_flush(timeout_millis=100)
        assert isinstance(result, bool)
        # shutdown tears down the provider.
        obs.shutdown()
        print("OK")
        """
    )
    cp = _run_in_venv(
        installed_scratch,
        code,
        extra_env={"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"},
    )
    assert cp.returncode == 0, f"stdout={cp.stdout!r} stderr={cp.stderr!r}"
    assert "OK" in cp.stdout


def test_all_exports(installed_scratch: Path) -> None:
    """__all__ should expose tracer, shutdown, force_flush, _otel_enabled."""
    code = textwrap.dedent(
        """
        from harness import observability as obs
        expected = {"tracer", "shutdown", "force_flush", "_otel_enabled"}
        assert expected.issubset(set(obs.__all__)), obs.__all__
        print("OK")
        """
    )
    cp = _run_in_venv(installed_scratch, code)
    assert cp.returncode == 0, f"stdout={cp.stdout!r} stderr={cp.stderr!r}"
    assert "OK" in cp.stdout
