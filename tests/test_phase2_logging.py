"""
Tests for `template/harness/logging.py.jinja2` (Plan 02-02 Task 2).

Verifies three-way structlog renderer dispatch (HARN-05) per the six env-var
permutations in PLAN 02-02 Task 2 <behavior>:

1. CI=1                          → JSONRenderer
2. LOG_FORMAT=json               → JSONRenderer
3. stderr not a TTY (pipe)       → JSONRenderer
4. TTY, no NO_COLOR, no CI       → ConsoleRenderer (colored)
5. TTY, NO_COLOR=1               → KeyValueRenderer (plain structured)
6. log.info(...) after configure → does not raise; LOG_LEVEL respected

Strategy: render the template once (module-scoped), install harness + structlog
into a venv, then run each renderer-selection assertion in its own subprocess
so the env-var dispatch path is exercised at import-time per call.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from _helpers import _DEFAULT_ANSWERS, _REPO_ROOT  # type: ignore[attr-defined]
from copier import run_copy


_DEPS = [
    "structlog>=25",
    # Observability is imported transitively only if something imports it; we
    # don't install OTel here to keep this suite fast and focused.
]


def _have_uv() -> bool:
    return shutil.which("uv") is not None


@pytest.fixture(scope="module")
def installed_scratch(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not _have_uv():
        pytest.skip("uv binary not available")
    tmp = tmp_path_factory.mktemp("p2-log")

    clean_src = tmp / "src"

    def _ignore(_d: str, names: list[str]) -> list[str]:
        skip = {".claude", ".venv", ".pytest_cache", ".ruff_cache",
                "__pycache__", "node_modules", ".planning"}
        return [n for n in names if n in skip]

    shutil.copytree(_REPO_ROOT, clean_src, ignore=_ignore)

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

    # Stub trace_id (Plan 02-01) until that plan merges. harness.logging does
    # `from harness.trace_id import get_trace_id` lazily inside its processor —
    # so the stub must exist or the processor will raise on first log call.
    trace_id_path = scratch / "harness" / "trace_id.py"
    if not trace_id_path.exists():
        trace_id_path.write_text(
            textwrap.dedent(
                """\
                \"\"\"Stub trace_id for Plan 02-02 tests (Plan 02-01 owns the real one).\"\"\"
                from __future__ import annotations
                def get_trace_id() -> str | None:
                    return None
                """
            )
        )

    venv = scratch / ".venv"
    subprocess.run(["uv", "venv", str(venv)], cwd=scratch, check=True, capture_output=True)
    env = {**os.environ, "VIRTUAL_ENV": str(venv)}
    subprocess.run(
        ["uv", "pip", "install", "-e", ".", *_DEPS],
        cwd=scratch,
        check=True,
        env=env,
        capture_output=True,
    )
    return scratch


def _python(scratch: Path) -> str:
    return str(scratch / ".venv" / "bin" / "python")


def _run(
    scratch: Path,
    code: str,
    env_overrides: dict[str, str] | None = None,
    env_unset: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    # Strip CI/LOG_FORMAT/NO_COLOR/LOG_LEVEL from inheriting env so each test
    # gets a deterministic baseline.
    base = {
        k: v
        for k, v in os.environ.items()
        if k not in {"CI", "LOG_FORMAT", "NO_COLOR", "LOG_LEVEL"} and k not in env_unset
    }
    if env_overrides:
        base.update(env_overrides)
    return subprocess.run(
        [_python(scratch), "-c", code],
        cwd=scratch,
        env=base,
        capture_output=True,
        text=True,
    )


# ── Renderer-dispatch helper ────────────────────────────────────────────────

# Each test forces sys.stderr.isatty() to a known value before
# configure_logging() runs, then inspects which renderer was installed.
# structlog stores the configured processor chain on its global config; we
# read the last processor (the renderer) and assert its class name.

_DISPATCH_PROBE = textwrap.dedent(
    """
    import sys
    # Force isatty to a deterministic value BEFORE harness.logging is imported.
    class _FakeStderr:
        def __init__(self, real, is_tty):
            self._real = real
            self._is_tty = is_tty
        def __getattr__(self, n):
            return getattr(self._real, n)
        def isatty(self):
            return self._is_tty
    sys.stderr = _FakeStderr(sys.stderr, {is_tty})

    from harness.logging import configure_logging
    configure_logging()

    import structlog
    cfg = structlog.get_config()
    renderer = cfg["processors"][-1]
    print(type(renderer).__name__)
    """
)


def test_ci_env_selects_json(installed_scratch: Path) -> None:
    cp = _run(
        installed_scratch,
        _DISPATCH_PROBE.format(is_tty=True),
        env_overrides={"CI": "1"},
    )
    assert cp.returncode == 0, cp.stderr
    assert cp.stdout.strip() == "JSONRenderer"


def test_log_format_json_selects_json(installed_scratch: Path) -> None:
    cp = _run(
        installed_scratch,
        _DISPATCH_PROBE.format(is_tty=True),
        env_overrides={"LOG_FORMAT": "json"},
    )
    assert cp.returncode == 0, cp.stderr
    assert cp.stdout.strip() == "JSONRenderer"


def test_pipe_selects_json(installed_scratch: Path) -> None:
    cp = _run(installed_scratch, _DISPATCH_PROBE.format(is_tty=False))
    assert cp.returncode == 0, cp.stderr
    assert cp.stdout.strip() == "JSONRenderer"


def test_tty_no_color_no_ci_selects_console(installed_scratch: Path) -> None:
    cp = _run(installed_scratch, _DISPATCH_PROBE.format(is_tty=True))
    assert cp.returncode == 0, cp.stderr
    assert cp.stdout.strip() == "ConsoleRenderer"


def test_tty_no_color_selects_keyvalue(installed_scratch: Path) -> None:
    cp = _run(
        installed_scratch,
        _DISPATCH_PROBE.format(is_tty=True),
        env_overrides={"NO_COLOR": "1"},
    )
    assert cp.returncode == 0, cp.stderr
    assert cp.stdout.strip() == "KeyValueRenderer"


def test_log_call_does_not_raise(installed_scratch: Path) -> None:
    code = textwrap.dedent(
        """
        from harness.logging import configure_logging, log
        configure_logging()
        log.info("hello", kind="test")
        log.warning("warned")
        log.error("err")
        print("OK")
        """
    )
    cp = _run(installed_scratch, code)
    assert cp.returncode == 0, cp.stderr
    assert "OK" in cp.stdout


def test_log_level_threshold_respected(installed_scratch: Path) -> None:
    """LOG_LEVEL=ERROR must drop info-level events."""
    code = textwrap.dedent(
        """
        import sys
        from harness.logging import configure_logging, log
        configure_logging()
        # default is WARNING — info should be dropped, error should print.
        log.info("dropped")
        log.error("kept")
        """
    )
    cp = _run(installed_scratch, code, env_overrides={"LOG_LEVEL": "ERROR"})
    assert cp.returncode == 0, cp.stderr
    assert "dropped" not in cp.stderr
    assert "kept" in cp.stderr


def test_log_is_canonical_export(installed_scratch: Path) -> None:
    code = textwrap.dedent(
        """
        from harness import logging as hl
        assert "configure_logging" in hl.__all__
        assert "log" in hl.__all__
        import structlog
        # log must be a BoundLoggerLazyProxy or similar structlog logger
        assert hasattr(hl.log, "info") and hasattr(hl.log, "bind")
        print("OK")
        """
    )
    cp = _run(installed_scratch, code)
    assert cp.returncode == 0, cp.stderr
    assert "OK" in cp.stdout


def test_trace_id_processor_runs(installed_scratch: Path) -> None:
    """The _add_trace_id processor must be in the chain and not raise."""
    code = textwrap.dedent(
        """
        from harness.logging import configure_logging, log
        configure_logging()
        # If the trace_id processor is broken, this raises.
        log.info("evt")
        print("OK")
        """
    )
    cp = _run(installed_scratch, code)
    assert cp.returncode == 0, cp.stderr
    assert "OK" in cp.stdout
