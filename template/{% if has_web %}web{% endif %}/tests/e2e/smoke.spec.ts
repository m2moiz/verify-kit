import { test, expect } from "./fixtures/trace";

test("gallery loads and renders 7 sections", async ({ page, traceparent }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Component Gallery");
  const sections = page.locator("[data-lost-pixel-id^='gallery-']");
  await expect(sections).toHaveCount(7, { timeout: 5_000 });
  // traceparent fixture proved itself by injecting the header — no further assertion needed
  // (07-04 CORS expose_headers means the fixture's traceparent reaches the backend when has_backend=true;
  // the smoke spec doesn't assert backend round-trip because 07-05 supports has_backend=false polarity too)
  expect(traceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
});

test("dark-mode toggle flips html class", async ({ page }) => {
  await page.goto("/");
  const html = page.locator("html");
  await expect(html).not.toHaveClass(/dark/);
  await page.getByRole("button", { name: /toggle.*mode|dark mode|theme/i }).click();
  await expect(html).toHaveClass(/dark/);
});
