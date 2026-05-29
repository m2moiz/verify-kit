/**
 * SSE EventSource E2E assertion — DEV-W03 / ROADMAP SC-2 (second half).
 *
 * This spec verifies that a browser EventSource receives a server-sent event
 * from the live FastAPI backend within 3 seconds.
 *
 * POLARITY NOTE: This spec ships ONLY in the has_web + has_backend polarity.
 * events.ts is excluded by copier.yml when has_backend=false, so this spec is
 * also excluded under the same guard (see Task 2 / copier.yml _exclude).
 *
 * ENDPOINT + EVENT-NAME CONTRACT (verify-kit-usi):
 *   The target is http://localhost:8000/events/stream — the app's demo SSE
 *   route (app/api.py), which emits a short burst of NAMED `tick` events:
 *       event: tick
 *       data: 0
 *   SSE semantics: `EventSource.onmessage` fires ONLY for the DEFAULT (unnamed)
 *   `message` event. A NAMED event (`event: tick`) dispatches to
 *   `addEventListener("tick", ...)` and NEVER to `onmessage`. This spec therefore
 *   listens for the named `tick` event the server actually sends. (An earlier
 *   version waited on `onmessage` against /__debug/events, which emits only a
 *   single named `empty` event and then closes the stream — so onmessage never
 *   fired and the assertion timed out / errored under a live backend.)
 *   We use /events/stream rather than /__debug/events because it emits multiple
 *   events over time (a genuine streaming assertion) and is always mounted, not
 *   gated on a .verify/events.jsonl file existing.
 *
 *   The absolute URL bypasses Vite's dev-proxy buffering (Pitfall §5); CORS for
 *   the preview origin (:4173) is configured in app/main.py + app/settings.py.
 *
 * REQUIREMENTS: A running FastAPI backend (uvicorn on :8000) with the
 * /events/stream demo SSE endpoint. This spec is an integration test against
 * that live dependency: it probes the backend first and SKIPS (does not fail)
 * when :8000 is unreachable, so the frontend `just verify` passes standalone.
 * The live event assertion runs whenever a backend is up — local dev
 * (`just dev`), or a full-stack run that starts uvicorn before Playwright.
 * Skip ≠ pass: a skipped run means the assertion was not exercised, not that
 * SSE works.
 */
import { test, expect } from "@playwright/test";

const SSE_URL = "http://localhost:8000/events/stream";
const HEALTH_URL = "http://localhost:8000/healthz";

test("SSE EventSource receives a tick event within 3 seconds", async ({ page, request }) => {
  // Probe the backend; skip (not fail) when it is not reachable. A frontend
  // `just verify` must not hard-require a live backend on a fixed port.
  let backendUp = false;
  try {
    const resp = await request.get(HEALTH_URL, { timeout: 2000 });
    backendUp = resp.ok();
  } catch {
    backendUp = false;
  }
  test.skip(!backendUp, `FastAPI backend not reachable at ${HEALTH_URL} — SSE assertion requires a live backend`);

  // Navigate to the app first to establish a same-origin page context.
  await page.goto("/");

  // Use page.evaluate to run an in-browser Promise that:
  //   1. Opens an EventSource to the FastAPI /events/stream SSE endpoint
  //      using the absolute URL (Pitfall §5 proxy bypass).
  //   2. Resolves on the first NAMED `tick` event (addEventListener("tick"),
  //      NOT onmessage — named events never reach onmessage; see contract note).
  //   3. Rejects after a 3000ms timeout if no event arrives.
  const received = await page.evaluate((sseUrl) => {
    return new Promise<boolean>((resolve, reject) => {
      const source = new EventSource(sseUrl);

      const timer = setTimeout(() => {
        source.close();
        reject(new Error("SSE timeout: no `tick` event received within 3000ms"));
      }, 3000);

      // Named SSE events are delivered to addEventListener(<name>), never to
      // onmessage. The /events/stream route emits `event: tick` lines.
      source.addEventListener("tick", () => {
        clearTimeout(timer);
        source.close();
        resolve(true);
      });

      source.onerror = (err) => {
        clearTimeout(timer);
        source.close();
        reject(new Error(`SSE connection error: ${JSON.stringify(err)}`));
      };
    });
  }, SSE_URL);

  expect(received).toBe(true);
});
