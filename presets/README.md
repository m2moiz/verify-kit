# Presets

Preset files let you skip the interactive copier prompts by providing pre-filled
answers. Instead of typing 12+ answers each time you scaffold a new project, run:

```sh
copier copy --data-file presets/personal.local.yml gh:m2moiz/verify-kit my-app
```

---

## The Two-File Convention

Two public preset files live in this directory:

| File | Purpose | Committed? |
|------|---------|------------|
| `personal.yml` | PII-free placeholder template — shows every key with safe placeholder values (`"Your Name Here"`, `"you@example.com"`). Copy it to create your own `.local.yml`. | Yes (no PII) |
| `oss-minimalist.yml` | Matches the `default:` values in `copier.yml`. Good starting point for OSS forks. | Yes (no PII) |
| `personal.local.yml` | Your real personal values — PII-bearing, gitignored. **Never commit.** | **No** |

---

## The `.local.yml` Pattern for Personal Use

1. Copy the placeholder template:
   ```sh
   cp presets/personal.yml presets/personal.local.yml
   ```
2. Edit `presets/personal.local.yml` with your real values (name, email, preferred add-ons).
3. Invoke copier with `--data-file`:
   ```sh
   copier copy --data-file presets/personal.local.yml gh:m2moiz/verify-kit /path/to/new-project
   ```

The `.local.yml` suffix is gitignored (see `.gitignore`). You will never accidentally
commit it, even with `git add .`.

---

## Invocation Syntax

Full invocation (D-W12 — `--data-file` flag, confirmed in 07-RESEARCH.md):

```sh
copier copy --data-file presets/personal.local.yml gh:m2moiz/verify-kit /path/to/new-project
```

Or copy the template locally first:

```sh
git clone gh:m2moiz/verify-kit verify-kit-local
copier copy --data-file verify-kit-local/presets/personal.local.yml verify-kit-local /path/to/new-project
```

Copier `9.15+` validates `--data-file` as an existing file path; the path must exist
on disk at invocation time.

---

## PII Grep + Bypass Story

A pre-commit hook (`scripts/check_preset_pii.sh`) runs on any staged `presets/*.yml`
file. It greps for:

- **Email patterns**: standard `user@domain.tld` format. Allowlist: `example.com` and
  `example.org` are not blocked (the placeholder `you@example.com` is intentional).
- **Maintainer-name regex**: configurable at the top of `scripts/check_preset_pii.sh`
  (disabled by default — forks can enable it by uncommenting one line).

If PII is found, the commit is blocked with a message like:

```
PII detected in presets/personal.local.yml:5: real.name@gmail.com
If this is intentional, commit with --no-verify (documented in presets/README.md).
```

**Bypass:** `git commit --no-verify` skips all pre-commit hooks. This is documented
and intentional — but discouraged. Use `.local.yml` files (gitignored) instead of
bypassing the hook.

---

## How to Add a New Preset

Example: an `oss-maximalist.yml` with every add-on enabled.

1. Copy `personal.yml` as a starting point:
   ```sh
   cp presets/personal.yml presets/oss-maximalist.yml
   ```
2. Edit the file. Set `has_backend: true`, `has_llm: true`, `has_web: true`, etc.
3. Replace placeholder identity values with appropriate OSS defaults.
4. Ensure `_schema_version: "0.2"` is present. Update the value if `copier.yml`
   prompts have changed since the last `_schema_version` bump.
5. If you want CI to self-validate this preset, add a matrix row to
   `.github/workflows/template-selftest.yml` (see the `+web+oss-minimalist-preset`
   pattern in that file as a template).
6. Run `bash scripts/check_preset_pii.sh presets/oss-maximalist.yml` to confirm
   the PII hook passes before committing.
