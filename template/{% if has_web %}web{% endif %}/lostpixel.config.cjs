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
    // host.docker.internal resolves to the Docker host on macOS/Windows (Docker
    // Desktop) and on Linux with --add-host=host.docker.internal:host-gateway.
    // web-baseline serves dist/ via `vite preview --port 3000` on the host
    // before invoking `lost-pixel docker update`, which runs inside a container
    // and uses this URL to reach the host-side gallery.
    baseUrl: "http://host.docker.internal:3000",
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

  // ── Exit non-zero on differences (required for check to catch regressions) ─
  // failOnDifference: when diffs are found AND generateOnly=true, Lost Pixel
  // calls exitProcess with no exitCode → defaults to exit 1 (runner.js).
  // Without failOnDifference=true, `lost-pixel docker` always exits 0 — a
  // silent no-op that would never catch visual regressions.
  // generateOnly: true forces the exit-1-on-diff code path in runner.js.
  // (The "generateOnly mode" label in lost-pixel's logs refers to non-SaaS
  // operation, not whether this flag is set. Both flags are required together.)
  failOnDifference: true,
  generateOnly: true,
};
