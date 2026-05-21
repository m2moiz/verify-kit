---
title: Next.js + React Frontend DX Ecosystem
aliases: [Wave 4 - Next.js, Web Add-on, React Tooling]
tags: [research, wave-4, nextjs, react, frontend, web]
wave: 4
source_agent: nextjs-react
created: 2026-05-17
---

# Next.js + React Frontend DX Ecosystem 2024–2026 — Research for Web Add-on

> [!abstract] Headline
> **12 ship-by-default libs** for the Web add-on. Standouts: **Vitest 4 browser mode** (stable Oct 2025 — single runner for unit AND real-DOM component tests via Playwright/CDP), **MSW** (network-level mocking in browser + Vitest + Node), **nuqs** (URL state = agent drives UI by URL alone, no clicks), **Biome** (10–25× faster than ESLint+Prettier; Next 15.5 ships official support). Scaffold drops **`window.__VERIFY_KIT__`** dev global exposing app state for agent introspection.

## 1. Next.js 15/16 Essentials

- **Turbopack** — now **default bundler** for `next dev` AND `next build` in Next.js 16 (Oct 2025), with stable filesystem caching in 16.1 (Dec 2025). `--turbo` flag is dead weight; it's just `next dev` now. On vercel.com codebase: ~77% faster server startup, ~96% faster Fast Refresh. **No-brainer ship**
- **`instrumentation.ts`** — auto-detected since Next.js 15 (drop any `experimental: { instrumentationHook: true }`). Define `register()` to bootstrap OpenTelemetry. Pair with `@vercel/otel` (`registerOTel({ serviceName: 'app' })`) — official, opinionated. **Known gotcha:** `fetch()` context propagation still misses sending `traceparent` to downstream services in some configurations; workaround is `opentelemetry-instrumentation-fetch-node` or manual header injection. **Ship by default in Web add-on**
- **Error overlay** — Next 15+ ships redesigned overlay with stack frame source mapping, copy-as-markdown buttons, AI-assistant deeplinks. Human-only; agents read terminal output of `next dev` or Sentry events
- **React Scan vs Million Lint** — complementary, not competitors. **React Scan** (MIT, free, by Aiden Bai) is lightweight runtime overlay highlighting re-renders. **Million Lint** is paid VS Code extension doing static analysis. **`react-doctor`** is new sibling targeted at AI-written React. Ship: **React Scan as dev dep, opt-in**

## 2. Component Dev Tooling

- **Storybook 9/10** unified its test story with `@storybook/test` (Playwright-driven play functions + a11y addon) and is the only one with serious automated-test story. Cold start ~8s vs Ladle's ~1.2s. **Ship Storybook 9 as opt-in via `--with-storybook` flag**
- **Ladle** — React-only, Vite-native, no automated-test integration
- **Histoire** — Vue/Svelte-focused (skip for React)
- **TanStack Devtools** — React Query v5 devtools rewritten framework-agnostic. Free, OSS, dev-only build. Ship: **always-on dev dep when TanStack Query installed**

## 3. Error Tracking & Runtime Visibility

- **Sentry Next.js SDK** — `withSentryConfig` auto-uploads source maps on `next build`. Free tier covers solo workloads (5k errors/mo). Critical for agents: Sentry MCP / API lets agent fetch latest error and stack trace as JSON. **Ship: opt-in via flag** (requires SENTRY_DSN)
- **PostHog** — best free tier (5k web replays + 2.5k mobile + 1M events/mo). Session replay human-debugging-only but event stream structured. **HighlightIO is dead** (LaunchDarkly acquisition March 2025). **OpenReplay** self-hosted choice if PostHog cloud unacceptable. Ship: **document PostHog, don't install**
- **Console Ninja** — VS Code extension streaming `console.log`/runtime errors inline. Human-only; agents read terminal. Skip from scaffold
- **Replay.io** — time-travel browser recordings. Excellent for human bug repros; paid + heavy. Skip
- **Error Boundary in React 19** — `createRoot(node, { onCaughtError, onUncaughtError, onRecoverableError })` are new root-level hooks. `react-error-boundary` package still works for declarative `<ErrorBoundary fallback={...}>`. Ship: **scaffold root-level `onUncaughtError` forwarding to `window.__VERIFY_KIT__.errors`** plus default `react-error-boundary` wrapper

## 4. Testing (agent-friendly)

