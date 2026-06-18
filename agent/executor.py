"""
Executor — turns a core Order into a Fill, with execution-reliability discipline.

Two implementations behind one interface:

  PaperExecutor   — prices the fill exactly like backtest.engine (same cost model,
                    same slippage-on-price math) so paper == sim, provably.
  OnchainExecutor — simulate-before-send → slippage cap → sign (TWAK) → broadcast
                    (BNB) → confirm → reconcile the REAL fill from the receipt.

Both share:
  • Idempotency: an order carries an idempotency key (the cycle_id). A key that
    has already produced a fill returns status="duplicate" and never re-sends —
    this is what prevents double-execution on retries / replays.
  • A typed ExecutionReport so the loop always knows what happened and why.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from backtest.engine import Bar, Fill, Order
from backtest.costs import BSCCostModel
from risk.guardrails import RiskConfig, check_slippage

# Execution outcomes
FILLED = "filled"
SIMULATED = "simulated"     # dry-run only, no broadcast
REJECTED = "rejected"       # pre-send guard blocked it (e.g. slippage cap)
FAILED = "failed"           # broadcast/confirm error
DUPLICATE = "duplicate"     # idempotency key already executed


@dataclass
class ExecutionReport:
    status: str
    order: Order
    fill: Optional[Fill] = None
    tx_hash: Optional[str] = None
    reason: str = ""

    @property
    def is_fill(self) -> bool:
        return self.status == FILLED and self.fill is not None


class Executor(Protocol):
    def execute(self, order: Order, bar: Bar, idempotency_key: str) -> ExecutionReport: ...


# ── Idempotency mixin ─────────────────────────────────────────────────────────

class _IdempotentBase:
    def __init__(self) -> None:
        self._seen: dict[str, ExecutionReport] = {}

    def _check_dupe(self, key: str, order: Order) -> Optional[ExecutionReport]:
        prior = self._seen.get(key)
        if prior is not None and prior.status in (FILLED, SIMULATED):
            return ExecutionReport(
                status=DUPLICATE, order=order, fill=prior.fill,
                tx_hash=prior.tx_hash,
                reason=f"idempotency key {key!r} already executed ({prior.status})",
            )
        return None

    def _remember(self, key: str, report: ExecutionReport) -> ExecutionReport:
        if report.status in (FILLED, SIMULATED):
            self._seen[key] = report
        return report

    def mark_seen(self, key: str, tx_hash: Optional[str] = None) -> None:
        """
        Crash recovery: mark a cycle_id as already executed so a post-restart
        replay of that cycle returns DUPLICATE instead of re-broadcasting.
        """
        self._seen[key] = ExecutionReport(
            status=FILLED, order=Order(side="buy", size_usd=0.0, symbol="", timestamp=0),
            tx_hash=tx_hash, reason="recovered: already executed before restart",
        )

    @property
    def seen_keys(self) -> set[str]:
        return set(self._seen.keys())


# ── Paper executor (sim-faithful) ─────────────────────────────────────────────

class PaperExecutor(_IdempotentBase):
    """
    Fills at bar.close with cost-model slippage priced into the fill price —
    byte-for-byte the same math as backtest.engine._apply_fill (non-delayed
    path). This is the contract that makes the paper run a faithful sim mirror.
    """

    def __init__(self, cost_model: Optional[BSCCostModel] = None):
        super().__init__()
        self._cost = cost_model or BSCCostModel()

    def execute(self, order: Order, bar: Bar, idempotency_key: str) -> ExecutionReport:
        dupe = self._check_dupe(idempotency_key, order)
        if dupe is not None:
            return dupe

        fee, gas, slippage = self._cost(order, bar)
        slip_pct = slippage / order.size_usd if order.size_usd > 0 else 0.0
        fill_price = bar.close * (1 + slip_pct if order.side == "buy" else 1 - slip_pct)
        fill = Fill(order=order, fill_price=fill_price,
                    fee_usd=fee, gas_usd=gas, slippage_usd=slippage)
        return self._remember(
            idempotency_key,
            ExecutionReport(status=FILLED, order=order, fill=fill, reason="paper fill"),
        )


# ── On-chain executor (testnet / mainnet) ─────────────────────────────────────

class OnchainExecutor(_IdempotentBase):
    """
    Real execution: simulate-before-send, enforce the slippage cap, sign through
    TWAK, broadcast via the BNB SDK, confirm on-chain, then reconcile the actual
    fill from the receipt. bnb_exec + signer are injected so this is unit-testable
    with mocks (chaos: failed tx, timeout, bad quote).

    dry_run=True stops after a successful simulation (status="simulated") — used
    for the rehearsal phase before a wallet is funded.
    """

    def __init__(
        self,
        bnb_exec,
        signer,
        wallet_address: str,
        risk_config: RiskConfig,
        cost_model: Optional[BSCCostModel] = None,
        dry_run: bool = False,
    ):
        super().__init__()
        self._bnb = bnb_exec
        self._signer = signer
        self._wallet = wallet_address
        self._risk = risk_config
        self._cost = cost_model or BSCCostModel()
        self._dry_run = dry_run

    def execute(self, order: Order, bar: Bar, idempotency_key: str) -> ExecutionReport:
        dupe = self._check_dupe(idempotency_key, order)
        if dupe is not None:
            return dupe

        swap = self._order_to_swap(order, bar)

        # 1. simulate-before-send
        try:
            sim = self._bnb.simulate_swap(swap, self._wallet)
        except Exception as e:  # noqa: BLE001 — surface as a clean report, never crash the loop
            return ExecutionReport(FAILED, order, reason=f"simulate error: {e}")
        if not sim.success:
            return ExecutionReport(REJECTED, order, reason=f"sim failed: {sim.error}")

        # 2. slippage cap (drawdown-first: abort on a bad quote)
        slip_pct = _expected_slippage_pct(order.size_usd, self._cost)
        cap = check_slippage(slip_pct, self._risk)
        if not cap.allowed:
            return ExecutionReport(REJECTED, order, reason=cap.reason)

        if self._dry_run:
            return self._remember(
                idempotency_key,
                ExecutionReport(SIMULATED, order, reason="dry-run: simulation ok"),
            )

        # 3. sign (TWAK) → 4. broadcast (BNB) → 5. confirm
        try:
            unsigned = self._bnb.build_unsigned_tx(swap, self._wallet, sim)
            signed = self._signer.sign_transaction(unsigned)
            tx_hash = self._bnb.broadcast(getattr(signed, "raw_hex", signed))
            receipt = self._bnb.wait_for_receipt(tx_hash)
        except Exception as e:  # noqa: BLE001
            return ExecutionReport(FAILED, order, reason=f"send/confirm error: {e}")

        if getattr(receipt, "status", 0) != 1:
            return ExecutionReport(FAILED, order, tx_hash=tx_hash,
                                   reason="tx reverted on-chain")

        # 6. reconcile the real fill from the receipt (source of truth)
        fee, _, slippage = self._cost(order, bar)
        gas_usd = _gas_usd_from_receipt(receipt, bar)
        fill = Fill(order=order, fill_price=bar.close,
                    fee_usd=fee, gas_usd=gas_usd, slippage_usd=slippage)
        return self._remember(
            idempotency_key,
            ExecutionReport(FILLED, order, fill=fill, tx_hash=tx_hash,
                            reason="on-chain confirmed"),
        )

    # ── helpers ────────────────────────────────────────────────────────────────

    def _order_to_swap(self, order: Order, bar: Bar):
        """Map a USD-sized Order to PancakeSwap V3 SwapParams at the current price."""
        from exec.bnb import SwapParams
        from config.constants import PANCAKE_DEFAULT_FEE

        tokens = self._bnb.tokens
        usdt = tokens.get("USDT", "")
        wbnb = tokens.get("WBNB", "")
        price = bar.close if bar.close > 0 else 1.0

        if order.side == "buy":
            token_in, token_out = usdt, wbnb
            amount_in = int(order.size_usd * 1e18)                  # USDT (18 dp on BSC)
        else:
            token_in, token_out = wbnb, usdt
            amount_in = int((order.size_usd / price) * 1e18)        # WBNB

        return SwapParams(
            token_in=token_in,
            token_out=token_out,
            fee=PANCAKE_DEFAULT_FEE,
            recipient=self._wallet,
            amount_in=amount_in,
            amount_out_min=0,   # router min set from sim in production; sim already gates
        )


class TwakSwapExecutor(_IdempotentBase):
    """
    Self-custody live execution via the `twak` CLI (Trust Wallet Agent Kit).

    The agent never holds a key: `twak` signs on-device and broadcasts. Flow:
      1. quote (--quote-only)        → simulate-before-send (price impact)
      2. slippage cap                → abort on a bad quote (drawdown-first)
      3. swap execute                → route + sign + broadcast on-device
      4. confirm (BNB SDK receipt)   → on-chain truth; reconcile the fill

    A USD-sized Order maps to `twak swap <from> <to> --usd <size>`:
      buy  symbol X  →  USDT → X
      sell symbol X  →  X → USDT

    `twak swap` is mainnet — paper mode covers pre-mainnet rehearsal.
    """

    QUOTE_CCY = "USDT"

    def __init__(
        self,
        twak,                 # TwakCli
        risk_config: RiskConfig,
        cost_model: Optional[BSCCostModel] = None,
        bnb_exec=None,        # optional: confirm receipt + real gas
        chain: str = "bsc",
        dry_run: bool = False,
        bridge=None,          # ConvexBridge — for rug-check config lookups
    ):
        super().__init__()
        self._twak = twak
        self.bridge = bridge
        self._risk = risk_config
        self._cost = cost_model or BSCCostModel()
        self._bnb = bnb_exec
        self._chain = chain
        self._dry_run = dry_run

    def _rug_check(self, asset_id: str) -> None:
        """Block the swap if TWAK risk endpoint flags the token as a rug.
        No-op when rug_check_enabled=False in Convex config or bridge is absent."""
        cfg = self.bridge.get_config() if self.bridge is not None else {}
        cfg = cfg or {}
        if not cfg.get("rug_check_enabled", True):
            return
        threshold = float(cfg.get("rug_risk_threshold") or 75)
        try:
            data = self._twak.risk(asset_id)
        except Exception:
            return   # risk check offline → don't block the trade
        is_rug = bool(data.get("isRug") or data.get("is_rug"))
        score = float(data.get("riskScore") or data.get("risk_score") or 0)
        if is_rug or score >= threshold:
            raise RuntimeError(
                f"rug risk blocked: asset={asset_id} isRug={is_rug} score={score:.0f}"
            )

    def execute(self, order: Order, bar: Bar, idempotency_key: str) -> ExecutionReport:
        from agent.twak_cli import TwakError

        dupe = self._check_dupe(idempotency_key, order)
        if dupe is not None:
            return dupe

        if order.side == "buy":
            from_tok, to_tok = self.QUOTE_CCY, order.symbol
        else:
            from_tok, to_tok = order.symbol, self.QUOTE_CCY
        slippage_pct_arg = self._risk.max_slippage_pct * 100.0

        # 1. quote = simulate-before-send
        try:
            quote = self._twak.swap_quote(
                from_tok, to_tok, usd=order.size_usd,
                chain=self._chain, slippage=slippage_pct_arg,
            )
        except TwakError as e:
            return ExecutionReport(FAILED, order, reason=f"twak quote error: {e}")

        # 2. slippage cap (drawdown-first abort on bad quote)
        cap = check_slippage(quote.price_impact_pct, self._risk)
        if not cap.allowed:
            return ExecutionReport(REJECTED, order, reason=cap.reason)

        if self._dry_run:
            return self._remember(
                idempotency_key,
                ExecutionReport(SIMULATED, order,
                                reason=f"dry-run: quote ok, impact {quote.price_impact_pct:.2%}"),
            )

        # 3. rug-check gate (capital preservation — abort if TWAK flags the token)
        self._rug_check(to_tok)

        # 4. execute (sign on-device + broadcast)
        try:
            res = self._twak.swap_execute(
                from_tok, to_tok, usd=order.size_usd,
                chain=self._chain, slippage=slippage_pct_arg,
            )
        except TwakError as e:
            return ExecutionReport(FAILED, order, reason=f"twak swap error: {e}")
        if not res.tx_hash:
            return ExecutionReport(FAILED, order, reason="twak swap returned no tx hash")

        # 5. confirm on-chain (BNB SDK receipt = source of truth)
        gas_usd = 0.0
        if self._bnb is not None:
            try:
                receipt = self._bnb.wait_for_receipt(res.tx_hash)
            except Exception as e:  # noqa: BLE001
                return ExecutionReport(FAILED, order, tx_hash=res.tx_hash,
                                       reason=f"confirm error: {e}")
            if getattr(receipt, "status", 1) != 1:
                return ExecutionReport(FAILED, order, tx_hash=res.tx_hash,
                                       reason="tx reverted on-chain")
            gas_usd = _gas_usd_from_receipt(receipt, bar)

        fee, model_gas, slippage_usd = self._cost(order, bar)
        fill = Fill(order=order, fill_price=bar.close,
                    fee_usd=fee, gas_usd=gas_usd or model_gas, slippage_usd=slippage_usd)
        return self._remember(
            idempotency_key,
            ExecutionReport(FILLED, order, fill=fill, tx_hash=res.tx_hash,
                            reason="twak swap confirmed"),
        )


def _expected_slippage_pct(size_usd: float, cost_model: BSCCostModel) -> float:
    from backtest.costs import amm_slippage
    if size_usd <= 0:
        return 0.0
    return amm_slippage(size_usd, cost_model.pool_liquidity_usd) / size_usd


def _gas_usd_from_receipt(receipt, bar: Bar) -> float:
    gas_used = getattr(receipt, "gas_used", 0) or 0
    gas_price_wei = getattr(receipt, "gas_price_wei", 0) or 0
    gas_bnb = gas_used * gas_price_wei * 1e-18
    return gas_bnb * max(bar.close, 1.0)
