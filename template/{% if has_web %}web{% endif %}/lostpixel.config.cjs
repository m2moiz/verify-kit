/**
 * Lost Pixel OSS visual-regression config.
 *
 * Capture and verify both run inside:
 *   mcr.microsoft.com/playwright:v1.60.0-jammy (D-W02)
 *
 * Outside-Docker runs are rejected by check_web_lost_pixel() with:
 *   code='web.lost_pixel.docker_unavailable' + suggest `just web-baseline`
 *
 * D-W01: baselines live in-git under web/.lost-pixel/baseline/
 * D-W03: baseline approval = `git add web/.lost-pixel/baseline/<filename>`
 *        (the literal command surfaces via ErrorEnvelope.fix_command → MCP fix_propose())
 *
 * Threshold: 0.01 (1% pixel diff) — tunable per project needs.
 *
 * OSS mode: lostPixelProjectId is undefined (no SaaS account required).
 *
 * CJS format: avoids esbuild TS-config loader path entirely (verify-kit-c7k).
 * Filename lostpixel.config (no hyphen): required by Lost Pixel v3.22 loader
 * (config.js:552 hardcodes this basename — verify-kit-4as).
 */

module.exports = {
  // ── Snapshot targets ────────────────────────────────────────────────────────
  // Full-page snapshot of the gallery root (/) covers all 7 vendored sections.
  // Per-component snapshots via data-lost-pixel-id selectors available in v0.2.x.
  pageShots: {
    pages: [{ path: "/", name: "gallery-full" }],
    // Lost Pixel's built-in docker mode serves the dist/ directory internally
    // at this address when running `lost-pixel docker` or `lost-pixel docker update`.
    baseUrl: "http://localhost:3000",
    waitBeforeScreenshot: 1000,
  },

  // ── Output paths (D-W01: baselines in-git; current/difference gitignored) ──
  imagePathBaseline: "./.lost-pixel/baseline",
  imagePathCurrent: "./.lost-pixel/current",
  imagePathDifference: "./.lost-pixel/difference",

  // ── Threshold: 1% pixel diff allowed (floating point 0.0–100.0) ─────────
  threshold: 0.01,

  // ── OSS mode: no SaaS project ID ────────────────────────────────────────────
  lostPixelProjectId: undefined,
};
