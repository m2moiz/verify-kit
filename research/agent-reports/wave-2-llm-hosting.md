---
title: LLM Observability Deployment at Solo Scale
aliases: [Wave 2 - LLM Hosting, Langfuse Hosting]
tags: [research, wave-2, llm, hosting, langfuse, hetzner]
wave: 2
source_agent: llm-eval-deployment
created: 2026-05-17
---

# Personal AI Ops Backend for a Solo Dev: Hosting Research

> [!abstract] TL;DR
> **Langfuse Cloud Hobby (free) until you outgrow it, then self-host Langfuse v3 on a Hetzner CX22/CX32 ($4–8/month) using docker-compose. One org per `~`, one project per repo, secrets in `.env` per project, nightly `pg_dump` + ClickHouse backup to Backblaze B2.** Add Promptfoo in CI per repo. Skip Helicone (proxy coupling). Skip vcrpy as *primary* observability (use only for deterministic unit tests).

## 1. Langfuse (self-host or Cloud)

- **Link:** [langfuse.com](https://langfuse.com/) · [self-hosting](https://langfuse.com/self-hosting) · [pricing](https://langfuse.com/pricing)
- **Deployment shape:** Docker Compose bundle of Postgres + ClickHouse + Redis + MinIO + 2 app containers (`web`, `worker`). Also Helm/k8s and managed cloud.
- **Solo-dev cost:**
  - Cloud Hobby: **$0**, 50k events/mo, 30-day retention, 2 users, no card
  - Cloud Core: **$29/mo**, Pro: **$199/mo** (was $59 — bumped in 2026)
  - Self-host Hetzner CX22 (€3.49/mo) or CX32 (€7.59/mo): **~$4–8/mo + ~1–2 hr/mo upkeep**
- **Multi-project support:** Genuine. One org → many projects, each with own public/secret key pair. SDK can route to multiple projects per process. RBAC supported.
- **Backup/upgrade:** You own it. `pg_dump` Postgres nightly, `clickhouse-backup` to S3/B2, `docker compose pull && up -d` for upgrades. v2→v3 migration was non-trivial; v3 now stable.
- **Fit:** **Excellent.** Literally the "personal AI ops backend across many projects" tool.
- **Catch:** v3 dependency stack (PG + ClickHouse + Redis + S3) heavier than indie intuition. Idles ~1.5 GB RAM; ClickHouse is memory hog — CX22 (4 GB) works, CX11 (2 GB) won't. Some features (Prompt Playground, LLM-as-judge in OSS) paywalled.

## 2. Arize Phoenix

- **Link:** [arize.com/phoenix](https://arize.com/phoenix/) · [vs Langfuse FAQ](https://arize.com/docs/phoenix/resources/frequently-asked-questions/langfuse-alternative-arize-phoenix-vs-langfuse-key-differences)
- **Deployment shape:** **Single Docker container**. Optional Postgres for persistence; SQLite works for hobby scale.
- **Solo-dev cost:** **$0 + ~$4/mo VPS**. Setup time ~30 min vs Langfuse's multi-hour first deploy.
- **Multi-project:** Yes via project-tagging on traces (OpenTelemetry resource attribute). Less polished tenant isolation than Langfuse — closer to "tag and filter" than "separate creds per project."
- **Backup/upgrade:** One container, one volume. Trivial.
- **Fit:** **Good** — strong second choice. Pick if you live in OpenTelemetry and notebooks (research/ML feel). Prompt Playground + LLM-as-judge **free** here vs paywalled in Langfuse.
- **Catch:** Project isolation weaker. If you ever want to share a project with collaborator without showing all others, Langfuse's RBAC wins.

## 3. Helicone (proxy)

- **Link:** [helicone.ai](https://www.helicone.ai/) · [self-host docker](https://docs.helicone.ai/getting-started/self-host/docker)
- **Deployment shape:** 5-service stack (Web/Next, Worker/Cloudflare Workers, Jawn/Express, Supabase, ClickHouse, MinIO). Or cloud SaaS with 10k requests/mo free.
- **Multi-project:** Yes via API keys; proxy URLs per project.
- **Backup/upgrade:** Multi-container, frequent image updates (multiple per week). More moving parts than Langfuse.
- **Fit:** **Marginal** for this use case. Proxy mode forces every project to change `base_url` to Helicone. That's coupling you don't want across 15 disparate hobby projects — especially ones using non-OpenAI providers (fal, Pioneer, Tavily) where proxy story weaker.
- **Catch:** Free tier cap (10k req/mo) tight; proxy adds hop on every call; self-hosting heavier than Langfuse for same outcome.

## 4. Promptfoo

- **Link:** [promptfoo.dev](https://www.promptfoo.dev/) · [GitHub Action](https://github.com/promptfoo/promptfoo-action)
- **Deployment shape:** **CLI + GitHub Action**, no backend.
- **Solo-dev cost:** **$0**. CI minutes only.
- **Multi-project:** One config per repo. **No native cross-project aggregation** — write a small script that pushes each run's JSON to S3/Langfuse datasets and aggregates from there.
- **Backup/upgrade:** It's in your repo. `git` is your backup.
- **Fit:** **Excellent — but complementary, not substitute.** Promptfoo answers "did this prompt regress?"; Langfuse answers "what did production actually do?". Use both.
- **Catch:** No aggregated dashboard out of box.

## 5. vcrpy (cassette replay)

- **Link:** [vcrpy docs](https://vcrpy.readthedocs.io/)
- **Deployment shape:** **None.** Pure file fixtures (`*.yaml`) in your repo.
- **Solo-dev cost:** $0.
- **Multi-project:** N/A — fixtures per-project.
- **Backup/upgrade:** `git`. Cassettes usually <1 MB each, so **plain git, not LFS**, until hundreds of MB.
- **Fit:** **Good for unit-test determinism, NO for observability.** Use so CI doesn't burn API credits on every PR. Don't use as "what did my AI do in dev?" answer — opposite question.
- **Catch:** Cassette drift. When upstream API changes (or your prompt changes), cassettes silently lie. Mitigation: delete + re-record on schedule, run one nightly "live" job bypassing cassettes.

## 6. Per-project SQLite + structlog (no central backend)

- **Cost:** $0.
- **Multi-project:** None by definition.
- **Fit:** **Marginal.** Tempting but you'll quickly want one place to see "which project's prompt regressed yesterday." That's exactly what Langfuse gives you for cost of CX22.
- **Catch:** **You'll build a worse Langfuse over six months.** Don't.

## Hosting Target Comparison

| Host | Monthly $ | Setup hours | Notes |
|---|---|---|---|
| **Hetzner CX22 (4 GB)** | ~$4.50 | 1–2 | Best $/RAM. Right size for Langfuse OSS. |
| **Hetzner CX32 (8 GB)** | ~$7.60 | 1–2 | Headroom for ClickHouse. **Recommended for Langfuse v3.** |
| **Fly.io** | ~$10–25 | 1 | Pricing changed 2026, free tier gutted. Volumes per-region locked. Fine for Phoenix (single container), painful for Langfuse multi-service. |
| **Railway** | ~$5 credit + usage | 0.5 | Langfuse has official Railway template — fastest path if you hate ops, but bill creeps past Hetzner once ClickHouse fills. |
| **Render** | ~$7/svc | 0.5 | Multiple services × $7 = expensive for Langfuse stack. |
| **Mac mini at home** | $0 marginal | 0 | Off when you sleep/travel; not "always-on enough" unless wake-on-LAN'd. |

Hetzner wins on $/perf; Railway wins on time-to-running.

## What Anthropic and Vercel Recommend (small scale)

Neither has strong opinion at indie scale. Anthropic's docs point at OpenTelemetry + your-tool-of-choice; internal Claude eval guidance leans on "build small golden-set + run on PRs" (Promptfoo's shape). Vercel's AI SDK ships OTel-compatible tracing surface dropping into Langfuse, Phoenix, or Helicone equally — explicitly do *not* prescribe a backend.

Official recommendation: "instrument with OTel, send wherever." Makes Langfuse and Phoenix natural endpoints — both speak OTel natively.

## Opinionated Recommendation

**Stack:**

1. **Langfuse Cloud Hobby (free)** for first 60 days. Zero ops. 50k events/month plenty for 15 dev-time projects. Each project gets own Langfuse project + key pair stored in that project's `.env`. **(0 hours/month, $0.)**
2. When you hit 50k cap, 30-day retention limit, or want a project private from future collaborator: **migrate to self-hosted Langfuse v3 on Hetzner CX32 (~€7.60/mo)** via docker-compose. One-evening setup using official compose file.
3. **Promptfoo per repo** in `.github/workflows/eval.yml` for prompt-regression gating on PRs. No central backend; let GitHub be dashboard. Optionally push final `results.json` to Langfuse datasets for cross-repo aggregation later.
4. **vcrpy** only for unit tests needing deterministic LLM responses. Commit cassettes as plain git (not LFS) until ~100 MB.
5. **Skip Helicone** — proxy coupling not worth it across heterogeneous providers like fal/Pioneer/Tavily.
6. **Skip Phoenix** unless heavily notebook-based or specifically need free Prompt Playground / LLM-as-judge that Langfuse paywalls.

**Backup/upgrade strategy for self-hosted phase:**
- Nightly cron on VPS: `pg_dump` → gzip → `rclone` to Backblaze B2 (~$0.005/GB/mo)
- `clickhouse-backup` weekly to same B2 bucket
- MinIO bucket also synced to B2
- Upgrade cadence: `docker compose pull && docker compose up -d` monthly, after reading Langfuse changelog. Pin image tags (never `:latest`)
- Disaster recovery: spin fresh CX32, restore Postgres + ClickHouse from B2, re-point DNS. Drill this once.

**Total realistic monthly cost (year 1):**
- Months 1–2: **$0**
- Months 3+: **~$8/mo VPS + ~$1/mo B2 backups ≈ $9/mo**, plus **1–2 hours/month** upkeep
- Compare Langfuse Cloud Pro at $199/mo: self-host pays back within first month

**Honest catch:** if projects run on Railway or Vercel and you have *zero* appetite for VPS ops, stay on Langfuse Cloud Hobby indefinitely and upgrade to Core ($29/mo) when outgrown. Break-even vs self-host time-cost is ~30 min/month of ops. Wrong choice is "let me just write SQLite logs and figure it out later."

## Sources

- [Langfuse self-hosting](https://langfuse.com/self-hosting)
- [Langfuse Docker Compose deployment](https://langfuse.com/self-hosting/deployment/docker-compose)
- [Langfuse pricing](https://langfuse.com/pricing)
- [Self-Host Langfuse with Docker (dev.to)](https://dev.to/signal-weekly/self-host-langfuse-with-docker-llm-observability-without-the-cloud-bill-5cc3)
- [Langfuse v3 Self-Hosting Complete Guide (2026)](https://jangwook.net/en/blog/en/langfuse-self-hosted-llm-tracing-setup-guide-2026/)
- [Langfuse multi-project SDK routing](https://github.com/orgs/langfuse/discussions/11540)
- [Arize Phoenix vs Langfuse FAQ](https://arize.com/docs/phoenix/resources/frequently-asked-questions/langfuse-alternative-arize-phoenix-vs-langfuse-key-differences)
- [Helicone self-host docs](https://docs.helicone.ai/getting-started/self-host/docker)
- [Hetzner Cloud pricing](https://www.hetzner.com/cloud)
- [Promptfoo GitHub Action](https://github.com/promptfoo/promptfoo-action)
- [vcrpy docs](https://vcrpy.readthedocs.io/)
- [Deploy Langfuse v3 on Railway](https://langfuse.com/self-hosting/deployment/railway)

## Related notes

- [[wave-1-llm-eval-frameworks]] · [[wave-2-scaffolding-tools]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
- [[tools/langfuse]] · [[tools/promptfoo]] · [[tools/vcrpy]]
