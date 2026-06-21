import { describe, it, expect, vi } from "vitest";
import { parseIntent, dispatchAction, type ProposedAction } from "./concierge";

// ── parseIntent ───────────────────────────────────────────────────────────────
describe("parseIntent", () => {
  it("returns halt for 'halt trading'", () => {
    expect(parseIntent("halt trading")).toMatchObject({ type: "halt" });
  });

  it("returns resume for 'resume now'", () => {
    expect(parseIntent("resume now")).toMatchObject({ type: "resume" });
  });

  it("returns set_strategy defensive for 'go conservative'", () => {
    expect(parseIntent("go conservative")).toMatchObject({ type: "set_strategy", params: { strategy_name: "defensive" } });
  });

  it("returns set_strategy momentum for 'aggressive mode'", () => {
    expect(parseIntent("aggressive mode")).toMatchObject({ type: "set_strategy", params: { strategy_name: "momentum" } });
  });

  it("returns update_limits for 'set size to $8'", () => {
    expect(parseIntent("set size to $8")).toMatchObject({ type: "update_limits", params: { max_position_usd: 8 } });
  });

  it("returns set_autopilot for 'take profit'", () => {
    const a = parseIntent("take profit");
    expect(a?.type).toBe("set_autopilot");
  });

  it("returns set_autopilot with pct for 'profit target 10%'", () => {
    const a = parseIntent("profit target 10%") as Extract<ProposedAction, { type: "set_autopilot" }>;
    expect(a.params.profit_target_pct).toBeCloseTo(0.1);
  });

  it("returns withdraw for full withdraw command", () => {
    const a = parseIntent("withdraw 5 USDT to 0xabcdef1234567890abcdef1234567890abcdef12") as Extract<ProposedAction, { type: "withdraw" }>;
    expect(a.type).toBe("withdraw");
    expect(a.params.amount).toBe(5);
    expect(a.params.token).toBe("USDT");
  });

  it("returns deposit_info for 'deposit'", () => {
    expect(parseIntent("I want to deposit")).toMatchObject({ type: "deposit_info" });
  });

  it("returns null for unknown text", () => {
    expect(parseIntent("what is the current price?")).toBeNull();
    expect(parseIntent("hello")).toBeNull();
  });
});

// ── dispatchAction ────────────────────────────────────────────────────────────
describe("dispatchAction", () => {
  function makeDispatchers() {
    return {
      setStrategy:    vi.fn().mockResolvedValue(undefined),
      updateLimits:   vi.fn().mockResolvedValue(undefined),
      setAutopilot:   vi.fn().mockResolvedValue(undefined),
      setHalted:      vi.fn().mockResolvedValue(undefined),
      setControl:     vi.fn().mockResolvedValue(undefined),
      recordFeedback: vi.fn().mockResolvedValue(undefined),
      enqueueCommand: vi.fn().mockResolvedValue("cmd-id"),
      onDepositInfo:  vi.fn(),
    };
  }

  it("calls setStrategy for set_strategy action", async () => {
    const d = makeDispatchers();
    await dispatchAction({ type: "set_strategy", params: { strategy_name: "defensive" }, summary: "" }, d);
    expect(d.setStrategy).toHaveBeenCalledWith(expect.objectContaining({ strategy_name: "defensive" }));
  });

  it("calls both setHalted and setControl for halt action", async () => {
    const d = makeDispatchers();
    await dispatchAction({ type: "halt", params: {}, summary: "" }, d);
    expect(d.setHalted).toHaveBeenCalledWith(expect.objectContaining({ halted: true }));
    expect(d.setControl).toHaveBeenCalledWith(expect.objectContaining({ trading_halted: true }));
  });

  it("enqueues withdraw command with JSON params", async () => {
    const d = makeDispatchers();
    await dispatchAction({
      type: "withdraw",
      params: { to_address: "0xabc", amount: 5, token: "USDT" },
      summary: "",
    }, d);
    expect(d.enqueueCommand).toHaveBeenCalledWith(expect.objectContaining({ command_type: "withdraw" }));
    const call = d.enqueueCommand.mock.calls[0][0];
    const parsed = JSON.parse(call.params);
    expect(parsed.to_address).toBe("0xabc");
    expect(parsed.amount).toBe(5);
  });

  it("calls onDepositInfo for deposit_info action", async () => {
    const d = makeDispatchers();
    await dispatchAction({ type: "deposit_info", params: {}, summary: "" }, d);
    expect(d.onDepositInfo).toHaveBeenCalled();
  });
});
