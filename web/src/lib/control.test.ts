import { test, expect, beforeEach } from "vitest";
import { withToken, setToken, loadToken } from "./control";

beforeEach(() => localStorage.clear());

test("withToken attaches stored token", () => {
  setToken("abc");
  expect(withToken({ halted: true })).toEqual({ halted: true, control_token: "abc" });
});

test("withToken attaches empty string when unpaired", () => {
  expect(withToken({ halted: true })).toEqual({ halted: true, control_token: "" });
});

test("setToken trims whitespace", () => {
  setToken("  tok  ");
  expect(loadToken()).toBe("tok");
});
