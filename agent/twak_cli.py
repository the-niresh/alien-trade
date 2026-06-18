"""
Thin wrapper around the `twak` CLI (Trust Wallet Agent Kit).

This is the self-custody execution surface: the agent never sees a private key.
`twak` holds the encrypted HD wallet on-device, signs locally, and broadcasts.
We only shell out to it and parse JSON.

Used for:
  • wallet status / address / balance   (connection checks)
  • swap quote (--quote-only)            (simulate-before-send)
  • swap execute                          (route + sign + broadcast on-device)

Windows-safe: `twak` installs as `twak.cmd`, which CreateProcess can't run
directly, so we route .cmd/.bat through COMSPEC.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


class TwakError(RuntimeError):
    pass


@dataclass
class TwakQuote:
    from_token: str
    to_token: str
    amount_in: float
    amount_out: float
    price_impact_pct: float    # fraction, e.g. 0.012 == 1.2%
    raw: dict

    @property
    def price(self) -> float:
        return self.amount_out / self.amount_in if self.amount_in else 0.0


@dataclass
class TwakSwapResult:
    tx_hash: str
    raw: dict


# BSC tokens that `twak swap` does NOT resolve by symbol — must use contract addresses.
# ETH works by symbol; everything else on BSC requires the 0x... address.
_BSC_TOKEN_REGISTRY: dict[str, str] = {
    "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
    "UNI":  "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1",
    "LINK": "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",
    "AAVE": "0xfb6115445Bff7b52FeB98650C87f44907E58f802",
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
}

def _resolve_bsc_token(symbol: str) -> str:
    """Return contract address for BSC tokens that twak can't resolve by symbol."""
    return _BSC_TOKEN_REGISTRY.get(symbol.upper(), symbol)


