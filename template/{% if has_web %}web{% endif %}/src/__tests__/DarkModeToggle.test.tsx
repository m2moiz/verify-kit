import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach } from "vitest";
import { DarkModeToggle } from "@/components/gallery/DarkModeToggle";

describe("DarkModeToggle", () => {
  beforeEach(() => { document.documentElement.classList.remove("dark"); });

  it("adds 'dark' class to <html> on click; removes on second click", async () => {
    const user = userEvent.setup();
    render(<DarkModeToggle />);
    const button = screen.getByRole("button", { name: /toggle.*mode|dark mode|theme/i });
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    await user.click(button);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    await user.click(button);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
