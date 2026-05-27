import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "@/App";

describe("App gallery", () => {
  it("renders the gallery title containing PROJECT_NAME", () => {
    render(<App />);
    // PROJECT_NAME comes from @/config; gallery title is `<h1>{PROJECT_NAME} — Component Gallery</h1>`
    // Dialog/Sheet with defaultOpen causes radix to set aria-hidden on surrounding elements;
    // use { hidden: true } so the query sees the full DOM including aria-hidden regions.
    expect(screen.getByRole("heading", { level: 1, hidden: true })).toHaveTextContent(/Component Gallery/);
  });

  it("renders at least 7 gallery sections (one per D-W10 component)", () => {
    const { container } = render(<App />);
    const sections = container.querySelectorAll("[data-lost-pixel-id^='gallery-']");
    expect(sections.length).toBeGreaterThanOrEqual(7);
  });
});