- **Vitest 4** — released Oct 2025, **browser mode now stable**. Runs tests inside real Chromium via Playwright (`@vitest/browser-playwright`). Combined with `vitest-browser-react` you get React component tests in real DOM with real events (CDP-based, not jsdom synthetic). **Single biggest agent-DX win of 2025** — same runner for unit, browser-DOM, integration; one JSON reporter agent can parse. Ship: **always**
- **`@testing-library/react` + `userEvent`** — consensus fully shifted to `userEvent` over `fireEvent`. Ship: **always**
- **Playwright vs Cypress** — Playwright is unambiguous 2025–2026 default for E2E. Cypress still wins *interactive component-testing* niche, but Vitest browser mode largely eats it. Use Playwright for E2E, Vitest browser mode for component. **`@playwright/test`** parallelizes by file via `fullyParallel: true` + `workers: '50%'`. Ship: **always**
- **MSW (Mock Service Worker)** — the *magic* library. Service-worker-based request interception works in browser dev, Vitest browser mode, AND Node tests with `msw/node`. **Critical limitation just fixed:** SSR/server-side fetch mocking was broken in Next 14 App Router; **Next 15+ works**. Ship: **always**. Bonus: same handler file becomes "offline demo" agent can run without backend keys

## 5. Visual + Accessibility Verification

- **Argos** — free tier exists, integrates as Playwright reporter (`@argos-ci/playwright`). Better fit than Chromatic for app screenshots. Ship: **opt-in via `--with-visual-regression`**
- **Chromatic** — Storybook-native; only worth it if Storybook shipped
- **`@axe-core/playwright`** — runs axe in any Playwright test, catches ~57% of WCAG issues automatically (Deque 2025 study). Ship: **always** — structured violation arrays agent can parse
- **Lighthouse CI** — performance budgets + accessibility floor. Heavyweight. Ship: **opt-in via `--with-perf-budget`**
- **Pa11y** — older, axe-core preferred now. Document, don't install

## 6. API Client + End-to-End Types

