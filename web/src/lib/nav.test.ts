import { describe, expect, it } from "vitest";
import { MORE_VIEWS, NAV_ITEMS, NAV_ORDER, PRIMARY_VIEWS, VIEW_META, VALID_VIEWS } from "./nav";
import type { View } from "./nav";

/**
 * These exist because the rail shipped with Trackers and Pipeline on the same icon.
 * Two buttons that look identical are not a cosmetic problem — the icon is the only
 * label a 44px rail button has, so a repeat makes one of them unreachable by sight.
 */

describe("navigation metadata", () => {
  it("gives every view its own icon", () => {
    const byIcon = new Map<unknown, View[]>();
    for (const view of NAV_ORDER) {
      const icon = VIEW_META[view].icon;
      byIcon.set(icon, [...(byIcon.get(icon) ?? []), view]);
    }
    const shared = [...byIcon.values()].filter((views) => views.length > 1);
    expect(shared, `views sharing one icon: ${JSON.stringify(shared)}`).toEqual([]);
  });

  it("gives every view its own label", () => {
    const labels = NAV_ORDER.map((v) => VIEW_META[v].label);
    expect(new Set(labels).size).toBe(labels.length);
  });

  it("describes every view in plain words", () => {
    for (const view of NAV_ORDER) {
      const { blurb } = VIEW_META[view];
      expect(blurb.length, `${view} has no blurb`).toBeGreaterThan(20);
      // A first-time visitor reads these. Jargon here defeats the point.
      expect(blurb.toLowerCase()).not.toMatch(/sortino|calmar|oos|twak|x402|bep-?20/);
    }
  });

  it("has metadata for exactly the views in the order list, and no orphans", () => {
    expect(Object.keys(VIEW_META).sort()).toEqual([...NAV_ORDER].sort());
    expect(NAV_ITEMS).toHaveLength(NAV_ORDER.length);
  });

  it("splits the mobile bar into primary and more with nothing lost or duplicated", () => {
    const combined = [...PRIMARY_VIEWS, ...MORE_VIEWS].map((i) => i.view);
    expect(new Set(combined).size).toBe(combined.length);
    expect([...combined].sort()).toEqual([...NAV_ORDER].sort());
  });

  it("keeps the route allowlist in step with the rail", () => {
    for (const view of NAV_ORDER) expect(VALID_VIEWS.has(view)).toBe(true);
    expect(VALID_VIEWS.size).toBe(NAV_ORDER.length);
  });
});
