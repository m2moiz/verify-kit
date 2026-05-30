/**
 * console.spec.ts — runtime error guard for the web app.
 *
 * Catches what a standard render-and-check pipeline misses: an uncaught
 * TypeError or a failed fetch can leave a BLANK SCREEN while every other web
 * check (build, typecheck, a11y) still passes. This probe loads the app, listens
 * for `pageerror` (uncaught exceptions) and `console.error` messages, writes any
 * captured errors to ../.verify/web/console.json for the harness `web.console`
 * check to surface, then fails if any were collected.
 */
import { test, expect } from "./fixtures/trace";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

const OUTPUT = resolve("../.verify/web/console.json");

interface RuntimeError {
  type: "pageerror" | "console.error";
  message: string;
  url: string;
  stack: string;
}

test("no uncaught page errors or console.error on load", async ({ page }) => {
  const errors: RuntimeError[] = [];

  page.on("pageerror", (err) => {
    errors.push({
      type: "pageerror",
      message: err.message,
      url: page.url(),
      stack: err.stack ?? "",
    });
  });
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push({
        type: "console.error",
        message: msg.text(),
        url: page.url(),
        stack: "",
      });
    }
  });

  await page.goto("/");
  await page.waitForLoadState("networkidle");
  // Give async effects (useEffect, fetch) a beat to throw after first paint.
  await page.waitForTimeout(500);

  mkdirSync(dirname(OUTPUT), { recursive: true });
  writeFileSync(OUTPUT, JSON.stringify(errors, null, 2));

  expect(
    errors,
    `runtime errors detected on load:\n${JSON.stringify(errors, null, 2)}`,
  ).toHaveLength(0);
});
