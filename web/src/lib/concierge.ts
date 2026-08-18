import { withToken } from "./control";

// ── Types ─────────────────────────────────────────────────────────────────────

export type ProposedAction =
  | { type: "set_strategy";   params: { strategy_name: string };                                         summary: string }
  | { type: "update_limits";  params: { max_position_usd?: number; daily_loss_limit_usd?: number; max_drawdown_pct?: number; equity_floor?: number }; summary: string }
  | { type: "set_autopilot";  params: { enabled: boolean; profit_target_pct?: number; protect_principal?: boolean; trailing_giveback_pct?: number }; summary: string }
  | { type: "halt";           params: Record<string, never>;                                             summary: string }
  | { type: "resume";         params: Record<string, never>;                                             summary: string }
  | { type: "mark_setup";     params: { setup_key: string; cycle_id: string; symbol: string; label: "good" | "bad"; note?: string }; summary: string }
  | { type: "withdraw";       params: { to_address: string; amount: number; token: string };              summary: string }
  | { type: "deposit_info";   params: Record<string, never>;                                             summary: string };

export type ConciergeDispatchers = {
  setStrategy:   (args: { strategy_name: string; control_token?: string }) => Promise<void>;
  updateLimits:  (args: { max_position_usd?: number; daily_loss_limit_usd?: number; max_drawdown_pct?: number; equity_floor?: number; control_token?: string }) => Promise<void>;
  setAutopilot:  (args: { autopilot: { enabled: boolean; profit_target_pct?: number; protect_principal?: boolean; trailing_giveback_pct?: number }; control_token?: string }) => Promise<void>;
  setHalted:     (args: { halted: boolean; control_token?: string }) => Promise<void>;
  setControl:    (args: { trading_halted: boolean; updated_by: string; control_token?: string }) => Promise<void>;
  recordFeedback:(args: { setup_key: string; cycle_id: string; symbol: string; label: "good" | "bad"; note?: string; control_token?: string }) => Promise<void>;
  enqueueCommand:(args: { command_type: string; params: string; queued_by?: string; control_token: string }) => Promise<unknown>;
  onDepositInfo: () => void;
};

// ── Suggestion card builders (deterministic - no LLM needed) ─────────────────

export function suggestionConservative(): ProposedAction {
  return {
    type: "set_strategy",
    params: { strategy_name: "defensive" },
    summary: "Switch strategy to defensive (low risk, small positions, strict stop-loss).",
  };
}

export function suggestionAdjustRisk(max_position_usd: number, equity_floor: number): ProposedAction {
  return {
    type: "update_limits",
    params: { max_position_usd, equity_floor },
    summary: `Set max position to $${max_position_usd} and equity floor to $${equity_floor}.`,
  };
}

export function suggestionTakeProfit(profit_target_pct: number): ProposedAction {
  return {
    type: "set_autopilot",
    params: { enabled: true, profit_target_pct, protect_principal: true },
    summary: `Enable autopilot: take profit at ${(profit_target_pct * 100).toFixed(0)}%, protect principal.`,
  };
}

// ── Deterministic intent grammar ─────────────────────────────────────────────

export function parseIntent(text: string): ProposedAction | null {
  const t = text.toLowerCase().trim();

  // halt / resume
  if (/\b(halt|stop|pause)\b/.test(t) && !/resume|restart/.test(t)) {
    return { type: "halt", params: {}, summary: "Halt all trading immediately." };
  }
  if (/\b(resume|restart|unpause|continue)\b/.test(t)) {
    return { type: "resume", params: {}, summary: "Resume trading." };
  }

  // strategy keywords
  const strategyMap: Record<string, string> = {
    conservative: "defensive", defensive: "defensive",
    aggressive: "momentum",   momentum: "momentum",
    balanced: "balanced",     contrarian: "contrarian",
  };
  for (const [kw, strat] of Object.entries(strategyMap)) {
    if (t.includes(kw)) {
      return {
        type: "set_strategy",
        params: { strategy_name: strat },
        summary: `Switch strategy to ${strat}.`,
      };
    }
  }

  // size / position
  const sizeMatch = t.match(/\bsize\b.*?\$?(\d+(?:\.\d+)?)/);
  if (sizeMatch) {
    const n = parseFloat(sizeMatch[1]);
    return {
      type: "update_limits",
      params: { max_position_usd: n },
      summary: `Set max position size to $${n}.`,
    };
  }

  // take profit
  const tpMatch = t.match(/\btake\s+profit\b|profit\s+target.*?(\d+(?:\.\d+)?)%/);
  if (tpMatch) {
    const pct = tpMatch[1] ? parseFloat(tpMatch[1]) / 100 : 0.05;
    return {
      type: "set_autopilot",
      params: { enabled: true, profit_target_pct: pct, protect_principal: true },
      summary: `Enable autopilot profit-take at ${(pct * 100).toFixed(0)}%.`,
    };
  }

  // withdraw
  const withdrawMatch = t.match(/withdraw\s+(\d+(?:\.\d+)?)\s*(usdt|eth|bnb)\s+to\s+(0x[0-9a-f]{40})/i);
  if (withdrawMatch) {
    const [, amtStr, token, to_address] = withdrawMatch;
    return {
      type: "withdraw",
      params: { to_address, amount: parseFloat(amtStr), token: token.toUpperCase() },
      summary: `Withdraw ${amtStr} ${token.toUpperCase()} to ${to_address.slice(0, 6)}...${to_address.slice(-4)}.`,
    };
  }

  // deposit
  if (/\bdeposit\b/.test(t)) {
    return { type: "deposit_info", params: {}, summary: "Show deposit address and on-ramp." };
  }

  return null; // read-only - no proposed action
}

// ── Action dispatcher ─────────────────────────────────────────────────────────

export async function dispatchAction(action: ProposedAction, d: ConciergeDispatchers): Promise<void> {
  switch (action.type) {
    case "set_strategy":
      await d.setStrategy(withToken({ strategy_name: action.params.strategy_name }));
      break;
    case "update_limits":
      await d.updateLimits(withToken(action.params));
      break;
    case "set_autopilot":
      await d.setAutopilot(withToken({ autopilot: action.params }));
      break;
    case "halt":
      await d.setHalted(withToken({ halted: true }));
      await d.setControl(withToken({ trading_halted: true, updated_by: "copilot" }));
      break;
    case "resume":
      await d.setHalted(withToken({ halted: false }));
      await d.setControl(withToken({ trading_halted: false, updated_by: "copilot" }));
      break;
    case "mark_setup":
      await d.recordFeedback(withToken(action.params));
      break;
    case "withdraw": {
      const p = action.params;
      await d.enqueueCommand(withToken({
        command_type: "withdraw",
        params: JSON.stringify({ to_address: p.to_address, amount: p.amount, token: p.token }),
        queued_by: "copilot",
      }));
      break;
    }
    case "deposit_info":
      d.onDepositInfo();
      break;
  }
}
