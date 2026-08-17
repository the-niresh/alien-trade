import { describe, expect, it } from "vitest";
import { GUIDE_ANSWERS, matchGuideAnswer } from "./guide";

describe("visitor guide", () => {
  it("answers its own suggested questions", () => {
    for (const entry of GUIDE_ANSWERS) {
      const hit = matchGuideAnswer(entry.question);
      expect(hit, `no match for "${entry.question}"`).not.toBeNull();
      expect(hit!.question).toBe(entry.question);
    }
  });

  it("answers the questions people actually type", () => {
    const cases: [string, string][] = [
      ["did it make money?", "Did it make money?"],
      ["is this profitable", "Did it make money?"],
      ["what is this", "What am I looking at?"],
      ["why can't I click anything", "Why can't I click anything?"],
      ["how does the llm fit in", "Where does the AI actually come in?"],
      ["where should i start", "Where should I look first?"],
    ];
    for (const [typed, expected] of cases) {
      const hit = matchGuideAnswer(typed);
      expect(hit?.question, `"${typed}" matched ${hit?.question ?? "nothing"}`).toBe(expected);
    }
  });

  it("returns nothing rather than guessing on an unrelated question", () => {
    expect(matchGuideAnswer("what is the capital of France")).toBeNull();
    expect(matchGuideAnswer("")).toBeNull();
    expect(matchGuideAnswer("   ")).toBeNull();
  });

  it("never claims a profit", () => {
    // The single hard rule for anything user-facing in this project.
    for (const entry of GUIDE_ANSWERS) {
      const text = entry.answer.toLowerCase();
      expect(text).not.toMatch(/\bwe (made|earned) (a )?profit/);
      expect(text).not.toMatch(/\bprofitable strategy\b/);
      expect(text).not.toMatch(/\bgains? of \d/);
    }
  });

  it("states the loss consistently wherever it comes up", () => {
    const money = GUIDE_ANSWERS.find((a) => a.question === "Did it make money?")!;
    expect(money.answer).toContain("40");
    expect(money.answer).toContain("44 cents");
    expect(money.answer.toLowerCase()).toContain("lost money");
  });

  it("keeps every answer short enough to read on a phone", () => {
    for (const entry of GUIDE_ANSWERS) {
      expect(entry.answer.length, `${entry.question} is too long`).toBeLessThan(900);
      expect(entry.answer.length, `${entry.question} is too thin`).toBeGreaterThan(80);
    }
  });

  it("only routes to views that exist", async () => {
    const { VALID_VIEWS } = await import("./nav");
    for (const entry of GUIDE_ANSWERS) {
      if (entry.goTo) expect(VALID_VIEWS.has(entry.goTo), `${entry.goTo} is not a view`).toBe(true);
    }
  });
});
