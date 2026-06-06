"""
BNB AI Agent SDK execution wrapper.
Pattern: simulate-before-send → sign (TWAK) → broadcast → confirm → ledger.
BNB_SDK_API_KEY: optional SDK auth; falls back to direct JSON-RPC when absent.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from eth_abi import encode as abi_encode

load_dotenv(Path(__file__).parent.parent.parent / ".env.local")

# ── Chain config ──────────────────────────────────────────────────────────────

TESTNET_RPC = os.environ.get("BNB_TESTNET_RPC_URL", "https://data-seed-prebsc-1-s1.binance.org:8545/")
MAINNET_RPC = os.environ.get("BNB_RPC_URL", "https://bsc-dataseed.binance.org/")
TESTNET_CHAIN_ID = int(os.environ.get("BNB_TESTNET_CHAIN_ID", 97))
MAINNET_CHAIN_ID = int(os.environ.get("BNB_CHAIN_ID", 56))

# PancakeSwap V3 SmartRouter — BSC testnet
PANCAKE_ROUTER_TESTNET = "0x1b81D678ffb9C0263b24A97847620C99d213eB14"
PANCAKE_ROUTER_MAINNET = "0x13f4EA83D0bd40E75C8222255bc855a974568Dd4"

# Token addresses — BSC testnet
TOKENS_TESTNET: dict[str, str] = {
    "WBNB": "0xae13d989daC2f0dEbFf460aC112a837C89BAa7cd",
    "USDT": "0x337610d27c682E347C9cD60BD4b3b107C9d34dDE",
    "USDC": "0x64544969ed7EBf5f083679233325356EbE738930",
}

TOKENS_MAINNET: dict[str, str] = {
    "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
    "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
    "BTCB": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
    "ETH": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
}

# PancakeSwap V3 fee tiers (0.01%, 0.05%, 0.25%, 1%)
FEE_TIERS = {100, 500, 2500, 10000}
DEFAULT_FEE = 2500  # 0.25% — most liquid for BNB pairs

# exactInputSingle selector: keccak256("exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))")
EXACT_INPUT_SINGLE_SEL = bytes.fromhex("414bf389")


@dataclass
class SwapParams:
    token_in: str       # checksummed address
    token_out: str      # checksummed address
    fee: int            # fee tier
    recipient: str      # who receives output tokens
    amount_in: int      # in token_in decimals (wei for 18-decimal tokens)
    amount_out_min: int # minimum output (slippage protection)
    sqrt_price_limit: int = 0  # 0 = no limit


@dataclass
class SwapSimResult:
    amount_out: int     # expected output in token_out decimals
    gas_estimate: int   # gas units
    gas_price_wei: int  # current gas price
    gas_cost_wei: int   # gas_estimate * gas_price_wei
    calldata: bytes     # encoded calldata for the swap
    success: bool
    error: Optional[str] = None


@dataclass
class SwapReceipt:
    tx_hash: str
    block_number: int
    gas_used: int
    gas_price_wei: int
    status: int         # 1 = success, 0 = reverted
    amount_in: int
    token_in: str
    token_out: str


class BNBExec:
    """
    BSC execution engine.
    Wraps PancakeSwap V3 swaps with simulate-before-send discipline.
    Signing is delegated to TWAKSigner — this class never holds private keys.
    """

    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.rpc_url = TESTNET_RPC if testnet else MAINNET_RPC
        self.chain_id = TESTNET_CHAIN_ID if testnet else MAINNET_CHAIN_ID
        self.router = PANCAKE_ROUTER_TESTNET if testnet else PANCAKE_ROUTER_MAINNET
        self.tokens = TOKENS_TESTNET if testnet else TOKENS_MAINNET
        self._http = httpx.Client(timeout=20.0)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BNBExec":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Core public API ──────────────────────────────────────────────────────

    def simulate_swap(
        self,
        params: SwapParams,
        from_address: str,
    ) -> SwapSimResult:
        """
        eth_call the PancakeSwap router. Returns expected output + gas estimate.
        Never submits a transaction — pure read.
        """
        calldata = _encode_exact_input_single(params)

        # Simulate via eth_call
        call_result = self._rpc("eth_call", [
            {"from": from_address, "to": self.router, "data": "0x" + calldata.hex()},
            "latest",
        ], allow_revert=True)
        if call_result.startswith("0x") and len(call_result) >= 66:
            amount_out = int(call_result, 16)
            sim_ok = True
            sim_err = None
        else:
            amount_out = 0
            sim_ok = False
            sim_err = f"eth_call returned: {call_result}"

        # Gas estimate
        gas_estimate = 150_000  # conservative fallback
        try:
            gas_hex = self._rpc("eth_estimateGas", [
                {"from": from_address, "to": self.router, "data": "0x" + calldata.hex()},
            ])
            gas_estimate = int(gas_hex, 16)
        except Exception:
            pass

        gas_price_wei = self._get_gas_price()
        return SwapSimResult(
            amount_out=amount_out,
            gas_estimate=gas_estimate,
            gas_price_wei=gas_price_wei,
            gas_cost_wei=gas_estimate * gas_price_wei,
            calldata=calldata,
            success=sim_ok,
            error=sim_err,
        )

    def build_unsigned_tx(
        self,
        params: SwapParams,
        from_address: str,
        sim: Optional[SwapSimResult] = None,
    ) -> dict:
        """
        Build an unsigned EVM tx dict ready for TWAKSigner.sign_transaction().
        Caller should run simulate_swap() first and pass the result in as `sim`.
        """
        calldata = sim.calldata if sim else _encode_exact_input_single(params)
        gas_estimate = sim.gas_estimate if sim else 200_000
        gas_price = sim.gas_price_wei if sim else self._get_gas_price()
        nonce = self._get_nonce(from_address)

        return {
            "from": from_address,
            "to": self.router,
            "value": "0x0",
            "data": "0x" + calldata.hex(),
            "gas": hex(int(gas_estimate * 1.2)),   # +20% headroom
            "gasPrice": hex(gas_price),
            "nonce": hex(nonce),
            "chainId": self.chain_id,
        }

    def broadcast(self, raw_signed_hex: str) -> str:
        """Broadcast a TWAK-signed raw tx. Returns tx hash."""
        if not raw_signed_hex.startswith("0x"):
            raw_signed_hex = "0x" + raw_signed_hex
        return self._rpc("eth_sendRawTransaction", [raw_signed_hex])

    def wait_for_receipt(self, tx_hash: str, timeout: int = 90, poll_interval: float = 3.0) -> SwapReceipt:
        """Poll until tx is mined. Raises TimeoutError if not confirmed in `timeout` seconds."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                receipt = self._rpc("eth_getTransactionReceipt", [tx_hash])
                if receipt is not None:
                    return SwapReceipt(
                        tx_hash=receipt["transactionHash"],
                        block_number=int(receipt["blockNumber"], 16),
                        gas_used=int(receipt["gasUsed"], 16),
                        gas_price_wei=int(receipt.get("effectiveGasPrice", "0x0"), 16),
                        status=int(receipt["status"], 16),
                        amount_in=0,   # caller fills from params
                        token_in="",
                        token_out="",
                    )
            except Exception:
                pass
            time.sleep(poll_interval)
        raise TimeoutError(f"Tx {tx_hash} not mined within {timeout}s")

    def get_bnb_balance(self, address: str) -> int:
        """Return BNB balance in wei."""
        result = self._rpc("eth_getBalance", [address, "latest"])
        return int(result, 16)

    # ── JSON-RPC helpers ─────────────────────────────────────────────────────

    def _rpc(self, method: str, params: list, allow_revert: bool = False) -> any:
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        r = self._http.post(self.rpc_url, json=payload)
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            err = body["error"]
            if allow_revert and err.get("code") == 3:
                return "0x"  # execution reverted — caller handles
            raise RuntimeError(f"RPC error: {err}")
        return body["result"]

    def _get_gas_price(self) -> int:
        try:
            return int(self._rpc("eth_gasPrice", []), 16)
        except Exception:
            return 5_000_000_000  # 5 gwei fallback

    def _get_nonce(self, address: str) -> int:
        result = self._rpc("eth_getTransactionCount", [address, "pending"])
        return int(result, 16)


