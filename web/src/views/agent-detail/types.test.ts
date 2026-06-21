import { describe, it, expect } from "vitest";
import { sectionLabel, SECTION_ORDER } from "./types";

describe("sectionLabel", () => {
  it("maps each section to a human label", () => {
    expect(sectionLabel("dashboard")).toBe("Dashboard");
    expect(sectionLabel("positions")).toBe("Live Positions");
    expect(sectionLabel("configure")).toBe("Configure");
  });
  it("SECTION_ORDER lists all five sections in nav order", () => {
    expect(SECTION_ORDER).toEqual(["dashboard", "trades", "scanning", "positions", "configure"]);
  });
});
