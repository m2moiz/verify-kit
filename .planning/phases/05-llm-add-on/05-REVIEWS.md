---
phase: 5
cycle: 7
reviewers: [codex]
reviewed_at: 2026-05-21T20:23:45Z
plans_reviewed:
  - 05-01-PLAN.md
  - 05-02-PLAN.md
  - 05-03-PLAN.md
  - 05-04-PLAN.md
  - 05-05-PLAN.md
adversarial: true
post_restructure_verification: true
restructure_commit: 48604cc
---

# Cross-AI Plan Review — Phase 5 (Cycle 7, Adversarial Post-Restructure)

Trajectory: ∞ → 8 → 5 → 2 → 1 → 3 (oscillation) → RESTRUCTURE (48604cc) → this cycle.

Per rule 08, this is the post-restructure verification cycle: expect 1–2 cycles of prose-drift cleanup. Codex was framed adversarially — assume something remains; hunt across 7 specific vectors.

## Codex Review

**HIGH**

1. [05-03-PLAN.md:186](/Users/moiz/Documents/code/verify-kit/.planning/phases/05-llm-add-on/05-03-PLAN.md:186) `_CONFTEST_BRIDGE` cannot reliably import the real fixtures inside `pytester.runpytest_subprocess`.

`pytester` changes cwd to its isolated temp dir, and its subprocess helper puts that cwd into `PYTHONPATH`, not the scratch project root. The verify block also strips `PYTHONPATH` before running the outer contract test. So the spawned sub-pytest conftest:

```python
from tests.conftest import vcr_config
from tests.llm.conftest import _reset_llm_cost, _skip_when_no_cassette
```

is likely to fail with `ModuleNotFoundError` or import some unrelated `tests` namespace, rather than inheriting the scratch project’s actual fixtures. This is not just a brittle detail: it defeats the claimed contract that the pytester subtest exercises the real `_skip_when_no_cassette` fixture.

Fix shape: generate the bridge dynamically in each test with the scratch project root inserted explicitly, e.g. derive `project_root = Path(__file__).resolve().parents[2]` in `test_skip_fixture_contract.py`, then write:

```python
pytester.makeconftest(f"""
import sys
sys.path.insert(0, {str(project_root)!r})
from tests.conftest import vcr_config  # noqa: F401
from tests.llm.conftest import _reset_llm_cost, _skip_when_no_cassette  # noqa: F401
""")
```

Stronger fix: avoid package import ambiguity entirely and import the two conftest files by absolute path via `importlib.util.spec_from_file_location`, then bind the fixture functions into the pytester conftest namespace.

**Per-Vector Review**

1. **Contract test substance:** Good. `assert_outcomes(skipped=1)` plus skip reason catches collection/error/fell-through in default mode. `skipped == 0` plus sentinel catches record-mode skip and proves the probe body ran. This part is materially stronger than the old inline probe.

2. **Conftest bridge correctness:** HIGH above. The bridge assumes pytester subprocess import reachability that is not established by the plan and is contradicted by the clean-env verify shape.

3. **`uv sync --extra dev`:** Looks correct for the rendered scaffold. `template/pyproject.toml.jinja2` declares `[project.optional-dependencies] dev = [...]`, so `--extra dev` matches the template convention. The root repo’s `pyproject.toml` has `[dependency-groups]`, but that is not the rendered scratch project surface.

4. **Clean-env discipline:** No HIGH. Stripping `VIRTUAL_ENV`, `UV_PROJECT_ENVIRONMENT`, `PYTHONPATH`, and `PYTHONHOME` covers the known false-pass vector. I would add `PYTEST_ADDOPTS`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD`, `COVERAGE_PROCESS_START`, and possibly `UV_CACHE_DIR` as MEDIUM hardening, because they can make the contract environment-dependent.

5. **Prose-drift residue:** MEDIUM only. The remaining “inline subprocess probe” references are mostly historical/explanatory, not instructions to reintroduce the old shape.

6. **Cross-plan drift:** No HIGH found. 05-04’s `refresh-cassettes` still uses `--record-mode=once`, and 05-05’s polarity plan still points at the same cassette/env assumptions after the restructure.

7. **Residual HIGH:** The import bridge is the residual HIGH. The test’s assertions are sound, but the spawned subprocess is not guaranteed to load the real fixture producer.

Conclusion: explicit HIGH concern above.

---

## Consensus Summary

Single-reviewer adversarial cycle.

### Agreed Strengths
- Contract test substance is materially stronger than the old inline probe (assert_outcomes + sentinel-string distinguishes fell-through from errored/collection-failed).
- `uv sync --extra dev` matches the rendered scaffold's `[project.optional-dependencies].dev` declaration in 05-01.
- Clean-env strips cover the known false-pass vector (VIRTUAL_ENV/UV_PROJECT_ENVIRONMENT/PYTHONPATH/PYTHONHOME).

### Agreed Concerns (HIGH)
- **05-03-PLAN.md:186 — `_CONFTEST_BRIDGE` import reachability.** pytester.runpytest_subprocess changes cwd to its isolated temp dir and puts THAT into PYTHONPATH (not the scratch project root). The outer verify block also strips PYTHONPATH before running the contract test. The bridge `from tests.conftest import ...` / `from tests.llm.conftest import ...` will either ModuleNotFoundError or import an unrelated `tests` namespace — defeating the claimed contract that the pytester subtest exercises the real `_skip_when_no_cassette` fixture.

### Suggested Fix Shape
Generate the bridge dynamically in each test with scratch project root inserted explicitly:
```python
project_root = Path(__file__).resolve().parents[2]
pytester.makeconftest(f"""
import sys
sys.path.insert(0, {str(project_root)!r})
from tests.conftest import vcr_config  # noqa: F401
from tests.llm.conftest import _reset_llm_cost, _skip_when_no_cassette  # noqa: F401
""")
```
Stronger alternative: use `importlib.util.spec_from_file_location` to load both conftest files by absolute path and bind fixtures into pytester's conftest namespace explicitly.

### MEDIUM (prose-drift / hardening)
- Clean-env list could also strip PYTEST_ADDOPTS, PYTEST_DISABLE_PLUGIN_AUTOLOAD, COVERAGE_PROCESS_START, UV_CACHE_DIR for full determinism.
- Historical "inline subprocess probe" prose remains in places; explanatory not prescriptive, but worth a sweep.

### Divergent Views
N/A (single reviewer).

CYCLE_SUMMARY: current_high=1
