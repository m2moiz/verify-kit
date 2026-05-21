"""Test that the scaffolded docker-compose.yml is valid in all has_backend/has_db polarities.

Three parametrized cells:
  - has_backend=true, has_db=true   → compose parses; postgres service present
  - has_backend=true, has_db=false  → compose parses; NO DATABASE_URL/depends_on/postgres
  - has_backend=false               → Dockerfile, docker-compose.yml, .dockerignore absent
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _docker_daemon_running() -> bool:
    """`docker info` exits 0 — Codex HIGH #9 fix (vs `which docker`).

    30s timeout (not 5s) because Docker Desktop on macOS has a slow
    first-call path; the tight budget produced flaky skip-when-healthy.
    """
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=30)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


pytestmark = pytest.mark.skipif(
    not _docker_daemon_running(),
    reason="docker daemon not running — skipping compose parsing test",
)


@pytest.mark.parametrize("has_db_value", ["true", "false"])
def test_docker_compose_parses_when_has_backend_true(tmp_path: Path, has_db_value: str):
    """`docker compose config -q` succeeds on the scaffolded compose file."""
    # Render scratch via copier (model after tests/test_phase04_scaffold_polarity.py).
    project_root = Path(__file__).resolve().parent.parent
    scratch = tmp_path / "scratch"
    subprocess.run(
        [
            "copier",
            "copy",
            "--defaults",
            "--trust",
            "--data",
            "has_backend=true",
            "--data",
            f"has_db={has_db_value}",
            "--data",
            "project_name=test",
            "--data",
            "author_name=t",
            "--data",
            "author_email=t@t.t",
            "--data",
            "project_description=t",
            str(project_root),
            str(scratch),
        ],
        cwd=tmp_path,
        check=True,
        timeout=120,
    )
    r = subprocess.run(
        ["docker", "compose", "-f", str(scratch / "docker-compose.yml"), "config", "-q"],
        cwd=scratch,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, f"compose config failed (has_db={has_db_value}): {r.stderr}"

    # When has_db=false, the api service must NOT reference DATABASE_URL or postgres
    # SERVICE BLOCK (Codex cycle-2 PARTIAL #6 — the cycle-1 fix grepped for the bare
    # word "postgres" which produced a false positive against the rendered comment
    # `# Brings up api + (postgres if has_db) + jaeger`. The comment is now gated
    # in cycle 3 so the bare-word grep is meaningful AGAIN, but we also add a
    # service-block grep for defense in depth — even if a future regression
    # adds the word "postgres" somewhere innocuous, the service-block check still
    # catches an actual service registration.
    if has_db_value == "false":
        compose_text = (scratch / "docker-compose.yml").read_text()
        assert "DATABASE_URL" not in compose_text, (
            "Codex HIGH #6: has_db=false should drop DATABASE_URL"
        )
        assert "depends_on" not in compose_text, (
            "Codex HIGH #6: api should not depend on postgres when has_db=false"
        )
        # Service-block check: parse the YAML and confirm there is no `postgres:` key
        # under top-level `services:`. This is the FORCING FUNCTION — robust against
        # future stray comment text.
        import yaml as _yaml

        parsed = _yaml.safe_load(compose_text)
        services = (parsed or {}).get("services", {}) or {}
        assert "postgres" not in services, (
            f"Codex HIGH #6: has_db=false rendered a `postgres` service block: "
            f"services={list(services.keys())}"
        )
        # Bare-word grep is now meaningful (comment was gated in cycle 3).
        assert "postgres" not in compose_text, (
            "Codex HIGH #6: has_db=false should drop ALL `postgres` references — "
            "if this fires, either the comment ungated again or a new reference snuck in."
        )


def test_no_docker_files_when_has_backend_false(tmp_path: Path):
    project_root = Path(__file__).resolve().parent.parent
    scratch = tmp_path / "scratch"
    subprocess.run(
        [
            "copier",
            "copy",
            "--defaults",
            "--trust",
            "--data",
            "has_backend=false",
            "--data",
            "project_name=test",
            "--data",
            "author_name=t",
            "--data",
            "author_email=t@t.t",
            "--data",
            "project_description=t",
            str(project_root),
            str(scratch),
        ],
        cwd=tmp_path,
        check=True,
        timeout=120,
    )
    assert not (scratch / "Dockerfile").exists()
    assert not (scratch / "docker-compose.yml").exists()
    assert not (scratch / ".dockerignore").exists()
