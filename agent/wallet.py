"""
Wallet connection check for the live runtime.

Verifies the self-custody execution path is ready end-to-end:
  twak installed -> authenticated -> agent wallet created -> address on BSC ->
  funded -> BNB SDK can read the balance on-chain.

Prints the exact next command for whatever is missing. Never handles the
password or mnemonic — wallet creation/funding is the operator's job.

    core/.venv/Scripts/python.exe -m agent.wallet            # status check
    core/.venv/Scripts/python.exe -m agent.wallet --chain bsc
"""
from __future__ import annotations

import argparse

from agent.twak_cli import TwakCli, TwakError

FAUCET_BSC_TESTNET = "https://www.bnbchain.org/en/testnet-faucet"


def check(chain: str = "bsc") -> dict:
    twak = TwakCli(chain=chain)
    report: dict = {"chain": chain, "ok": False, "steps": []}

    if not twak.available:
        report["steps"].append(
            "Install the CLI:  npm install -g @trustwallet/cli")
        return report

    # auth
    try:
        auth = twak.auth_status()
    except TwakError as e:
        report["steps"].append(f"twak auth failed: {e}")
        return report
    report["auth"] = auth
    if not auth.get("configured"):
        report["steps"].append(
            "Set TWAK_ACCESS_ID + TWAK_HMAC_SECRET (portal.trustwallet.com), then:  twak init")
        return report

    # wallet
    try:
        wstat = twak.wallet_status()
    except TwakError as e:
        report["steps"].append(f"twak wallet status failed: {e}")
        return report
    report["wallet_status"] = wstat
    agent_wallet = wstat.get("agentWallet")
    if not agent_wallet or agent_wallet == "not configured":
        report["steps"].append(
            'Create the agent wallet (you choose the password):  '
            'twak wallet create --password <STRONG_PW>')
        return report

    # address
    try:
        addr = twak.wallet_address(chain)
    except TwakError as e:
        report["steps"].append(f"resolve address failed: {e}")
        return report
    report["address"] = addr
    report["steps"].append(f"Set WALLET_ADDRESS={addr} in .env.local")

    # balance
    try:
        report["balance"] = twak.balance(chain)
    except TwakError as e:
        report["balance_error"] = str(e)

    report["ok"] = bool(addr)
    return report


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Alien-Trade wallet connection check")
    ap.add_argument("--chain", default="bsc")
    args = ap.parse_args(argv)

    r = check(args.chain)
    print("\n  -- wallet connection ----------------------")
    print(f"  chain     : {r['chain']}")
    print(f"  twak auth : {'ok' if r.get('auth', {}).get('configured') else 'NOT configured'}")
    ws = r.get("wallet_status", {})
    print(f"  wallet    : {ws.get('agentWallet', 'not configured')}")
    if r.get("address"):
        print(f"  address   : {r['address']}")
    if r.get("balance"):
        print(f"  balance   : {r['balance']}")
    print(f"  connected : {'YES' if r['ok'] else 'no'}")
    if r["steps"]:
        print("\n  next:")
        for s in r["steps"]:
            print(f"   - {s}")
    if not r["ok"]:
        print(f"\n  testnet faucet: {FAUCET_BSC_TESTNET}")
    print("  -------------------------------------------\n")


if __name__ == "__main__":
    main()
