import { test, expect } from "vitest";
import {
  SPONSOR_CONTROLS,
  getControlsByTransport,
  getControlsBySponsor,
  type SponsorControl,
} from "./sponsorRegistry";

test("all controls have required fields", () => {
  for (const c of SPONSOR_CONTROLS) {
    expect(c.id).toBeTruthy();
    expect(c.label).toBeTruthy();
    expect(c.description.length).toBeGreaterThan(10);
    expect(["TWAK", "CMC", "BNB_SDK", "agent"]).toContain(c.sponsor);
    expect(["policy", "read", "imperative"]).toContain(c.transport);
    expect(["scored", "neutral", "operator"]).toContain(c.scoringImpact);
  }
});

test("no duplicate ids", () => {
  const ids = SPONSOR_CONTROLS.map((c) => c.id);
  expect(new Set(ids).size).toBe(ids.length);
});

test("imperative controls have commandType", () => {
  for (const c of SPONSOR_CONTROLS.filter((c) => c.transport === "imperative")) {
    expect(c.commandType).toBeTruthy();
  }
});

test("read controls have readEndpoint", () => {
  for (const c of SPONSOR_CONTROLS.filter((c) => c.transport === "read")) {
    expect(c.readEndpoint).toBeTruthy();
  }
});

test("getControlsByTransport filters correctly", () => {
  const imperative = getControlsByTransport("imperative");
  expect(imperative.every((c) => c.transport === "imperative")).toBe(true);
});

test("getControlsBySponsor filters correctly", () => {
  const twak = getControlsBySponsor("TWAK");
  expect(twak.every((c) => c.sponsor === "TWAK")).toBe(true);
  expect(twak.length).toBeGreaterThan(0);
});