class TwakCli:
    """Subprocess wrapper. Construct once; reuse across cycles."""

    def __init__(self, chain: str = "bsc", binary: Optional[str] = None, timeout: float = 120.0):
        self.chain = chain
        self.timeout = timeout
        self._bin = binary or shutil.which("twak")

    # ── availability ───────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return bool(self._bin)

    def _run(self, *args: str, timeout: Optional[float] = None) -> dict:
        if not self._bin:
            raise TwakError("`twak` CLI not found on PATH (npm install -g @trustwallet/cli)")
        cmd: list[str] = [self._bin, *args]
        if os.name == "nt" and self._bin.lower().endswith((".cmd", ".bat")):
            cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", *cmd]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout or self.timeout,
        )
        out = (proc.stdout or "").strip()
        # Windows libuv quirk: twak can print a valid JSON result and THEN crash
        # on exit (UV_HANDLE_CLOSING assertion -> nonzero code). A parseable JSON
        # payload is the truth; trust it even on a nonzero exit. The on-chain
        # receipt (BNB SDK) is the final confirmation for any swap regardless.
        if out:
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                # twak swap prefixes human-readable status lines before the JSON
                # block (e.g. "Swapping ... Swap executed!\n{...}"). Extract the
                # last top-level JSON object from the mixed output.
                start = out.rfind("{")
                end = out.rfind("}") + 1
                if start != -1 and end > start:
                    try:
                        return json.loads(out[start:end])
                    except json.JSONDecodeError:
                        pass
        if proc.returncode != 0:
            raise TwakError(f"twak {' '.join(args)} failed (exit {proc.returncode}): "
                            f"{(proc.stderr or out).strip()[:400]}")
        return {"_raw": out} if out else {}

    # ── read-only checks ───────────────────────────────────────────────────────

    def auth_status(self) -> dict:
        return self._run("auth", "status", "--json")

    def wallet_status(self) -> dict:
        return self._run("wallet", "status", "--json")

    def wallet_address(self, chain: Optional[str] = None) -> str:
        data = self._run("wallet", "address", "--chain", chain or self.chain, "--json")
        return data.get("address", "")

    def balance(self, chain: Optional[str] = None) -> dict:
        return self._run("wallet", "balance", "--chain", chain or self.chain, "--json")

    # ── competition (Track-1 on-chain registration) ─────────────────────────────

    def compete_status(self) -> dict:
        """Is this wallet registered for the BNB Hack Track-1 competition?
        (`twak compete status`). Read-only; safe to call as a preflight."""
        return self._run("compete", "status", "--json")

    def compete_register(self) -> dict:
        """Register this wallet on-chain for Track 1 (`twak compete register`).
        Operator-run ONCE before the trading window opens (Jun 22) — resolves the
        agent wallet + submits the registration tx to the competition contract.
        Late entries are rejected, so this must happen during the build window."""
        return self._run("compete", "register", "--json")

    # ── swaps ──────────────────────────────────────────────────────────────────

    def swap_quote(
        self, from_token: str, to_token: str, *, usd: float, chain: Optional[str] = None,
        slippage: float = 1.0,
    ) -> TwakQuote:
        """Quote a USD-sized swap without executing (simulate-before-send)."""
        c = chain or self.chain
        # BSC: CAKE/UNI/LINK/AAVE require contract addresses, not symbols
        ft = _resolve_bsc_token(from_token) if c == "bsc" else from_token
        tt = _resolve_bsc_token(to_token)   if c == "bsc" else to_token
        data = self._run(
            "swap", ft, tt, "--usd", str(usd),
            "--chain", c, "--slippage", str(slippage),
            "--quote-only", "--json",
        )
        return _parse_quote(data, from_token, to_token)

    def swap_execute(
        self, from_token: str, to_token: str, *, usd: float, chain: Optional[str] = None,
        slippage: float = 1.0,
    ) -> TwakSwapResult:
        """Execute a USD-sized swap: route + sign on-device + broadcast."""
        c = chain or self.chain
        ft = _resolve_bsc_token(from_token) if c == "bsc" else from_token
        tt = _resolve_bsc_token(to_token)   if c == "bsc" else to_token
        data = self._run(
            "swap", ft, tt, "--usd", str(usd),
            "--chain", c, "--slippage", str(slippage), "--json",
        )
        tx = data.get("txHash") or data.get("hash") or data.get("transactionHash") or ""
        return TwakSwapResult(tx_hash=tx, raw=data)


    # ── portfolio + market data ────────────────────────────────────────────────

    def portfolio(self, chains: Optional[list[str]] = None) -> dict:
        """Full multi-chain portfolio: native + token holdings + USD values."""
        args = ["wallet", "portfolio", "--json"]
        if chains:
            args += ["--chains", ",".join(chains)]
        return self._run(*args)

    def price(self, token: str, chain: Optional[str] = None) -> dict:
        """Spot price for a token (TWAK asset ID or ticker)."""
        args = ["price", token, "--json"]
        if chain:
            args += ["--chain", chain]
        return self._run(*args)

    def risk(self, asset_id: str) -> dict:
        """Token security / rug-risk check."""
        return self._run("risk", asset_id, "--json")

    def trending(
        self,
        category: str = "bnb",
        sort: str = "price_change",
        limit: int = 10,
    ) -> list:
        data = self._run(
            "trending",
            "--category", category,
            "--sort", sort,
            "--limit", str(limit),
            "--json",
        )
        return data if isinstance(data, list) else data.get("items", [])

    def search(self, query: str, networks: Optional[list[str]] = None, limit: int = 10) -> list:
        args = ["search", query, "--limit", str(limit), "--json"]
        if networks:
            args += ["--networks", ",".join(networks)]
        data = self._run(*args)
        return data if isinstance(data, list) else data.get("results", [])

    # ── automate (DCA + limit orders) ─────────────────────────────────────────

    def automate_list(self) -> list:
        data = self._run("automate", "list", "--json")
        return data if isinstance(data, list) else data.get("automations", [])

    def automate_add(
        self,
        from_token: str,
        to_token: str,
        amount: str,
        *,
        chain: Optional[str] = None,
        interval: Optional[str] = None,
        price: Optional[float] = None,
        condition: str = "below",
        max_runs: Optional[int] = None,
    ) -> dict:
        if interval is None and price is None:
            raise ValueError("automate_add: supply interval or price (not neither)")
        if interval is not None and price is not None:
            raise ValueError("automate_add: interval and price are mutually exclusive")
        args = [
            "automate", "add",
            "--from", from_token,
            "--to", to_token,
            "--amount", amount,
            "--chain", chain or self.chain,
            "--json",
        ]
        if interval is not None:
            args += ["--interval", interval]
        if price is not None:
            args += ["--price", str(price), "--condition", condition]
        if max_runs is not None:
            args += ["--max-runs", str(max_runs)]
        return self._run(*args)

    def automate_pause(self, automation_id: str) -> dict:
        return self._run("automate", "pause", automation_id, "--json")

    def automate_resume(self, automation_id: str) -> dict:
        return self._run("automate", "resume", automation_id, "--json")

    def automate_delete(self, automation_id: str) -> dict:
        return self._run("automate", "delete", automation_id, "--json")

    # ── alerts ────────────────────────────────────────────────────────────────

    def alert_list(self) -> list:
        data = self._run("alert", "list", "--json")
        return data if isinstance(data, list) else data.get("alerts", [])

    def alert_create(
        self,
        token: str,
        chain: str,
        *,
        above: Optional[float] = None,
        below: Optional[float] = None,
    ) -> dict:
        if above is None and below is None:
            raise ValueError("alert_create: supply above or below price threshold")
        args = ["alert", "create", "--token", token, "--chain", chain, "--json"]
        if above is not None:
            args += ["--above", str(above)]
        if below is not None:
            args += ["--below", str(below)]
        return self._run(*args)

    def alert_delete(self, alert_id: str) -> dict:
        return self._run("alert", "delete", alert_id, "--json")

    # ── erc20 ─────────────────────────────────────────────────────────────────

    def erc20_allowance(self, token: str, owner: str, spender: str) -> dict:
        return self._run(
            "erc20", "allowance",
            "--token", token, "--owner", owner, "--spender", spender, "--json",
        )

    def erc20_approve(self, token: str, spender: str, amount: str) -> dict:
        return self._run(
            "erc20", "approve",
            "--token", token, "--spender", spender, "--amount", amount, "--json",
        )

    def erc20_revoke(self, token: str, spender: str) -> dict:
        return self._run(
            "erc20", "revoke",
            "--token", token, "--spender", spender, "--json",
        )

    # ── x402 ──────────────────────────────────────────────────────────────────

    def x402_quote(self, url: str, method: str = "GET") -> dict:
        return self._run("x402", "quote", url, "--method", method, "--json")

    def x402_request(
        self,
        url: str,
        max_payment: str,
        *,
        method: str = "POST",
        body: Optional[dict] = None,
        prefer_network: Optional[str] = None,
    ) -> dict:
        args = [
            "x402", "request", url,
            "--max-payment", max_payment,
            "--method", method,
            "--yes", "--json",
        ]
        if body is not None:
            import json as _json
            args += ["--body", _json.dumps(body)]
        if prefer_network:
            args += ["--prefer-network", prefer_network]
        return self._run(*args)


def _parse_quote(data: dict, from_token: str, to_token: str) -> TwakQuote:
    # The CLI's JSON shape varies by version; pull fields defensively.
    amount_in = _to_float(data.get("amountIn") or data.get("fromAmount") or data.get("amount"))
    amount_out = _to_float(data.get("amountOut") or data.get("toAmount") or data.get("expectedOutput"))
    impact = data.get("priceImpact") or data.get("priceImpactPct") or data.get("impact") or 0.0
    impact_pct = _to_float(impact)
    if impact_pct > 1.0:        # CLI sometimes reports percent (1.2) not fraction (0.012)
        impact_pct /= 100.0
    return TwakQuote(
        from_token=from_token, to_token=to_token,
        amount_in=amount_in, amount_out=amount_out,
        price_impact_pct=impact_pct, raw=data,
    )


def _to_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
