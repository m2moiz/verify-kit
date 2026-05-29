/**
 * Unit test for subscribeDebugEvents (src/lib/events.ts) — the Phase-8/9
 * SSE fix (verify-kit-usi). It exercises the SHIPPED helper directly, which
 * the /events/stream e2e spec (sse.spec.ts) does NOT: that spec opens its own
 * inline EventSource, so nothing else imports subscribeDebugEvents. A
 * regression to `onmessage`-only would still pass `just verify-web` without
 * this test.
 *
 * POLARITY NOTE: ships ONLY in has_web + has_backend. events.ts and
 * sse.spec.ts are excluded by copier.yml when has_backend=false; this test is
 * excluded under the SAME guard (see copier.yml _exclude), so a has_web +
 * NOT-has_backend scaffold does not ship (and cannot false-RED on) it.
 *
 * EVENTSOURCE STUB: the vitest env is happy-dom, which ships NO EventSource.
 * Importing/calling subscribeDebugEvents against a real EventSource throws
 * ("EventSource is not defined"). We install a fake globalThis.EventSource
 * that records each addEventListener(name, handler) call and exposes a
 * dispatch() helper so the test can simulate a server-sent event by name.
 * This lets us assert the named-event wiring without any network or DOM SSE
 * support.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { subscribeDebugEvents } from "@/lib/events";

/** Minimal fake EventSource capturing the named-event wiring under test. */
class FakeEventSource {
  static instances: FakeEventSource[] = [];

  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  closed = false;
  // Map of event-name -> registered listeners (mirrors addEventListener).
  listeners: Record<string, EventListener[]> = {};

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(name: string, handler: EventListener): void {
    (this.listeners[name] ??= []).push(handler);
  }

  close(): void {
    this.closed = true;
  }

  /** Simulate a NAMED server-sent event reaching the browser. */
  dispatch(name: string, data: string): void {
    const event = { type: name, data } as unknown as MessageEvent;
    for (const handler of this.listeners[name] ?? []) {
      (handler as (e: MessageEvent) => void)(event);
    }
  }
}

describe("subscribeDebugEvents", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    // happy-dom has no EventSource; install the fake before each test.
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("delivers a NAMED `verify-event` to the user callback (addEventListener wiring)", () => {
    const received: MessageEvent[] = [];
    const unsubscribe = subscribeDebugEvents((e) => received.push(e));

    expect(FakeEventSource.instances).toHaveLength(1);
    const source = FakeEventSource.instances[0];

    // The helper MUST register a listener for the named `verify-event` event,
    // because the browser delivers NAMED events ONLY to addEventListener(name),
    // never to onmessage. A regression to onmessage-only leaves this empty.
    expect(source.listeners["verify-event"]).toBeDefined();
    expect(source.listeners["verify-event"].length).toBeGreaterThan(0);

    // Simulate the server emitting `event: verify-event` — it must reach the
    // user callback. This is the assertion that fails if the
    // addEventListener("verify-event", ...) line is removed.
    source.dispatch("verify-event", "logged-line-1");

    expect(received).toHaveLength(1);
    expect(received[0].type).toBe("verify-event");
    expect(received[0].data).toBe("logged-line-1");

    // The returned disposer must close the underlying EventSource.
    expect(source.closed).toBe(false);
    unsubscribe();
    expect(source.closed).toBe(true);
  });
});