- **`openapi-typescript` + `openapi-fetch`** — generate types from any OpenAPI spec (FastAPI emits natively at `/openapi.json`). `openapi-fetch` is 5 kB type-safe fetch wrapper. **This is right default when backend is Python/FastAPI** (user's stack: dexters-laboratory, dexter-plan-forge). Ship: **always when backend OpenAPI URL configured**
- **Hey API (`@hey-api/openapi-ts`)** — spiritual successor, plugin-architected, used by Vercel/OpenCode/PayPal. Document as upgrade path
- **Orval** — still solid, generates hooks by default, has built-in mock generation. Document, don't install
- **tRPC** — only worth it for *TypeScript-on-both-sides* monorepos. With FastAPI backends, OpenAPI is right pick. **`oRPC` v1** (Dec 2025) is newer middle ground — worth watching but too young to default
- **TanStack Query v5** — server state default. Ship: **always**
- **Zod** — universal validator; shared between client/server when both TS. Pair with `openapi-zod-client` if backend is Python. Ship: **always**

## 7. Form Handling

- **`react-hook-form` + Zod** — boring, correct default. 12M weekly downloads, performant uncontrolled-input model. Ship: **always**
- **TanStack Form** — only if forms deeply nested/dynamic with hard TS requirements
- **Conform** — Next.js–native, designed around Server Actions and progressive enhancement. Ship if project explicitly does PE; otherwise skip

## 8. UI Primitives + Design System

- **shadcn/ui + Radix Primitives + Tailwind v4** — 2025–2026 default React stack. shadcn CLI now initializes Next.js 15 with Tailwind v4 + React 19 out of box. **Tailwind v4** key change: configuration via CSS (`@theme` directive in stylesheet), not `tailwind.config.js`. Uses Rust-based Oxide engine. Ship: **always — this is scaffold's UI foundation**
- **MagicUI / Aceternity** — copy-paste animated React components. Worth it for portfolio polish. Document, don't install
- **Headless UI / Park UI / Catalyst** — alternatives. Skip from scaffold; shadcn won default war

## 9. State Management

- **Zustand** — default client state. ~2 kB, hook API, no Context performance pitfalls. Ship: **always**
- **Jotai** — atomic state, complementary to Zustand for fine-grained reactivity. Document as opt-in
- **TanStack Query** — server state (see §6). Ship: always
- **nuqs** — type-safe URL search-param state (`useQueryState` API). Adopted by Sentry, Supabase, Vercel, Clerk. 6 kB gzipped. Excellent for share-as-link debugging and **agent-friendly: agent can drive UI state purely via URL** (no clicks needed for many flows). Ship: **always for App Router projects**

## 10. Build-time + Dev-time Checks

- **Biome vs ESLint** — Next.js 15.5 (Aug 2025) **officially shipped Biome support** alongside ESLint, with migration codemod. Biome is 10–25× faster and replaces both ESLint + Prettier. Catch: ~250 lint rules vs ESLint's 1000+ (security plugins not yet covered). Ship: **Biome by default**, document ESLint as opt-out for plugin-heavy codebases
- **Knip** — replaces `unimported` (archived), `depcheck`, `ts-prune` in one tool. Finds unused files, deps, exports, members. Ship: **always — runs in `just lint`**
- **`@next/bundle-analyzer`** — first-party, outputs `client.html`/`edge.html`/`nodejs.html`. Ship: **always (dev dep, `ANALYZE=true npm run build`)**
- **`size-limit`** — performance budgets in CI, exits non-zero on regression. Pairs with `bundle-analyzer`. Ship: **always**

## 11. AI-Specific Frontend Libraries

- **Vercel AI SDK v5** — `useChat` now transport-based (SSE-standard), distinguishes `UIMessage` from `ModelMessage`, supports streaming tool inputs. Required for any LLM frontend. Ship: **opt-in via `--with-ai-sdk`** (most projects don't need it)
- **`assistant-ui`** — TS/React chat UI on shadcn + Tailwind. **Caveat:** original maintainers stepped back May 2025, now community-maintained. Document, don't install
- **CopilotKit** — full agent-UI platform with AG-UI protocol (Google/LangChain/AWS adopters). Freemium. Document for users who want agentic UIs

## 12. Frontend Trace Propagation

The wiring: `@vercel/otel` + `@opentelemetry/sdk-trace-web` + `@opentelemetry/instrumentation-fetch` in `instrumentation-client.ts` (Next 15+ supports client-side instrumentation entry). Fetch instrumentation auto-injects `traceparent` headers so button-click span becomes parent of backend FastAPI span. **Real gotcha** (open Vercel issue #107 + Next discussion #54877): server-side `fetch()` inside RSC doesn't always propagate `traceparent` — verify with `NEXT_OTEL_VERBOSE=1`. Ship: **always when backend has OTel collector**

## 13. Dev-Mode Polish Patterns

- **Sonner** — replaced `react-hot-toast` as default since shadcn adopted it. 47M weekly downloads vs react-hot-toast's 4.8M. Ship: **always**
- **`@uidotdev/usehooks`** — quality hook recipes (useDebounce, useLocalStorage, useIntersectionObserver). Ship: **always (zero cost, devs reach for it daily)**
- **`__VERIFY_KIT__` global** — the agent-superpower. Dev-only `window.__VERIFY_KIT__` namespace exposing: `errors[]` (from `onUncaughtError`), `routes()` (App Router state), `queries()` (TanStack Query cache snapshot), `state()` (Zustand stores), `dumpA11y()` (run axe synchronously). Agent dumps via `agent-browser run-code "JSON.stringify(window.__VERIFY_KIT__.snapshot())"` — sub-second app introspection without scraping DOM

---

## (A) Web Add-on Stack for verify-kit v0.2

### Always Ship (12 libraries)

| # | Library | One-line rationale |
|---|---|---|
| 1 | **Next.js 16 + React 19 + Turbopack** | Default framework; Turbopack stable for build + dev |
| 2 | **TypeScript + Biome** | Lint+format in one Rust binary, 10–25× faster than ESLint+Prettier |
| 3 | **Tailwind v4 + shadcn/ui + Radix** | CSS-first theming, copy-paste components, accessible primitives |
| 4 | **Vitest 4 (browser mode) + vitest-browser-react** | Single runner for unit + real-DOM component tests via Playwright/CDP |
| 5 | **@testing-library/react + userEvent** | Real user-event sequences, not synthetic fireEvent |
| 6 | **Playwright + @axe-core/playwright** | E2E + a11y in one runner, structured JSON output for agents |
| 7 | **MSW** | Network-level mocking that works in browser dev, Vitest, and Node |
| 8 | **TanStack Query v5 + devtools** | Server-state default; mutation observability included |
| 9 | **Zustand + nuqs** | Client state (Zustand) + URL state (nuqs) — agent can drive via URL alone |
| 10 | **react-hook-form + Zod** | Boring correct form default |
| 11 | **Sonner + @uidotdev/usehooks** | Toast (shadcn default) + standard hook recipes |
| 12 | **@vercel/otel + @opentelemetry/instrumentation-fetch + Sentry SDK** | Traces propagate to backend, errors land in Sentry, source maps auto-uploaded |

Plus scaffold drops: `instrumentation.ts` with OTel, root-layout `<ErrorBoundary>` + `onUncaughtError` wiring to `window.__VERIFY_KIT__`, `mocks/handlers.ts` MSW skeleton, `tests/smoke.spec.ts` Playwright file, `justfile` with `just smoke`/`just lint`/`just test`/`just analyze`.

### Opt-in via flag

- `--with-storybook` → Storybook 9 + `@storybook/test` + Chromatic config
- `--with-visual-regression` → Argos CI (Playwright reporter)
- `--with-perf-budget` → Lighthouse CI + size-limit thresholds
- `--with-ai-sdk` → Vercel AI SDK v5 + assistant-ui starter route
- `--with-openapi` → openapi-typescript + openapi-fetch + codegen task wired to backend OpenAPI URL
- `--with-react-scan` → dev-only React Scan overlay
- `--with-posthog` → PostHog session replay + event tracking

### Document but don't install

Hey API, Orval, tRPC, oRPC, TanStack Form, Conform, Jotai, CopilotKit, Million Lint, Replay.io, Console Ninja, OpenReplay, Pa11y, Histoire, Ladle, MagicUI, Aceternity, react-error-boundary (only if you want declarative scoping beyond root hook).

## (B) `just smoke` Output Mockup

```
$ just smoke
────────────────────────────────────────────────────────────────────
  verify-kit smoke · dexter-plan-forge · web add-on v0.1.3
  target: http://127.0.0.1:3000  ·  backend: http://127.0.0.1:8000
────────────────────────────────────────────────────────────────────

[1/6] preflight                                                  ok
      • next 16.1.2 detected (turbopack default)
      • backend /health → 200 in 12ms
      • OTel collector reachable at http://127.0.0.1:4318
      • MSW handlers: 14 registered (offline mode: disabled)

[2/6] type-check + lint (biome + tsc + knip)                     ok
      • biome     249 files  ·  0 errors  ·  0 warnings  · 71ms
      • tsc       0 errors                                · 1.4s
      • knip      0 unused files · 0 unused deps · 0 unused exports

[3/6] vitest (browser mode, chromium via playwright)             ok
      Test Files  18 passed (18)
      Tests       142 passed (142)
      Duration    4.71s
      Coverage    lines 87.2%  ·  branches 81.4%  ·  funcs 91.1%

[4/6] playwright e2e + a11y                                    FAIL
      ✓ landing-page.spec.ts          (3 tests, 2.1s)
      ✓ auth-flow.spec.ts             (5 tests, 4.7s)
      ✗ plan-editor.spec.ts › saves plan after edit
        screenshots: tests/__screenshots__/plan-editor-save.png
        trace:        playwright-report/trace-plan-editor-save.zip
      ✓ search-state-via-nuqs.spec.ts (4 tests, 1.8s)
      a11y: 0 critical · 0 serious · 1 moderate · 3 minor

      ┌─ error[E_PLAN_SAVE] save button click did not persist plan ─┐
      │                                                             │
      │ tests/plan-editor.spec.ts:42:5                              │
      │                                                             │
      │  40 │   await page.getByRole('textbox',{name:'title'})      │
      │     │     .fill('Refactor auth layer');                     │
      │  41 │   await page.getByRole('button',{name:'Save'}).click();│
      │  42 │   await expect(page.getByText(/saved/i))               │
      │     │     ────────────────────────────────                  │
      │     │     ^^^ expected text "saved" within 5000ms           │
      │  43 │     .toBeVisible({ timeout: 5000 });                  │
      │                                                             │
      │  agent-browser refs at failure:                             │
      │     @e3  button[name="Save"]      (clicked, visible)        │
      │     @e7  toast region              (empty)                  │
      │     @e9  errors panel              ["POST /api/plan 422"]   │
      │                                                             │
      │  __VERIFY_KIT__ snapshot:                                   │
      │    queries.mutations[0].state = 'error'                     │
      │    queries.mutations[0].error.body =                        │
      │       { "detail": "title.length must be ≤ 40" }             │
      │                                                             │
      │ help: backend rejected payload — title is 42 chars,         │
      │       limit is 40. Either fix the test fixture              │
      │       (tests/fixtures/plans.ts:12) or relax the             │
      │       backend constraint (backend/app/models/plan.py:18).   │
      └─────────────────────────────────────────────────────────────┘

[5/6] visual regression (argos)                                  ok
      • 12 screenshots compared  ·  0 diffs  ·  baseline: main@a3f91c2

[6/6] bundle budget (size-limit)                                 ok
      • app/page.js              42.1 kB / 50 kB    ok
      • app/dashboard/page.js    78.4 kB / 100 kB   ok
      • total first-load         184  kB / 200 kB   ok

────────────────────────────────────────────────────────────────────
  RESULT: FAIL  ·  1 of 6 phases failed  ·  total 14.2s
  artifacts: .verify-kit/last-run/
    ├── playwright-report/         (open with: just smoke-report)
    ├── screenshots/               (annotated PNGs, agent-readable)
    ├── coverage/                  (lcov + html)
    ├── trace.json                 (OTel spans, frontend → backend)
    └── verify-kit-snapshot.json   (__VERIFY_KIT__ dumps per test)
────────────────────────────────────────────────────────────────────
```

Notes:
- **miette-style box** renders same whether human or agent reads
- **`agent-browser refs`** let agent re-attach to `@e3`/`@e7`/`@e9` without re-snapshotting
- **`__VERIFY_KIT__` snapshot** is high-signal payload — TanStack Query mutation state pinpoints 422 instantly
- **artifacts paths** absolute under `.verify-kit/last-run/` so agent always knows where to look

## Sources

- [Next.js 16 release notes](https://nextjs.org/blog/next-16)
- [Next.js Turbopack stable](https://nextjs.org/blog/turbopack-for-development-stable)
- [Next.js OpenTelemetry guide](https://nextjs.org/docs/app/guides/open-telemetry)
- [@vercel/otel docs](https://vercel.com/docs/tracing/instrumentation)
- [React Scan](https://github.com/aidenybai/react-scan)
- [Storybook adoption guide (LogRocket)](https://blog.logrocket.com/storybook-js-adoption-guide/)
- [Vercel AI SDK 5](https://vercel.com/blog/ai-sdk-5)
- [Playwright vs Cypress (BugBug 2026)](https://bugbug.io/blog/test-automation-tools/cypress-vs-playwright/)
- [MSW + Next.js App Router guide](https://gimbap.dev/blog/setting-msw-in-next)
- [Hey API openapi-ts](https://github.com/hey-api/openapi-ts)
- [shadcn/ui Tailwind v4](https://ui.shadcn.com/docs/tailwind-v4)
- [nuqs docs](https://nuqs.dev/)
- [Knip comparison](https://knip.dev/explanations/comparison-and-migration)
- [Argos CI](https://argos-ci.com/)
- [React 19 release notes](https://react.dev/blog/2024/12/05/react-19)
- [Biome vs ESLint 2026](https://www.pkgpulse.com/guides/biome-vs-eslint-vs-oxlint-2026)
- [Next.js 15.5 Biome migration](https://www.tsepakme.com/blog/nextjs-biome-migration)
- [Sentry Next.js source maps](https://docs.sentry.io/platforms/javascript/guides/nextjs/sourcemaps/)
- [Vitest Browser Mode](https://vitest.dev/guide/browser/)
- [axe-core + Playwright in CI](https://rishikc.com/articles/accessibility-testing-ci-integration/)
- [Zustand vs Jotai vs Valtio 2025](https://www.reactlibraries.com/blog/zustand-vs-jotai-vs-valtio-performance-guide-2025)
- [tRPC vs OpenAPI](https://medium.com/@Modexa/ship-faster-with-type-safe-apis-trpc-vs-openapi-9aa977b4331b)
- [TanStack Query v5 devtools](https://tanstack.com/query/v5/docs/framework/react/devtools)
- [Sonner vs react-hot-toast (LogRocket)](https://blog.logrocket.com/react-toast-libraries-compared-2025/)

## Related notes

- [[wave-4-fastapi-ecosystem]] · [[wave-4-mcp-agent-integration]] · [[wave-1-general-verification-harnesses]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
- Used in v0.2 Web add-on
