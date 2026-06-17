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
        data = self._run(
            "swap", from_token, to_token, "--usd", str(usd),
            "--chain", chain or self.chain, "--slippage", str(slippage),
            "--quote-only", "--json",
        )
        return _parse_quote(data, from_token, to_token)

    def swap_execute(
        self, from_token: str, to_token: str, *, usd: float, chain: Optional[str] = None,
        slippage: float = 1.0,
    ) -> TwakSwapResult:
        """Execute a USD-sized swap: route + sign on-device + broadcast."""
        data = self._run(
            "swap", from_token, to_token, "--usd", str(usd),
            "--chain", chain or self.chain, "--slippage", str(slippage), "--json",
        )
        tx = data.get("txHash") or data.get("hash") or data.get("transactionHash") or ""
        return TwakSwapResult(tx_hash=tx, raw=data)


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
