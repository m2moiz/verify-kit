---
title: Game Testing Automation (Godot 4 focus)
aliases: [Wave 1 - Game, Game Testing, Godot Testing]
tags: [research, wave-1, game, godot, testing]
wave: 1
source_agent: game-testing-automation
created: 2026-05-17
---

# Automated Game Testing — Field Guide for Godot 4 Web Dev (2024–2026)

> [!abstract] Headline
> **gdUnit4 + JavaScriptBridge + Playwright** is the canonical Godot 4 HTML5 test stack in 2026. **PlayGodot** (with its purpose-built Claude Code skill) handles desktop dev loops. **GameDriver** is the only commercial tool that natively speaks both Godot and Claude (MCP server shipped in 2025.06 release).

## 1. Godot 4 testing ecosystem: gdUnit4 vs GUT

### gdUnit4 — recommended
- **Link:** https://github.com/godot-gdunit-labs/gdUnit4 · [asset library](https://godotengine.org/asset-library/asset/4390)
- **What:** Embedded unit + scene testing for GDScript and C#. CLI runner, JUnit XML output, HTML reports, mocking, embedded inspector. **Bundles SceneRunner** that simulates input (`set_mouse_position`, `simulate_mouse_button_pressed`, key presses, action holds).
- **Web fit:** Tests run on desktop Godot, not WASM export.
- **Claude loop fit:** **High.** Official [`gdUnit4-action`](https://github.com/MikeSchulze/gdUnit4-action) GitHub Action wraps it in `xvfb` so headless tests with input actually work — biggest practical win over GUT.
- **Catch:** Documentation uneven across versions; `--headless` disabled by default and needs `--ignoreHeadlessMode` for UI tests.

### GUT (Godot Unit Test) — older, lighter
- **Link:** [CI write-up](https://medium.com/@kpicaza/ci-tested-gut-for-godot-4-fast-green-and-reliable-c56f16cde73d)
- Older, lighter framework. Has community **code-coverage** addon (jamie-pate fork) that gdUnit4 lacks.
- **Catch:** Scene-level interaction testing much weaker than gdUnit4's SceneRunner. Bolt on GodotTestDriver to compensate.

### Chickensoft GodotTestDriver
- **Link:** https://github.com/chickensoft-games/GodotTestDriver
- Integration test harness with **node drivers** (Page-Object pattern for scenes), input simulation. C#-focused. NuGet v3.1.x.

**Verdict:** gdUnit4 + GitHub Action is the modern default. GUT wins only if you specifically need code coverage.

## 2. Headless game execution

- **Godot `--headless`** ([forum](https://forum.godotengine.org/t/automated-testing-for-godot-games/118085)): renders nothing, audio off, physics runs. **Cannot process UI input in headless mode** — that's why gdUnit4's action runs everything through `xvfb` (virtual framebuffer). For CI always use `xvfb-run` not pure `--headless`.
- **Unity `-batchmode -nographics`**: production-tier, runs Unity Test Framework (NUnit wrapper). Frame-limit gotcha — set `targetFrameRate=-1` ([partiallydisassembled](https://partiallydisassembled.net/posts/unity-headless.html)).
- **Unreal Automation Framework + Gauntlet** ([docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/gauntlet-automation-framework-in-unreal-engine)): two-layer system. Andrew Fray's [2025 topography post](https://andrewfray.wordpress.com/2025/04/09/the-topography-of-unreal-test-automation-in-2025/) is the canonical map.

**Takeaway:** budget time for `xvfb-run` in CI. Don't trust `--headless` alone to fire input events.

## 3. AI bots / scripted agents that actually play games

- **EA SEED — Imitation Learning** ([overview](https://www.ea.com/seed/news/seed-ml-research-aaa-game-testing), [MultiGAIL](https://www.ea.com/seed/news/seed-cog2023-multimodal-adversarial-imitation-learning)): production usage. Battlefield 2042 shipped SEED path-following improvement (39% reduction in stuck-vehicle time). Not available to indies.
- **Ubisoft La Forge** ([R6 Siege bots](https://news.ubisoft.com/en-us/article/1MlKnolSLJFuJDnATWiorr/how-rainbow-six-siege-developed-ai-that-acts-like-real-players)): 22-engineer automation team. Internal.
- **modl.ai / modl:test** ([site](https://modl.ai/)): commercial behavioral-AI QA. "Integrationless" play-testing bots. Unity/Unreal focus.
- **GameDriver** ([site](https://gamedriver.ai/) · [2025.06 release](https://www2.gamedriver.io/gamedriver-blog-news-updates/2025.06-release-update)): Quality-as-a-Service across Unity, Unreal, **Godot**, Frostbite, Snowdrop. **As of 2025.06 ships a local MCP server for Claude** — the most directly relevant tool. Paid (enterprise).

**Indie takeaway:** SEED/La Forge research inspirational but not buyable. GameDriver is the only commercial option that lists Godot support AND speaks MCP/Claude.

## 4. Game ↔ external test harness bridges (HTML5/WASM)

### Pattern A: JavaScriptBridge + Playwright (canonical)
- **Link:** [Godot docs](https://docs.godotengine.org/en/stable/tutorials/platform/web/javascript_bridge.html)
- Use `JavaScriptBridge.eval("window.__game = {...}", true)` to publish state on `window`. Register callbacks with `create_callback()` for JS→Godot commands. Playwright then calls `page.evaluate(() => window.__game.getState())` and `page.evaluate(() => window.__game.simulate('jump'))`.
- **Fit:** **High** — Playwright snapshots + state JSON give a coding agent something to assert on.
- **Catch:** Canvas opaque to DOM-based selectors. *You* must design state-export and command surface; nothing auto-generates it.

### Pattern B: PlayGodot
- **Link:** https://github.com/Randroids-Dojo/PlayGodot
- "Playwright for Godot." Python client talks to Godot's RemoteDebugger over TCP 6007 using Godot's binary Variant format. Supports `get_node`, `get_property`, `set_property`, `call_method`, `screenshot`, input injection. Ships a [Claude Code skill](https://github.com/randroids-dojo/godot-claude-skills).
- **HTML5 fit:** **No** — RemoteDebugger isn't available in browser WASM. PlayGodot drives **desktop** Godot runs.
- **Catch:** Requires patched Godot engine branch (their `automation` fork).

**Recommendation:** use **both**. PlayGodot drives dev/CI loop on desktop; JavaScriptBridge + Playwright validates actual web build.

## 5. Visual regression for games

Game industry consensus ([8th Light](https://8thlight.com/insights/machine-learning-visual-validation-game-devops)): pixel-diff tools like SSIM/pixelmatch fail on real game frames (animation, particles, GPU driver differences).

- **Pixelmatch with high threshold + masked regions** — works for static UI screens, title cards, menus, deterministic 2D pixel-art frames
- **Freeze time + force fixed seed before snapshot** — disable particles, pin RNG
- **Perceptual hash (pHash)** instead of per-pixel diff

**For 2D pixel-art roguelike specifically you're lucky** — pixel art has hard edges, no antialiasing, often integer-scaled, so plain pixelmatch works if you pin level seed and snapshot at known frames.

## 6. Record / replay / determinism

No first-class Godot solution. Common pattern ([forum](https://forum.godotengine.org/t/how-to-record-and-replay-game-events-demo-files/20626), [Godot 4.5 replay example](https://docs.godotengine.org/en/4.5/getting_started/first_3d_game/08.score_and_replay.html)):
- Singleton records `(frame_number, input_event)` tuples to JSON
- Replay pushes events via `Input.parse_input_event()` on matching frame in `_physics_process` (fixed delta = deterministic)
- Use `Engine.physics_ticks_per_second` and fixed seed for `RandomNumberGenerator`

True frame-perfect determinism requires: (a) drive everything off `_physics_process` not `_process`, (b) seed every RNG, (c) avoid `randf()` global state across systems.

**For agent's purposes:** record a baseline run once, replay every CI build, assert on final game state JSON — that's the achievable target.

## 7. Honest state of "AI testing" for games

Cutting through vendor copy ([Qase](https://qase.io/blog/ai-test-automation-hype/), [MIT TR](https://www.technologyreview.com/2025/12/15/1129174/the-great-ai-hype-correction-of-2025/)):

- **Real and shipping:** ML-prioritized regression suites, LLM-assisted test *authoring*, behavioral bots for *balance* exploration in big online games
- **Still hype:** "AI generates test cases from user behavior" — promised for years, brittle in practice. Self-healing tests for game UIs — works for web, weak for canvas-rendered games
- **For indie:** realistic AI angle is *Claude writes and maintains deterministic test suite for you*, not *ML agent plays game and finds bugs autonomously*

## Recommendation: solo Godot 4 web-game dev in 2026

In priority order:

1. **gdUnit4 + official `gdUnit4-action` GitHub Action** — non-negotiable foundation. SceneRunner for input-driven scene tests; xvfb handling already solved.
2. **A `JavaScriptBridge`-based "test API"** — write a `TestHarness` autoload that exposes `window.__game.getState()`, `__game.loadSeed(n)`, `__game.simulate(action)`, `__game.advance(frames)`. Two hours of work, pays back forever.
3. **Playwright driving the HTML5 export** in CI — call `window.__game` API, screenshot at known checkpoints, diff with pixelmatch.
4. **Deterministic replay**: record input as `(physics_frame, action)` JSON, replay in `_physics_process`, assert on final state JSON. Pin every RNG seed.
5. **PlayGodot for desktop dev loop** (optional) — its Claude Code skill lets agent drive desktop Godot directly during development.

**Explicitly skip:** modl.ai/GameDriver (enterprise pricing), ML-based test generation (not real for indies), SSIM/perceptual visual diff (overcomplicated for pixel art).

## Sources

- [gdUnit4 repo](https://github.com/godot-gdunit-labs/gdUnit4)
- [gdUnit4 GitHub Action](https://github.com/MikeSchulze/gdUnit4-action)
- [CI-tested GUT for Godot 4 — Kpicaza](https://medium.com/@kpicaza/ci-tested-gut-for-godot-4-fast-green-and-reliable-c56f16cde73d)
- [Chickensoft GodotTestDriver](https://github.com/chickensoft-games/GodotTestDriver)
- [PlayGodot](https://github.com/Randroids-Dojo/PlayGodot)
- [Randroids-Dojo Godot Claude skills](https://github.com/randroids-dojo/godot-claude-skills)
- [Godot JavaScriptBridge docs](https://docs.godotengine.org/en/stable/tutorials/platform/web/javascript_bridge.html)
- [EA SEED — ML for AAA game testing](https://www.ea.com/seed/news/seed-ml-research-aaa-game-testing)
- [GameDriver 2025.06 release with Claude MCP](https://www2.gamedriver.io/gamedriver-blog-news-updates/2025.06-release-update)
- [Unreal Gauntlet docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/gauntlet-automation-framework-in-unreal-engine)
- [8th Light — ML visual validation in game DevOps](https://8thlight.com/insights/machine-learning-visual-validation-game-devops)
- [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots)
- [Qase — AI test automation hype vs real](https://qase.io/blog/ai-test-automation-hype/)

## Related notes

- [[wave-1-general-verification-harnesses]] · [[wave-1-audio-testing]]
- [[00-architecture-overview]] · [[00-stack-decisions]]
- Used in v0.2 Game add-on (not v0.1)
