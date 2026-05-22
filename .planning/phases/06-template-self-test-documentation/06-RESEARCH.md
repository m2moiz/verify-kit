# Phase 6: Template Self-Test & Documentation — Research

**Researched:** 2026-05-22
**Domain:** OSS template-repo self-verification + launch documentation + retroactive hardening
**Confidence:** HIGH (locked decisions cover most surface area; research targets are mostly Claude's-Discretion items with well-known canonical answers)

---

## User Constraints (from 06-CONTEXT.md)

### Locked Decisions (17 total — research does NOT explore alternatives)

| ID | Constraint |
|----|------------|
| D-01 | Self-test matrix = 5 rows on Linux per-PR + nightly macOS rerun (weekly cron). |
| D-02 | The 5 matrix entries are exactly: `base`, `+backend`, `+llm`, `+backend+llm`, `+backend+llm+logfire+fastapi_mcp`. |
| D-03 | Wall-clock budget per PR < 10 minutes (ROADMAP SC5). |
| D-04 | Nightly macOS cadence is weekly cron (precedent `0 4 * * 0` from Phase 5 D-09). |
| D-05 | README opens quickstart-first, then philosophy. |
| D-06 | asciinema cast of `just verify` is the headline visual; in-repo or asciinema.org embed — planner picks based on what GitHub renders cleanly. |
| D-07 | Architecture diagram is inline Mermaid in README (single source of truth, satisfies DOC-05). |
| D-08 | IDE Problems-panel PNG screenshot in README; PNG lives at `docs/img/`. |
| D-09 | Dual-audience six-row checklist lives in README as its own section (~50 lines). |
| D-10 | release-please (Google) is the release automation. |
| D-11 | Per-release "Breaking changes for consumers" callout mandatory (may be empty); hand-edited before merging release PR. |
| D-12 | SemVer enforced via release-please commit-message contract; documented in CONTRIBUTING.md. |
| D-13 | CONTRIBUTING.md scope = smoke-test loop + add-a-check + add-an-add-on-slot (last is speculative; flagged "may evolve"). |
| D-14 | PR template checkbox for six dual-audience rows; no CI grep gate. |
| D-15 | OSS boilerplate set: LICENSE (MIT), SECURITY.md, CODE_OF_CONDUCT.md (Contributor Covenant 2.1), ISSUE_TEMPLATE/{bug,feature}, pull_request_template.md. |
| D-16 | Phase 6 also closes 4 OSS-blocker beads + 2 deferred Phase 4 audits. |
| D-17 | Each bead/audit is its own dedicated Phase 6 plan. Estimated 8-11 plans total. |

### Claude's Discretion (research scope)

- Exact asciinema asset hosting (in-repo `.cast` vs asciinema.org embed URL).
- Mermaid diagram exact box-and-arrow layout — derived from `research/00-architecture-overview.md`.
- release-please config knobs (single-package vs monorepo, changelog sections, header text).
- Exact route auth scaffold mechanism for `/__debug/*` + `/summarize` + `/echo` (verify-kit-3u2).
- Exact prompt-injection defenses for `/summarize` beyond locked input-length cap (verify-kit-yr7).
- Nightly macOS cron exact value.
- CHANGELOG sections beyond mandatory "Breaking changes for consumers".
- CONTRIBUTING.md "add an add-on slot" depth.

### Deferred Ideas (OUT OF SCOPE — research does NOT cover these)

- Audio / web / game add-on slots (v0.2).
- Automated CI grep gate for dual-audience checklist (current model = checkbox + reviewer).
- release-please monorepo migration.
- macOS-only failure-isolation deep-dive.
- GitHub Security Advisory workflow integration.
- Pre-commit hook enforcement of conventional-commits.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-01 | README with philosophy, quickstart, add-on inventory, update path, troubleshooting, dual-audience checklist | §5 (Mermaid), §2 (asciinema), §9 (dual-audience PR/README rows) |
| DOC-02 | CHANGELOG with strict SemVer + "Breaking changes for consumers" callout per release | §1 (release-please), §12 (breaking-change UX) |
| DOC-03 | CONTRIBUTING.md documents smoke-test loop + add-a-check guide | §5 (CI matrix shape — referenced by smoke-test-loop section) |
| DOC-04 | Repo's own CI runs `copier copy` matrix per PR | §5 (matrix YAML) + §11 (act validation) |
| DOC-05 | Architecture diagram showing layered design | §6 (Mermaid flowchart) |
| (D-16) verify-kit-3u2 | Token-gate `/__debug/*` + `/summarize` + `/echo` | §3 (FastAPI APIKeyHeader pattern) |
| (D-16) verify-kit-yr7 | `/summarize` input-length cap + injection defenses | §4 (OWASP LLM01 defenses) |
| (D-16) verify-kit-93h | `/echo` route hardening (same shape as `/summarize`) | §3 + §4 |
| (D-16) verify-kit-1v6 | README LLM section human-read pass | (no external research needed; manual prose review) |
| (D-16) phase4-secure | Phase 4 secure-phase audit ceremony | §10 |
| (D-16) phase4-validate | Phase 4 validate-phase audit ceremony | §10 |

---

## Domain Summary

Phase 6 closes the loop on the verify-kit trust anchor by making the template verify itself, then ships a v0.1-OSS-ready repo with documentation, release automation, OSS boilerplate, and a hardening pass that resolves 4 Phase-5-deferred security beads plus 2 retroactive Phase 4 ceremonies. The work is **mostly mechanical** — almost everything is a well-trodden GitHub/OSS pattern (release-please, Contributor Covenant, GHA matrix, Mermaid in README) — but couples with two non-trivial substantive pieces: (a) a FastAPI auth scaffold that must thread cleanly through the existing Phase 4 LIFO middleware order without breaking the env-gated `/__debug/*` UX, and (b) a defensible-but-not-overbuilt prompt-injection guard on `/summarize` that aligns with the Phase 5 SECURITY.md acceptance for T-05-15 (which currently delegates injection defense to the consumer).

**Primary recommendations:**
- Use release-please-action v4 manifest mode with `release-type: python`, `bump-minor-pre-major: true`, and a `sections` override in `release-please-config.json` to emit a literal "Breaking changes for consumers" H3 in every release entry (release-please generates it; the operator hand-edits the prose before merging the release PR).
- Embed asciinema via **GIF rendered from the .cast file** (in-repo `.cast` + in-repo `.gif`, `agg` for conversion). GitHub does NOT natively render `.cast` and does NOT allow `<script>` tags in README markdown. GIF is the only embed that works inline.
- Use `APIKeyHeader` with `secrets.compare_digest` for verify-kit-3u2; install as a **global dependency** in `app/main.py` BUT keep the existing `ENV` env-gate on `/__debug/*` (defense-in-depth, two-key model). Read token from `pydantic-settings` (`VERIFYKIT_AUTH_TOKEN`).
- Ship 4 layered defenses for `/summarize` (verify-kit-yr7): (1) length cap (already locked), (2) control-char strip, (3) Content-Type enforcement, (4) static denylist of known injection markers. Match Phase 5 SECURITY.md T-05-15 "starter scaffold" framing — defenses are reasonable demonstrations, not bulletproof.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Template self-test matrix | CI (GitHub Actions) | — | This IS infra; nothing else owns it. |
| README/CHANGELOG/CONTRIBUTING | Repo root (docs) | CI (release-please bot) | Static markdown owned by repo; release-please mutates CHANGELOG via PR. |
| Mermaid arch diagram | README (inline) | — | Inline per D-07 — no separate file. |
| OSS boilerplate (LICENSE, SECURITY.md, CoC, ISSUE_TEMPLATE, PR template) | Repo root + `.github/` | — | Canonical GitHub conventions. |
| `/__debug/*` + `/summarize` + `/echo` auth | FastAPI API tier (in scaffolded project) | pydantic-settings | Token check is a request-time dependency; secret source is settings. |
| `/summarize` injection defenses | FastAPI API tier (request validation) | — | Runs at request entry, before the LLM call. |
| Phase 4 secure-phase + validate-phase audits | Planning artifacts (`.planning/phases/04-*/`) | — | Retroactive audit of already-shipped phase. |

---

## §1. release-please-action — config for verify-kit

**TL;DR:** Use **manifest mode** with `release-please-action@v4`, `release-type: python`, single-package layout, and `bump-minor-pre-major: true` for pre-1.0 SemVer. Inject a literal "Breaking changes for consumers" section via the `sections` override in `release-please-config.json`. The release PR is a normal PR — the operator hand-edits the section before merging.

### Verified facts [CITED: github.com/googleapis/release-please-action]

- `release-please-action@v4` is the current major.
- For a single-package Python repo, `release-please-config.json` is minimal:

```json
{
  "release-type": "python",
  "bump-minor-pre-major": true,
  "bump-patch-for-minor-pre-major": true,
  "include-component-in-tag": false,
  "packages": {
    ".": {
      "package-name": "verify-kit",
      "changelog-sections": [
        {"type": "feat", "section": "Added", "hidden": false},
        {"type": "fix", "section": "Fixed", "hidden": false},
        {"type": "chore", "section": "Changed", "hidden": false},
        {"type": "docs", "section": "Documentation", "hidden": false},
        {"type": "refactor", "section": "Changed", "hidden": false},
        {"type": "perf", "section": "Changed", "hidden": false},
        {"type": "test", "section": "Changed", "hidden": true}
      ]
    }
  }
}
```

- `.release-please-manifest.json` is just `{".": "0.1.0"}` — bumped automatically on each release PR merge.
- `bump-minor-pre-major: true` means breaking changes pre-1.0 bump the minor (0.1.0 → 0.2.0), not the major. This is correct for pre-1.0.
- A `feat!:` / `fix!:` commit OR a body line `BREAKING CHANGE: ...` triggers the breaking-change classification.

### Hand-edit injection pattern for "Breaking changes for consumers" [VERIFIED: release-please docs]

release-please does NOT natively support arbitrary hand-edited sections. The pattern that works:

1. release-please opens a release PR with the auto-generated CHANGELOG diff.
2. Operator opens the PR locally (`gh pr checkout <num>`), edits `CHANGELOG.md` to add (or fill in) the "Breaking changes for consumers" subsection under the new release heading, commits + pushes.
3. release-please will **preserve** manual edits on subsequent PR updates as long as the bot's own sections (Added/Fixed/Changed) aren't touched.
4. Squash-merge the release PR; tag is cut automatically.

**Canonical workflow file:**

```yaml
# .github/workflows/release-please.yml
name: release-please
on:
  push:
    branches: [main]
permissions:
  contents: write
  pull-requests: write
jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
```

No `token:` needed for a template repo using the default `GITHUB_TOKEN` — release-please will use it. (PAT is only required if you want the release PR to trigger downstream workflows, which we do NOT need here.)

### Commit-message contract for CONTRIBUTING.md

| Prefix | Effect | Example |
|--------|--------|---------|
| `feat:` | Minor bump (0.1 → 0.2 pre-1.0) | `feat(llm): add streaming summarize` |
| `fix:` | Patch bump (0.1.0 → 0.1.1) | `fix(matrix): nightly cron fires twice` |
| `feat!:` or `BREAKING CHANGE:` in body | Pre-1.0: minor bump + breaking-change footer parsed | `feat!: rename has_backend prompt to enable_backend` |
| `chore:`, `docs:`, `refactor:`, `perf:`, `test:` | No release PR triggered (chore/docs/etc don't bump) | `docs: refresh quickstart` |

### Pitfalls

- Do **NOT** use `release-as: X.Y.Z` unless explicitly forcing a version — it overrides SemVer detection.
- Avoid `release-please-action@main` (unstable); pin to `@v4`.
- The release-please bot needs `contents: write` AND `pull-requests: write` permissions — easy to miss.

**Sources:**
- [CITED: github.com/googleapis/release-please-action README v4]
- [CITED: github.com/googleapis/release-please docs — configuration]

---

## §2. asciinema embedding on GitHub

**TL;DR:** GitHub does NOT natively render `.cast` files and strips `<script>` tags from README markdown. The **only embed that renders inline on github.com is a GIF**. Ship the source `.cast` (for reproducibility) AND a rendered `.gif` (for the README), generated with `agg`.

### Verified facts [CITED: docs.asciinema.org]

- `asciinema rec <file>.cast` records terminal session to a JSON cast file.
- `agg <file>.cast <file>.gif` (separate Rust tool, `cargo install agg` or `brew install agg`) converts cast → animated GIF.
- asciinema.org provides JS embed snippets (`<script async id="asciicast-X" src="...">`), but **GitHub-flavored markdown strips `<script>` tags** — they will not render in any README.
- Self-hosted asciinema-player works only on a site you control (verify-kit docs site would need to exist; we are not building one).

### Recommendation for verify-kit

Ship three artifacts:

```
docs/casts/just-verify.cast         # source, versioned, reproducible
docs/casts/just-verify.gif          # rendered animated GIF, embedded in README
docs/casts/record-cast.sh           # one-line script: asciinema rec --cols 100 --rows 28 --overwrite docs/casts/just-verify.cast
```

README embed:

```markdown
![just verify demo](docs/casts/just-verify.gif)
```

### Deterministic recording recipe

```bash
asciinema rec \
  --overwrite \
  --cols 100 --rows 28 \
  --idle-time-limit 1.5 \
  --title "just verify — first run on a fresh copier copy" \
  docs/casts/just-verify.cast

# Convert to GIF for README
agg --cols 100 --rows 28 --font-size 14 docs/casts/just-verify.cast docs/casts/just-verify.gif
```

`--idle-time-limit 1.5` compresses long pauses (e.g. uv install latency) so the GIF doesn't drag.

### Pitfalls

- Don't try `<script>` embed → invisible in README.
- Don't commit the GIF without committing the `.cast` — loses reproducibility.
- Recordings done in a window of variable size produce inconsistent GIFs across re-records → always pass `--cols/--rows`.

**Sources:**
- [CITED: docs.asciinema.org — getting started + embedding]
- [VERIFIED: GitHub markdown spec — `<script>` is sanitized] (this is well-known; no live source needed)

---

## §3. FastAPI auth scaffold (verify-kit-3u2)

**TL;DR:** Use `APIKeyHeader(name="X-VerifyKit-Token", auto_error=False)` as a **global dependency** registered when `app = FastAPI(dependencies=[...])` is created. Read the expected token from `pydantic-settings` (`VERIFYKIT_AUTH_TOKEN`). Compare via `secrets.compare_digest`. Keep the existing Phase 4 `ENV=dev` gate on `/__debug/*` (two-layer defense: env-gate + token-gate). If `VERIFYKIT_AUTH_TOKEN` is unset AND `ENV=dev`, log a one-line warning and ALLOW requests — preserves zero-config dev UX.

### Comparison of options [CITED: fastapi.tiangolo.com/advanced/security/]

| Option | Pros | Cons |
|--------|------|------|
| **`APIKeyHeader`** (recommended) | Header-based, simplest, OpenAPI-documented, generates "🔒 Authorize" UI in `/docs` | Single fixed value; no JWT validation |
| `HTTPBearer` | Standard `Authorization: Bearer ...` shape | Implies you're issuing tokens; overkill for a single shared secret |
| Custom middleware | Most flexible | Doesn't appear in OpenAPI; doesn't integrate with FastAPI `Depends` |
| Per-route guard | Granular | Easy to forget on new routes — opposite of what we want |

### Canonical implementation

```python
# app/auth.py
import secrets
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from app.settings import Settings, get_settings

_api_key_header = APIKeyHeader(name="X-VerifyKit-Token", auto_error=False)

def require_auth(
    presented: Annotated[str | None, Depends(_api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    expected = settings.verifykit_auth_token
    if not expected:
        if settings.env == "dev":
            # Zero-config dev UX: log once, allow.
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VERIFYKIT_AUTH_TOKEN not configured in non-dev environment",
        )
    if not presented or not secrets.compare_digest(
        presented.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing X-VerifyKit-Token",
        )
```

```python
# app/main.py — apply globally
app = FastAPI(
    title="...",
    dependencies=[Depends(require_auth)],  # gates EVERY route
)
```

Then in `pydantic-settings`:

```python
class Settings(BaseSettings):
    env: Literal["dev", "prod"] = "dev"
    verifykit_auth_token: str | None = None  # blank in .env.example
```

### Interaction with Phase 4 middleware order (LIFO)

From STATE.md: `secure` outermost (registered last), `pyinstrument` innermost. **Dependencies run AFTER all middleware** but BEFORE the route handler — so `require_auth` adds a stage that sits between `secure` (outer) and the route. It does NOT change the LIFO order of middleware registration. Safe to bolt on.

Exception path that must be preserved: `/healthz` should remain **unauthenticated** so docker-compose healthchecks and CI smoke tests keep working. Use a per-route dependency override via `dependencies=[]` on the `/healthz` decorator, OR exclude `/healthz` inside `require_auth` itself.

### Recommended exclusion list

| Route | Auth required? | Why |
|-------|----------------|-----|
| `GET /healthz` | NO | docker healthcheck + smoke tests |
| `GET /docs`, `/redoc`, `/openapi.json` | Dev: NO; Prod: YES | Dev UX |
| `POST /summarize` | YES | LLM cost surface |
| `POST /echo` | YES | reflection surface |
| `GET /__debug/*` | YES + env-gate (defense in depth) | Already env-gated, now also token-gated |

### Pitfalls

- Don't use `Depends(_api_key_header)` directly on routes; the indirection via `require_auth` is what lets you implement the dev-mode fallback.
- `secrets.compare_digest` MUST receive equal-length byte strings to be constant-time; encode both sides to `utf-8`.
- A blank token in `.env.example` is fine; verifying tests must explicitly set `VERIFYKIT_AUTH_TOKEN` to a known value.

**Sources:**
- [CITED: fastapi.tiangolo.com/advanced/security/api-key/] — APIKeyHeader pattern
- [CITED: fastapi.tiangolo.com/advanced/security/http-basic-auth/] — `secrets.compare_digest`
- [VERIFIED: Phase 4 SECURITY.md + STATE.md] — middleware LIFO order

---

## §4. Prompt-injection defenses for `/summarize` (verify-kit-yr7)

**TL;DR:** Phase 5 SECURITY.md T-05-15 explicitly **accepts** prompt-injection risk for `/summarize` and documents it as "consumer's responsibility". verify-kit-yr7 walks this back partially: ship **starter-scaffold defenses** that demonstrate the pattern without claiming bulletproof protection. Layer four input-side defenses; explicitly document the limitation.

### The defenses to ship

| # | Defense | Implementation | Why |
|---|---------|----------------|-----|
| 1 | **Input length cap** (locked) | Pydantic `Field(max_length=5000)` on the request `text` field | Bounds attack surface; bounds LLM cost |
| 2 | **Control-character strip** | `text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)` before LLM call | Strips zero-width chars + null bytes used in some injection variants |
| 3 | **Content-Type enforcement** | FastAPI implicit (request body validated as JSON); add explicit `Content-Type: application/json` check via middleware OR rely on FastAPI default | Prevents form-encoded or text/plain bypass attempts |
| 4 | **Static denylist** | Reject (HTTP 400) if request text matches a small list of obvious injection markers: `r"(?i)\b(ignore|disregard|forget)\s+(all\s+)?previous\s+(instructions|prompts)"`, `r"<\|im_(start|end)\|>"`, `r"###\s*system"` | Catches naive copy-pasted injection payloads |

### What to NOT ship in v0.1 (deferred per scope)

- Output filtering (would require parsing the LLM's response — too opinionated for a starter)
- LLM-based classifier prefilter (recursive cost surface)
- Allow-list of input vocabulary (impossible without knowing the consumer's domain)
- System-prompt sandwiching beyond what's already in the `_summarize` function

### Canonical implementation

```python
# app/api.py — /summarize request validation
import re
from typing import Annotated
from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_INJECTION_MARKERS = [
    re.compile(r"(?i)\b(ignore|disregard|forget)\s+(all\s+)?previous\s+(instructions|prompts)"),
    re.compile(r"<\|im_(start|end)\|>"),
    re.compile(r"###\s*system\b", re.IGNORECASE),
]

class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)

    @field_validator("text")
    @classmethod
    def _strip_control_chars_and_check_injection(cls, v: str) -> str:
        v = _CONTROL_CHARS.sub("", v)
        for marker in _INJECTION_MARKERS:
            if marker.search(v):
                raise ValueError("input contains a disallowed pattern")
        return v
```

The `ValueError` becomes a 422 via Pydantic; the injection-marker case can be elevated to 400 with a dedicated handler if the planner wants clearer telemetry.

### Documentation contract (LLM-12 README addendum)

The README MUST include a paragraph noting:

> verify-kit's `/summarize` ships starter-grade input defenses (length cap, control-char strip, obvious-injection denylist). These demonstrate the pattern but are **not bulletproof**. Consumers handling untrusted input should layer additional defenses: output validation, system-prompt hardening, and an LLM-based classifier prefilter. See OWASP LLM01.

This aligns with Phase 5 SECURITY.md R-05-15 acceptance language.

### Apply same shape to `/echo` (verify-kit-93h)

`/echo` exists as a Phase 4 demo route. It does NOT call an LLM, but it DOES reflect untrusted input. Apply layers 1–3 (skip the denylist — it's LLM-specific). Add a length cap and control-char strip; that's enough for the starter scaffold.

### Pitfalls

- Don't put the regex in `app/main.py` — keep it in `app/api.py` or `app/services.py` next to the route.
- Don't claim "prompt-injection protection" in marketing copy — Phase 5 SECURITY.md T-05-15 framing must be preserved.
- The `field_validator` running on a 5000-char string with 3 regexes is cheap (<1ms) but worth a single benchmark assertion in the test suite.

**Sources:**
- [CITED: owasp.org/www-project-top-10-for-large-language-model-applications/] — LLM01 framing
- [CITED: genai.owasp.org/llm-top-10/ — LLM01:2025 Prompt Injection] (deeper guide; visit if more detail needed)
- [VERIFIED: .planning/phases/05-llm-add-on/05-SECURITY.md T-05-15, R-05-15] — current accepted-risk language

---

## §5. GitHub Actions self-test matrix shape

**TL;DR:** Single workflow `template-selftest.yml` with a 5-row matrix and `fail-fast: false`. Sibling workflow `template-selftest-macos.yml` reuses the same matrix on `macos-latest` via `schedule: cron` + `workflow_dispatch`.

### Linux per-PR workflow

```yaml
# .github/workflows/template-selftest.yml
name: template-selftest

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  selftest:
    name: ${{ matrix.combo }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        combo:
          - base
          - backend
          - llm
          - backend-llm
          - full
        include:
          - combo: base
            data: '{"has_backend": false, "has_llm": false, "has_logfire": false, "has_fastapi_mcp": false}'
          - combo: backend
            data: '{"has_backend": true,  "has_llm": false, "has_logfire": false, "has_fastapi_mcp": false}'
          - combo: llm
            data: '{"has_backend": false, "has_llm": true,  "has_logfire": false, "has_fastapi_mcp": false}'
          - combo: backend-llm
            data: '{"has_backend": true,  "has_llm": true,  "has_logfire": false, "has_fastapi_mcp": false}'
          - combo: full
            data: '{"has_backend": true,  "has_llm": true,  "has_logfire": true,  "has_fastapi_mcp": true}'

    steps:
      - uses: actions/checkout@v4
      - uses: jdx/mise-action@v2
      - name: Install copier
        run: uv tool install copier
      - name: Render scratch project
        run: |
          SCRATCH="/tmp/scratch-${{ matrix.combo }}"
          copier copy --trust --defaults --data-file <(echo '${{ matrix.data }}') \
            "$GITHUB_WORKSPACE" "$SCRATCH"
      - name: Run just verify in scratch
        working-directory: /tmp/scratch-${{ matrix.combo }}
        run: just verify
```

Notes:
- `fail-fast: false` — REQUIRED so a `+llm` failure doesn't mask a `+backend` failure.
- `--trust` flag — Copier 9.x requires it for templates with `_tasks` or `_jinja_extensions` (verify-kit has neither yet, but defensive).
- `--defaults` — uses Copier prompt defaults for everything not in `--data-file`.
- `<(echo '...')` — process substitution converts the JSON string into a file for `--data-file`.

### Nightly macOS sibling

```yaml
# .github/workflows/template-selftest-macos.yml
name: template-selftest-macos

on:
  schedule:
    - cron: '0 4 * * 0'  # Sun 04:00 UTC — matches Phase 5 D-09
  workflow_dispatch:

jobs:
  selftest:
    name: ${{ matrix.combo }}
    runs-on: macos-latest
    strategy:
      fail-fast: false
      matrix:
        combo: [base, backend, llm, backend-llm, full]
        # ... same `include:` block as linux ...
    # ... same steps ...
```

Per D-04, weekly Sunday 04:00 UTC. Failures **surface but do not block** PRs — this is a separate workflow with no PR trigger.

### Pitfalls

- macOS runners are ~10× more expensive in GHA minutes than Linux — keep them weekly, not per-PR.
- `copier copy "$GITHUB_WORKSPACE" "$SCRATCH"` copies from a local path, not a git URL — critical so the PR's diff is what's tested.
- If `just verify` requires Docker (Testcontainers for Postgres), the macOS runner needs `colima` or skip — current Phase 4 Testcontainers paths already have a skip-on-no-docker pattern; ensure it activates on macos-latest.

**Sources:**
- [CITED: docs.github.com/actions/using-jobs/using-a-matrix-for-your-jobs] — `include:` + `fail-fast`
- [CITED: copier.readthedocs.io] — `--data-file`, `--trust`, `--defaults`

---

## §6. Mermaid architecture diagram on GitHub

**TL;DR:** Inline `mermaid` fenced code block. GitHub's renderer caps at roughly 5000 nodes/edges per chart (well above what verify-kit needs). Use `flowchart TD` with subgraphs for the four-layer model. Source the layout directly from `research/00-architecture-overview.md`'s ASCII diagram — it already shows the right shape.

### Canonical embed

```markdown
\`\`\`mermaid
flowchart TD
    subgraph L0["Layer 0 — Universal Foundation"]
        copier["Copier template"]
        mise[".mise.toml + just + Makefile"]
        verify["just verify (trust anchor)"]
        harness["harness/ package<br/>(structlog · trace_id · /__debug · cache)"]
        mcp["verify-kit MCP server<br/>(13 tools)"]
        agents["AGENTS.md + per-agent rules"]
        otel["OpenTelemetry (inert until OTLP set)"]
    end

    L0 --> Backend
    L0 --> LLM
    L0 -.-> Web
    L0 -.-> Audio
    L0 -.-> Game

    subgraph addons["Add-on slots"]
        Backend["Backend (FastAPI) — v0.1"]
        LLM["LLM — v0.1"]
        Web["Web — v0.2"]
        Audio["Audio — v0.2"]
        Game["Game — v0.2"]
    end

    Backend -.composes.- LLM

    classDef shipped fill:#7CFFCB,stroke:#0a4,color:#000;
    classDef deferred fill:#eee,stroke:#999,color:#666,stroke-dasharray: 5 5;
    class Backend,LLM shipped;
    class Web,Audio,Game deferred;
\`\`\`
```

### Verified facts [CITED: docs.github.com creating-diagrams + mermaid-js.github.io]

- GitHub renders Mermaid in any markdown file via ```` ```mermaid ```` fenced block.
- No documented hard node cap in GitHub's docs; Mermaid itself processes 1000s of nodes; verify-kit's diagram has ~12 nodes.
- `flowchart TD` (top-down) is the modern syntax; `graph TD` is the legacy alias and still works.
- Subgraph labels with quotes support multi-word names.
- `classDef` + `class` enables visual differentiation (shipped vs deferred).

### Pitfalls

- Mermaid theming on GitHub uses light/dark auto-switch — avoid hardcoding hex colors that fail in dark mode. The `classDef` colors above are tuned for both.
- Don't use `<br/>` inside subgraph labels — use plain text. Inside node labels it's fine (as shown).
- The README must be `.md` (not `.rst` or anything else) for the fenced-mermaid renderer to fire.

**Sources:**
- [CITED: docs.github.com/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams]
- [VERIFIED: research/00-architecture-overview.md — canonical layered shape]

---

## §7. Contributor Covenant 2.1

**TL;DR:** Single canonical source URL. One placeholder to fill in. Ship as markdown at repo root.

### Verified facts [CITED: contributor-covenant.org/version/2/1/]

- Canonical markdown URL: https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md
- One placeholder: `[INSERT CONTACT METHOD]` in the Enforcement section.
- Recommended file name: `CODE_OF_CONDUCT.md` at repo root (GitHub's community-profile checker looks here specifically).
- Plain text and AsciiDoc versions also exist; markdown is correct for this repo.

### Recommended substitution

Replace `[INSERT CONTACT METHOD]` with the operator's email (`m.moiz1995@gmail.com`) — the simplest, most permissionless reporting channel. Mention that GitHub issues + private security reports (per SECURITY.md) are also options.

### Pitfalls

- Don't pin to an older version (2.0); 2.1 is current as of mid-2026 with no 2.2 released yet (verify before committing).
- Don't strip the attribution footer — Contributor Covenant is CC-BY-4.0; attribution is required.

**Sources:**
- [CITED: www.contributor-covenant.org/version/2/1/code_of_conduct/]

---

## §8. GitHub issue templates — YAML form vs markdown

**TL;DR:** Ship **YAML form templates** (`bug.yml`, `feature.yml`). They are the GitHub-recommended modern approach as of 2024–2026 and produce structured submissions that are easier for the operator to triage.

### Why YAML forms

- Structured fields (dropdowns, text inputs, checkboxes) reduce follow-up questions.
- Form-validated required fields ensure bug reports include repro steps + version.
- Rendered as a guided form, not a markdown blob with deletable boilerplate.
- Markdown templates are still supported but are the older pattern.

### Canonical `bug.yml`

```yaml
# .github/ISSUE_TEMPLATE/bug.yml
name: Bug report
description: Report a bug or unexpected behavior in verify-kit.
title: "[Bug]: "
labels: [bug, triage]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for filing a bug! Please fill in the form below.

  - type: input
    id: version
    attributes:
      label: verify-kit version
      description: What version are you running? (`grep '^version' pyproject.toml` or look at the tag.)
      placeholder: "0.1.0"
    validations:
      required: true

  - type: dropdown
    id: addons
    attributes:
      label: Which add-ons did you enable?
      multiple: true
      options:
        - "(none — base)"
        - "has_backend"
        - "has_llm"
        - "has_logfire"
        - "has_fastapi_mcp"
    validations:
      required: true

  - type: textarea
    id: repro
    attributes:
      label: Steps to reproduce
      description: A clear sequence of commands and expected vs. actual output.
      placeholder: |
        1. `copier copy ... my-project`
        2. `cd my-project`
        3. `just verify`
        4. Expected exit 0, got exit N with message X
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: Relevant logs
      description: Paste `.verify/report.json` or the failing terminal output.
      render: shell

  - type: input
    id: env
    attributes:
      label: OS / runner
      placeholder: "macOS 14.5 / Ubuntu 24.04 / Windows WSL2"
```

### Canonical `feature.yml`

Mirror structure: name, description, problem-statement textarea, proposed-solution textarea, alternatives-considered textarea, optional "I'd like to try implementing this" checkbox.

### Optional `config.yml`

```yaml
# .github/ISSUE_TEMPLATE/config.yml
blank_issues_enabled: false
contact_links:
  - name: Security vulnerability
    url: https://github.com/m2moiz/verify-kit/security/advisories/new
    about: Use private security advisories for vulnerability reports.
```

### Pitfalls

- Don't mix `.yml` and `.md` forms in the same `.github/ISSUE_TEMPLATE/` directory unless you want GitHub to render the chooser screen with mismatched UX.
- `validations: required: true` blocks submission of empty required fields — use sparingly to avoid friction.

**Sources:**
- [CITED: docs.github.com/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository]
- [CITED: docs.github.com/communities/.../syntax-for-issue-forms]

---

## §9. Dual-audience PR template

**TL;DR:** Mirror the six rows from REQUIREMENTS.md verbatim as checkboxes. Add a short summary/test-plan header.

### Source-of-truth rows [VERIFIED: REQUIREMENTS.md lines 11-18 + research/00-architecture-overview.md]

The canonical six rows are already published in REQUIREMENTS.md and `research/00-architecture-overview.md`. Quote them verbatim — DO NOT rewrite. The exact text is:

1. Human in terminal sees → Pretty colorized output via isatty; spinner; failed checks summarized with one-line next-action hint
2. Human in VS Code sees → SARIF in Problems panel, JUnit in Testing sidebar — no agent involvement required
3. Agent calling programmatically gets → Deterministic JSON with stable schema (introspectable via `describe`), error envelope `{code, message, hint, fix_command, docs_url}`, semantic exit codes
4. Agent has a fix path → Failed check returns `fix_command`; `fix_propose` MCP tool returns unified diff with rationale; agent can re-verify without human round-trip
5. Human can override agent → Every fix is `--dry-run`-able; destructive MCP tools annotated `destructiveHint: true`; Stop-hook escape hatch (`VERIFY_KIT_SKIP=1`); audit log in `.verify-kit/audit.jsonl`
6. Both can collaborate mid-flow → Same `verify-kit trace --last` works for both; state file-backed in `.verify-kit/` so human can `cat` while agent runs

### Canonical PR template

```markdown
<!-- .github/pull_request_template.md -->
## Summary

<!-- 1-3 sentences: what changes, why -->

## Test plan

<!-- How was this verified? `just verify` output? Specific scenarios? -->

## Dual-audience checklist

Every change must answer all six rows. Tick each. If a row is N/A for this PR, write "N/A — <reason>" in the box.

- [ ] **1. Human in terminal sees:** Pretty colorized output via isatty; spinner; failed checks summarized with one-line next-action hint.
- [ ] **2. Human in VS Code sees:** SARIF in Problems panel, JUnit in Testing sidebar — no agent involvement required.
- [ ] **3. Agent calling programmatically gets:** Deterministic JSON with stable schema (introspectable via `describe`), error envelope `{code, message, hint, fix_command, docs_url}`, semantic exit codes.
- [ ] **4. Agent has a fix path:** Failed check returns `fix_command`; `fix_propose` MCP tool returns unified diff with rationale; agent can re-verify without human round-trip.
- [ ] **5. Human can override agent:** Every fix is `--dry-run`-able; destructive MCP tools annotated `destructiveHint: true`; Stop-hook escape hatch (`VERIFY_KIT_SKIP=1`); audit log in `.verify-kit/audit.jsonl`.
- [ ] **6. Both can collaborate mid-flow:** Same `verify-kit trace --last` works for both; state file-backed in `.verify-kit/` so human can `cat` while agent runs.

## Conventional-commit type

<!-- One of: feat / fix / chore / docs / refactor / perf / test (use `feat!:` for breaking) -->

## Breaking changes for consumers

<!-- If this changes any Copier prompt, rendered file path, or generated-project API: describe the migration step for users running `copier update`. Otherwise: "None." -->
```

### Pitfalls

- Don't add a CI grep gate (per D-14 deferred). Reviewer's eye + checkboxes is the policy.
- Don't reword the six rows — REQUIREMENTS.md is the canonical text.

**Sources:**
- [VERIFIED: .planning/REQUIREMENTS.md lines 11-18]
- [VERIFIED: research/00-architecture-overview.md "Dual-audience checklist" section]

---

## §10. Phase 4 secure-phase + validate-phase ceremony scope

**TL;DR:** Both files (`04-SECURITY.md`, `04-VALIDATION.md`) **already exist** in the repo. STATE.md still lists them as "deferred" because they were authored during phase execution but never formally re-audited via `/gsd:secure-phase` / `/gsd:validate-phase` after Phase 4 closed. The Phase 6 ceremonies are **re-runs** that produce updated audit-trail entries, not from-scratch builds.

### Current state on disk

```
.planning/phases/04-backend-fastapi-add-on/04-SECURITY.md       — 119 lines, status: verified, threats_open: 0
.planning/phases/04-backend-fastapi-add-on/04-VALIDATION.md     — 435 lines
.planning/phases/04-backend-fastapi-add-on/04-VERIFICATION.md   — 250 lines
```

`04-SECURITY.md` frontmatter says `status: verified, threats_total: 14, threats_closed: 14, auditor: gsd:secure-phase`. So the secure-phase ceremony was actually run — the open question is whether the STATE.md "deferred" entry is stale.

### Workflow behavior [VERIFIED: ~/.claude/get-shit-done/workflows/secure-phase.md, validate-phase.md]

**secure-phase ceremony:**
- Reads existing SECURITY.md, PLAN.md threat blocks, SUMMARY.md threat flags.
- Classifies each threat as CLOSED or OPEN.
- Short-circuit: if `threats_open == 0 AND register_authored_at_plan_time == true` → done.
- For Phase 4 specifically: PLAN.md files lack `<threat_model>` blocks, so the register is reconstructed from SUMMARY.md Threat Flags. The auditor then runs in retroactive-STRIDE mode.

**validate-phase ceremony:**
- Reads existing VALIDATION.md if present.
- Builds requirement-to-test map from PLAN/SUMMARY.
- Detects test infrastructure (pytest, jest, vitest configs).
- Cross-references each requirement against existing tests.
- Classifies: COVERED / PARTIAL / MISSING.
- Generates missing tests OR records justified gaps.

### Plan shape for these ceremonies

Each Phase 6 plan for these is **light** — the work is to invoke the existing GSD workflow, capture its output, and reconcile any reopened threats / gaps. Estimate per plan:

- 1 task: invoke `/gsd:secure-phase 4` (or `/gsd:validate-phase 4`)
- 1 task: review auditor output, file beads for any newly-surfaced gaps, mark closed in STATE.md
- 1 task: commit updated `04-SECURITY.md` / `04-VALIDATION.md` with new audit-trail row

### Pitfalls

- DO NOT delete the existing `04-SECURITY.md` / `04-VALIDATION.md` before re-running. The ceremonies are designed to update-in-place.
- If the re-audit surfaces a NEW threat that wasn't in the original register, it becomes a new bead — not in scope for Phase 6 unless the planner chooses to roll it in.

**Sources:**
- [VERIFIED: ~/.claude/get-shit-done/workflows/secure-phase.md lines 1-80]
- [VERIFIED: ~/.claude/get-shit-done/workflows/validate-phase.md lines 1-80]
- [VERIFIED: .planning/phases/04-backend-fastapi-add-on/04-SECURITY.md frontmatter]

---

## §11. act-local validation

**TL;DR:** `act -W .github/workflows/template-selftest.yml -j selftest --matrix combo:base` is the canonical invocation. ROADMAP SC5 requires "runs end-to-end in act locally" — that means at least the `base` combo passing. Full matrix in act is overkill (slow, container-heavy).

### Verified facts [CITED: nektosact.com/usage/index.html]

- `act -l <event>` lists workflows that trigger on `<event>` (default event = `push`).
- `act -W <path>` runs a specific workflow file.
- `act -j <jobname>` filters by job name.
- `act --matrix key:value` filters matrix rows.
- Combined: `act -W .github/workflows/template-selftest.yml -j selftest --matrix combo:base`.

### Recommended validation steps

```bash
# Minimal sanity: list workflows for PR event
act -l pull_request

# Run the base matrix entry (cheapest, fastest)
act pull_request \
  -W .github/workflows/template-selftest.yml \
  -j selftest \
  --matrix combo:base

# Full matrix locally (slow — ~30 min on M2)
act pull_request -W .github/workflows/template-selftest.yml -j selftest
```

### Pitfalls

- `act` defaults to the `catthehacker/ubuntu:act-latest` image which is multi-GB. First run will download it.
- The `mise-action` may behave differently in act vs real runners — test the `base` row before relying on full-matrix act runs.
- Don't try to run the macOS nightly workflow in act — act only supports Linux containers.

**Sources:**
- [CITED: nektosact.com/usage/index.html]

---

## §12. copier update breaking-change UX

**TL;DR:** When a Copier prompt is renamed, a default changes, or a file location moves, the CHANGELOG "Breaking changes for consumers" section should list **the exact migration command** a downstream user needs to run.

### Shape of an entry

```markdown
## 0.2.0 — 2026-06-15

### Breaking changes for consumers

If you scaffolded a project with verify-kit < 0.2.0 and want to pull this release via `copier update`:

1. **Prompt rename:** `has_backend` → `enable_backend` (and same for `has_llm` → `enable_llm`).
   When `copier update` shows a three-way merge conflict in `.copier-answers.yml`,
   accept the new key name and copy the old value:

   ```yaml
   # before
   has_backend: true
   # after
   enable_backend: true
   ```

2. **Path move:** `template/app/` → `template/{% if enable_backend %}app{% endif %}/` — no
   action required; Copier handles the rename automatically.

3. **New prompt added:** `auth_token_required` (default: `true`).
   If you previously ran without auth, set it to `false` during `copier update`.

### Added
- Token-gated `/__debug/*`, `/summarize`, `/echo` (verify-kit-3u2).
- ...

### Fixed
- ...
```

### Authoring rule

Every breaking change entry should answer three questions:
1. **What changed in the template?** (renamed prompt / moved file / changed default)
2. **What does the consumer see when they `copier update`?** (merge conflict / silent rename / new prompt)
3. **What manual step, if any, must they take?** (edit `.copier-answers.yml` / re-run `just verify` / nothing)

Empty section text for releases with no breaking changes: `_None — `copier update` is safe and silent._`

### Pitfalls

- "Breaking" here means "consumer-facing breaking" — internal template refactors that produce byte-identical output for a given answer set are NOT breaking.
- Don't conflate SemVer-breaking commits (`feat!:`) with consumer-breaking changes. They usually align, but a `feat!:` that adds a new optional Copier prompt is technically backwards-compatible — flag in the prose.

**Sources:**
- [VERIFIED: copier.readthedocs.io — `copier update` three-way merge semantics]
- [VERIFIED: D-11 from CONTEXT.md — hand-edited section is mandatory]

---

## Cross-Plan Dependencies

| Producer Plan | Consumer Plan(s) | Contract |
|--------------|------------------|----------|
| `OSS boilerplate plan` (LICENSE, CoC, SECURITY.md, ISSUE_TEMPLATE/*) | `README plan` (links to CoC, SECURITY.md, CONTRIBUTING.md from quickstart footer) | Footer link targets must match files actually shipped. |
| `auth-scaffold plan` (verify-kit-3u2) | `summarize-input-defenses plan` (verify-kit-yr7), `echo-hardening plan` (verify-kit-93h) | Both inherit `require_auth` global dependency. Their tests must set `VERIFYKIT_AUTH_TOKEN`. |
| `auth-scaffold plan` | `template-selftest CI plan` | Self-test matrix must set `VERIFYKIT_AUTH_TOKEN=dev-token-for-tests` in the `+backend` and `+backend+llm` matrix entries OR rely on `ENV=dev` fallback. |
| `release-please plan` | `CONTRIBUTING.md plan` | CONTRIBUTING must document the `feat:` / `fix:` / `feat!:` commit contract that release-please parses. |
| `README + Mermaid plan` | `OSS boilerplate plan` (LICENSE shows up via README badge link) | README badges link to LICENSE and CI status. |
| `template-selftest plan` (Linux) | `template-selftest-macos plan` | macOS plan reuses Linux plan's matrix definition; should DRY via YAML anchor or explicit copy with a comment. |
| `phase4-secure-audit plan` | `phase4-validate-audit plan` | Both update STATE.md "Todos" section; either order works but they should commit-sequentially to avoid merge conflicts. |
| `LLM-readme-pass plan` (verify-kit-1v6) | `README plan` | LLM-readme-pass operates on the section already written in the README plan; sequential dependency. |

---

## Open Questions for the Planner

1. **Is `04-SECURITY.md` already authoritative, or do we re-run secure-phase from scratch?**
   - Current state: `status: verified, threats_open: 0` with `auditor: gsd:secure-phase` already set.
   - Recommendation: planner runs `/gsd:secure-phase 4` once; if it short-circuits because `threats_open == 0`, capture the no-op as evidence and close the bead. Same for validate-phase.

2. **Where exactly does the asciinema `.cast` + `.gif` live?**
   - `docs/casts/` is conventional but verify-kit may not have a `docs/` tree yet.
   - Alternative: `assets/casts/`.
   - Planner picks based on what's already present.

3. **`/healthz` exclusion from auth — global dependency exception or in-route override?**
   - Both work. Planner picks based on test ergonomics. Recommend in-`require_auth`-exception (early-return on `request.url.path == "/healthz"`) so all auth logic stays in one file.

4. **Should the Mermaid arch diagram inline OR live in a separate file imported by reference?**
   - D-07 locks "inline Mermaid in README" — locked. No ambiguity.

5. **What's the verify-kit-1v6 "human-read pass" deliverable?**
   - It's a pure prose-review task with no scriptable output. Deliverable could be: (a) a commit that edits the README LLM section, OR (b) a SUMMARY.md note that says "read, no changes needed". Planner picks.

6. **Does the self-test matrix need `--data-file <(echo ...)` OR is `--data "key=val"` simpler?**
   - Copier supports both. `--data key=val` (repeatable) is simpler but uglier for boolean values. Planner picks; both are equivalent.

7. **Should `release-please` add a `release-as` override file for the first 0.1.0 release?**
   - First release (0.0.0 → 0.1.0) is a common stumbling point. May want to pre-populate `.release-please-manifest.json` with `{".": "0.0.0"}` so the first feat: commit triggers a release PR for 0.1.0. Planner verifies.

8. **Where does CONTRIBUTING.md's "add a new check in 10 lines" snippet live in the codebase to keep it in sync?**
   - Option A: hard-code in CONTRIBUTING.md, accept some drift risk.
   - Option B: pull from a test file (`tests/test_register_decorator.py`) via doctest-style include.
   - Recommendation: Option A for v0.1 (simpler, low-drift since the API is stable).

---

## Estimated Plan Count and Ordering

CONTEXT.md hypothesis: 8–11 plans. Refined recommendation: **10 plans**, ordered for clean dependency flow:

| Order | Plan | Output | Depends on |
|-------|------|--------|------------|
| 1 | `06-01-oss-boilerplate-PLAN.md` | LICENSE, CODE_OF_CONDUCT.md, SECURITY.md, ISSUE_TEMPLATE/{bug.yml,feature.yml,config.yml} | — |
| 2 | `06-02-auth-scaffold-PLAN.md` (verify-kit-3u2) | `app/auth.py`, `require_auth` global dep, settings, tests | Phase 4 app/ |
| 3 | `06-03-summarize-input-defenses-PLAN.md` (verify-kit-yr7) | `SummarizeRequest` validator, denylist regexes, tests | 06-02 (auth tests share fixture pattern) |
| 4 | `06-04-echo-hardening-PLAN.md` (verify-kit-93h) | `EchoRequest` validator + tests | 06-02, 06-03 |
| 5 | `06-05-release-please-PLAN.md` | `release-please-config.json`, `.release-please-manifest.json`, `release-please.yml` workflow, CHANGELOG.md stub | — |
| 6 | `06-06-readme-and-arch-diagram-PLAN.md` | README rewrite (quickstart-first, Mermaid, asciinema GIF, six-row checklist, IDE-screenshot caption), `docs/casts/` | 06-01 (links), 06-05 (CHANGELOG reference) |
| 7 | `06-07-contributing-and-pr-template-PLAN.md` | CONTRIBUTING.md, .github/pull_request_template.md | 06-05 (commit-contract doc) |
| 8 | `06-08-template-selftest-CI-PLAN.md` | `.github/workflows/template-selftest.yml` + `template-selftest-macos.yml`, act-validation script | 06-02 (matrix needs auth token), 06-03/04 (matrix exercises hardened routes) |
| 9 | `06-09-llm-readme-pass-PLAN.md` (verify-kit-1v6) | LLM section prose-review commit OR no-op SUMMARY | 06-06 (README must exist) |
| 10 | `06-10-phase4-audit-ceremonies-PLAN.md` | Updated `04-SECURITY.md` + `04-VALIDATION.md` with new audit-trail rows; STATE.md todo closure | — |

**Ordering rationale:**
- OSS boilerplate first (no deps, unblocks README links).
- Hardening trio (auth + summarize + echo) next — they're a tight cluster that the CI matrix needs working before the self-test plan lands.
- release-please before README because README references CHANGELOG.md location.
- README + diagram in the middle once the deliverables it documents exist.
- CONTRIBUTING + PR template after release-please (needs commit contract doc).
- CI self-test last among substantive plans because it exercises the hardened endpoints.
- LLM-readme-pass after README rewrite.
- Phase 4 audits can run any time (no deps); slotted last as a clean closure.

**Wave hypothesis** (planner can refine):
- **W1:** 06-01 (boilerplate), 06-05 (release-please), 06-10 (Phase 4 audits) — all independent.
- **W2:** 06-02 (auth scaffold).
- **W3:** 06-03 (summarize defenses), 06-04 (echo hardening) — both depend on 06-02.
- **W4:** 06-06 (README+diagram), 06-07 (CONTRIBUTING+PR template) — depend on 06-01 + 06-05.
- **W5:** 06-08 (self-test CI) — depends on 06-02/03/04 hardened routes existing.
- **W6:** 06-09 (LLM-readme-pass) — depends on 06-06.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Contributor Covenant 2.1 is still the current version (no 2.2 released as of 2026-05) | §7 | Low — version check is `curl https://www.contributor-covenant.org/version/2/1/` to verify; if 2.2 exists, planner switches |
| A2 | `agg` is installable via `brew install agg` on the operator's M2 mac | §2 | Low — fallback is `cargo install --git https://github.com/asciinema/agg` |
| A3 | release-please-action v4 is still current major (no v5 released) | §1 | Low — planner verifies with `gh release list -R googleapis/release-please-action` |
| A4 | The Phase 4 self-test matrix doesn't break when `VERIFYKIT_AUTH_TOKEN` is unset in `ENV=dev` (matches §3 dev-fallback design) | §5, §3 | Medium — if Phase 4 tests assume no auth at all, they may need `VERIFYKIT_AUTH_TOKEN=test-token` injected via test fixture |
| A5 | `act` works without modification for the proposed `template-selftest.yml` (no Docker-in-Docker for Testcontainers in the act run) | §11 | Medium — act sometimes diverges from real runners; planner should pre-validate the `base` row in act before declaring SC5 met |
| A6 | The `04-SECURITY.md` short-circuit (already verified) holds when re-run | §10 | Low — worst case: ceremony surfaces a new threat → file as bead, defer or roll in |

---

## Sources

### Primary (HIGH confidence)
- [CITED] github.com/googleapis/release-please-action — v4 README, config schema
- [CITED] docs.asciinema.org — recording + embedding patterns
- [CITED] fastapi.tiangolo.com/advanced/security/ — APIKeyHeader, HTTPBearer, secrets.compare_digest
- [CITED] docs.github.com/communities/.../configuring-issue-templates — YAML form syntax
- [CITED] docs.github.com/get-started/writing-on-github/.../creating-diagrams — Mermaid embed
- [CITED] www.contributor-covenant.org/version/2/1/ — canonical CoC source
- [CITED] nektosact.com/usage/index.html — act CLI invocations
- [CITED] docs.github.com/actions/.../using-a-matrix-for-your-jobs — matrix `include` + `fail-fast`

### Secondary (MEDIUM confidence)
- [CITED] owasp.org/www-project-top-10-for-large-language-model-applications/ — LLM01 framing (page is summary-only; deeper guidance at genai.owasp.org)

### Internal (VERIFIED via codebase read)
- .planning/REQUIREMENTS.md, .planning/PROJECT.md, .planning/STATE.md, .planning/ROADMAP.md
- .planning/REVIEW-CHECKLIST.md (eight drift patterns)
- .planning/phases/04-backend-fastapi-add-on/{04-SECURITY,04-VALIDATION,04-VERIFICATION,04-02-SUMMARY}.md
- .planning/phases/05-llm-add-on/{05-CONTEXT,05-SECURITY}.md
- research/00-architecture-overview.md (Mermaid diagram source)
- ~/.claude/get-shit-done/workflows/{secure-phase,validate-phase}.md

---

## Metadata

**Confidence breakdown:**
- release-please config: HIGH — verified against v4 README directly
- asciinema embed: HIGH — GitHub's `<script>` strip is well-established
- FastAPI auth scaffold: HIGH — pattern verified from official FastAPI docs, composes cleanly with Phase 4 LIFO middleware order
- Prompt-injection defenses: MEDIUM — concrete patterns are well-known; the line between "starter scaffold" and "false sense of security" is judgment-call territory (planner should keep R-05-15 acceptance language)
- GHA matrix shape: HIGH — pattern is canonical
- Mermaid arch diagram: HIGH — embed mechanism is documented; the specific shape is derived from in-repo source
- Contributor Covenant: HIGH
- Issue templates: HIGH
- Dual-audience PR template: HIGH — text is sourced verbatim from REQUIREMENTS.md
- Phase 4 audit ceremonies: MEDIUM — files exist; the question is whether STATE.md's "deferred" entry is stale (likely it is)
- act local validation: HIGH
- copier update breaking-change UX: MEDIUM — pattern is sound but "what counts as breaking" is judgment

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (30 days — stable patterns; re-verify version pins on Contributor Covenant, release-please-action, copier before phase execution)
