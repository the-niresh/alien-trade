"""
Single source of truth for all hardcoded values in alien-trade/core.

Rules:
- Contract addresses, API base URLs, fee tiers, selector bytes → here only.
- Anything a user might need to change → .env.local (loaded at runtime).
- Import from here everywhere else; never duplicate a magic string.
"""
from __future__ import annotations

# ── Chains ────────────────────────────────────────────────────────────────────

BSC_MAINNET_CHAIN_ID = 56
BSC_TESTNET_CHAIN_ID = 97

BSC_MAINNET_RPC  = "https://bsc-dataseed.binance.org/"
BSC_TESTNET_RPC  = "https://data-seed-prebsc-2-s2.binance.org:8545"

# ── BNB Agent SDK — network presets (mirrors bnbagent.config.NETWORKS) ───────
# Source: https://github.com/bnb-chain/bnbagent-sdk/blob/main/bnbagent/config.py
# All registration txs on testnet are gas-free via the MegaFuel paymaster.

BNB_SDK_NETWORKS: dict[str, dict] = {
    "bsc-testnet": {
        "chain_id":          BSC_TESTNET_CHAIN_ID,
        "rpc_url":           BSC_TESTNET_RPC,
        "paymaster_url":     "https://bsc-megafuel-testnet.nodereal.io",
        # ERC-8004 Agent Identity Registry
        "registry_contract": "0x8004A818BFB912233c491871b3d84c89A494BD9e",
        # ERC-8183 AgenticCommerce stack
        "commerce_contract": "0xa206c0517b6371c6638cd9e4a42cc9f02a33b0de",
        "router_contract":   "0xd7d36d66d2f1b608a0f943f722d27e3744f66f25",
        "policy_contract":   "0x4f4678d4439fec812ac7674bb3efb4c8f5fb78a6",
    },
    "bsc-mainnet": {
        "chain_id":          BSC_MAINNET_CHAIN_ID,
        "rpc_url":           BSC_MAINNET_RPC,
        "paymaster_url":     "https://bsc-megafuel.nodereal.io/",
        "registry_contract": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
        "commerce_contract": "0xea4daa3100a767e86fded867729ae7446476eba6",
        "router_contract":   "0x51895229e12f9876011789b04f8698af06ccd6da",
        "policy_contract":   "0x9c01845705b3078aa2e8cff7520a6376fd766de5",
    },
}

# ── PancakeSwap V3 ────────────────────────────────────────────────────────────
# SwapRouter / SmartRouter addresses.  BSC testnet values need on-chain verification.

PANCAKE_ROUTER: dict[str, str] = {
    "bsc-mainnet": "0x13f4EA83D0bd40E75C8222255bc855a974568Dd4",
    "bsc-testnet": "0x1b81D678ffb9C0263b24A97847620C99d213eB14",  # verify
}

PANCAKE_FEE_TIERS = (100, 500, 2500, 10000)   # 0.01 / 0.05 / 0.25 / 1 %
PANCAKE_DEFAULT_FEE = 2500                      # 0.25 % — most liquid BNB pairs

# exactInputSingle(ExactInputSingleParams) selector
PANCAKE_EXACT_INPUT_SINGLE_SEL = bytes.fromhex("414bf389")

# ── Token addresses ───────────────────────────────────────────────────────────

TOKENS: dict[str, dict[str, str]] = {
    "bsc-mainnet": {
        "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "BTCB": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
        "ETH":  "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
    },
    "bsc-testnet": {
        "WBNB": "0xae13d989daC2f0dEbFf460aC112a837C89BAa7cd",
        "USDT": "0x337610d27c682E347C9cD60BD4b3b107C9d34dDE",
        "USDC": "0x64544969ed7EBf5f083679233325356EbE738930",
    },
}

# ── CMC ───────────────────────────────────────────────────────────────────────

CMC_BASE_URL = "https://pro-api.coinmarketcap.com"

# CMC integer IDs for the trading universe
CMC_SYMBOL_IDS: dict[str, int] = {
    "BNB":  1839,
    "BTC":  1,
    "ETH":  1027,
    "USDT": 825,
}

# ── Binance ───────────────────────────────────────────────────────────────────

BINANCE_BASE_URL = "https://api.binance.com"

BINANCE_SYMBOL_PAIRS: dict[str, str] = {
    "BNB":  "BNBUSDT",
    "WBNB": "BNBUSDT",
    "BTC":  "BTCUSDT",
    "BTCB": "BTCUSDT",
    "ETH":  "ETHUSDT",
}

BINANCE_INTERVAL_MAP: dict[str, str] = {
    "daily": "1d",
    "4h":    "4h",
    "1h":    "1h",
    "15m":   "15m",
}

# ── TWAK (Trust Wallet Agent Kit) ─────────────────────────────────────────────
# Exact base URL confirmed from TWAK portal/docs — update when received.
# Override at runtime via TWAK_API_BASE env var.

TWAK_API_BASE_DEFAULT = "https://tws.trustwallet.com"
# Exact paths below need confirmation from TWAK docs or hackathon Builder Telegram.
# The server requires auth headers to respond — unauthenticated discovery returns 404.
TWAK_SIGN_PATH   = "/api/v1/sign"      # confirm
TWAK_WALLET_PATH = "/api/v1/wallet"    # confirm
