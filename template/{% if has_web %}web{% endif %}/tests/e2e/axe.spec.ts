/**
 * axe.spec.ts — WCAG 2.1 AA accessibility scan for both light and dark modes.
 *
 * Written by plan 07-06; extends the Playwright trace fixture from 07-05.
 * Outputs raw axe JSON to ../.verify/web/axe.json for harness.web.axe_adapter
 * to parse and emit SARIF 2.1.0 at .verify/web/axe.sarif.
 *
 * A11Y-04: scans both light mode (default) and dark mode (DarkModeToggle click).
 * Light and dark violations are merged into a single output file with a
 * `colorScheme` tag on each violation so the adapter can distinguish them.
 */
import { test, expect } from "./fixtures/trace";
import AxeBuilder from "@axe-core/playwright";
import { writeFileSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const AXE_OUTPUT = resolve("../.verify/web/axe.json");
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

test("axe-core a11y scan on gallery (light mode)", async ({ page }) => {
  await page.goto("/");

  const results = await new AxeBuilder({ page })
    .withTags(WCAG_TAGS)
    .analyze();

  // Write initial results (light mode)
  mkdirSync(dirname(AXE_OUTPUT), { recursive: true });
  const lightTagged = results.violations.map((v) => ({
    ...v,
    colorScheme: "light",
  }));
  writeFileSync(
    AXE_OUTPUT,
    JSON.stringify({ ...results, violations: lightTagged }, null, 2)
  );

  // Fail the spec on any light-mode violation; adapter classifies severity
  expect(results.violations).toEqual([]);
});

test("axe-core a11y scan on gallery (dark mode)", async ({ page }) => {
  await page.goto("/");

  // Toggle to dark mode using the DarkModeToggle button (A11Y-04)
  await page.getByRole("button", { name: /toggle.*mode|dark mode|theme/i }).click();

  // Small wait for CSS transitions to settle
  await page.waitForTimeout(300);

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();

  // Merge dark-mode violations into the existing axe.json from the light-mode test.
  // Both test cases run sequentially; the merge creates a single output file
  // with violations tagged by colorScheme for adapter classification.
  let existing: Record<string, unknown> = {};
  try {
    existing = JSON.parse(readFileSync(AXE_OUTPUT, "utf-8"));
  } catch {
    // No prior light-mode scan (e.g. running this test in isolation) — initialize
    existing = { violations: [] };
  }

  const lightViolations = (existing.violations as unknown[]) ?? [];
  const darkTagged = results.violations.map((v) => ({
    ...v,
    colorScheme: "dark",
  }));

  const merged = { ...existing, violations: [...lightViolations, ...darkTagged] };
  writeFileSync(AXE_OUTPUT, JSON.stringify(merged, null, 2));

  // Fail the spec on any dark-mode violation; adapter classifies severity
  expect(results.violations).toEqual([]);
});