# ── ABI encoding ──────────────────────────────────────────────────────────────

def _encode_exact_input_single(p: SwapParams) -> bytes:
    """
    Encode the exactInputSingle calldata for PancakeSwap V3 SmartRouter.
    Struct: (tokenIn, tokenOut, fee, recipient, amountIn, amountOutMinimum, sqrtPriceLimitX96)
    """
    encoded = abi_encode(
        ["(address,address,uint24,address,uint256,uint256,uint160)"],
        [(
            p.token_in,
            p.token_out,
            p.fee,
            p.recipient,
            p.amount_in,
            p.amount_out_min,
            p.sqrt_price_limit,
        )],
    )
    return EXACT_INPUT_SINGLE_SEL + encoded


# ── Convenience: full swap pipeline ──────────────────────────────────────────

def execute_swap_pipeline(
    exec_client: "BNBExec",
    signer,           # TWAKSigner instance
    params: SwapParams,
    wallet_address: str,
    dry_run: bool = False,
) -> SwapReceipt | SwapSimResult:
    """
    Full simulate → sign → broadcast → confirm pipeline.
    Pass dry_run=True to stop after simulation (never sends tx).
    """
    sim = exec_client.simulate_swap(params, wallet_address)
    if not sim.success:
        raise RuntimeError(f"Swap simulation failed: {sim.error}")
    if dry_run:
        return sim

    unsigned = exec_client.build_unsigned_tx(params, wallet_address, sim)
    signed = signer.sign_transaction(unsigned)
    tx_hash = exec_client.broadcast(signed.raw_hex)
    return exec_client.wait_for_receipt(tx_hash)
