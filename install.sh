#!/usr/bin/env bash
# Alien-Trade — one-command onboarding wizard
#
# Usage (hosted):   curl -fsSL https://<host>/install.sh | bash
# Local:            bash install.sh
# Non-interactive:  bash install.sh --non-interactive   (reads from existing env vars)
#
# What this does:
#   1. Checks deps (Python ≥ 3.11, uv, bun, twak)
#   2. Prompts for required secrets / risk caps
#   3. Writes .env.local
#   4. Installs Python deps (core/)
#   5. Installs JS deps + runs Convex dev health check (web/ + jobs/)
#   6. Seeds Convex config (paper mode, risk defaults)
#   7. Starts the agent in paper mode
#   8. Prints an ASCII QR for the PWA URL

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "  ${RED}✗${NC}  $*"; }
hdr()  { echo -e "\n${BOLD}${CYAN}── $* ──${NC}"; }

# ── Args ─────────────────────────────────────────────────────────────────────
NON_INTERACTIVE=false
for arg in "$@"; do
  case $arg in --non-interactive|-n) NON_INTERACTIVE=true ;; esac
done

# ── Banner ───────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}${CYAN}"
cat <<'EOF'
    █████╗ ██╗     ██╗███████╗███╗   ██╗      ████████╗██████╗  █████╗ ██████╗ ███████╗
   ██╔══██╗██║     ██║██╔════╝████╗  ██║      ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝
   ███████║██║     ██║█████╗  ██╔██╗ ██║         ██║   ██████╔╝███████║██║  ██║█████╗
   ██╔══██║██║     ██║██╔══╝  ██║╚██╗██║         ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝
   ██║  ██║███████╗██║███████╗██║ ╚████║         ██║   ██║  ██║██║  ██║██████╔╝███████╗
   ╚═╝  ╚═╝╚══════╝╚═╝╚══════╝╚═╝  ╚═══╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝
EOF
echo -e "${NC}${BOLD}  Autonomous BSC Trading Agent — Onboarding Wizard${NC}"
echo -e "  BNB Hack 2026 · self-custody · Convex real-time bus\n"

# ── Helpers ───────────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_prompt() {
  # Usage: VAR=$(_prompt "Label" "default")
  local label="$1" default="$2"
  if [ "$NON_INTERACTIVE" = "true" ]; then
    # In non-interactive mode, just return the default (caller reads from env)
    echo "${default}"
    return
  fi
  if [ -n "$default" ]; then
    printf "  %s [%s]: " "$label" "$default" >&2
  else
    printf "  %s: " "$label" >&2
  fi
  local val
  read -r val
  echo "${val:-$default}"
}

_prompt_secret() {
  # Like _prompt but masks input
  local label="$1" default="$2"
  if [ "$NON_INTERACTIVE" = "true" ]; then
    echo "${default}"
    return
  fi
  if [ -n "$default" ]; then
    printf "  %s [****]: " "$label" >&2
  else
    printf "  %s: " "$label" >&2
  fi
  local val
  read -rs val
  echo ""  >&2
  echo "${val:-$default}"
}

# ── Step 1: Dependency checks ─────────────────────────────────────────────────
hdr "Step 1 — Checking dependencies"

# Python ≥ 3.11
PYTHON_CMD=""
for cmd in python3.11 python3 python; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ver=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "${major:-0}" -ge 3 ] && [ "${minor:-0}" -ge 11 ]; then
      PYTHON_CMD="$cmd"
      ok "Python $ver ($cmd)"
      break
    fi
  fi
done
if [ -z "$PYTHON_CMD" ]; then
  err "Python ≥ 3.11 not found."
  echo "  Install: https://www.python.org/downloads/ or use pyenv"
  exit 1
fi

# uv
if command -v uv >/dev/null 2>&1; then
  ok "uv $(uv --version 2>&1 | head -1)"
else
  warn "uv not found — installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"
  ok "uv installed"
fi

# bun
if command -v bun >/dev/null 2>&1; then
  ok "bun $(bun --version 2>&1)"
else
  warn "bun not found — installing..."
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
  ok "bun installed"
fi

# twak CLI (optional — required only for mainnet)
if command -v twak >/dev/null 2>&1; then
  ok "twak CLI found"
else
  warn "twak CLI not found (only required for mainnet self-custody trading)"
  echo "  Install: https://developer.trustwallet.com/agent-kit"
fi

# ── Step 2: Gather secrets ────────────────────────────────────────────────────
hdr "Step 2 — Configuration"
echo "  Leave blank to skip optional values (press Enter to accept defaults)"

# Load existing .env.local as defaults if present
if [ -f "$REPO_ROOT/.env.local" ]; then
  warn "Existing .env.local found — using as defaults (press Enter to keep each value)"
  # shellcheck disable=SC1090
  set -o allexport; source "$REPO_ROOT/.env.local" 2>/dev/null || true; set +o allexport
fi

echo ""
echo -e "  ${BOLD}Required — data + infrastructure${NC}"
CMC_API_KEY=$(_prompt_secret   "CMC_API_KEY (CoinMarketCap)"              "${CMC_API_KEY:-}")
CONVEX_URL=$(_prompt           "CONVEX_URL (your Convex deployment)"       "${CONVEX_URL:-}")
UPSTASH_REDIS_REST_URL=$(_prompt_secret "UPSTASH_REDIS_REST_URL"          "${UPSTASH_REDIS_REST_URL:-}")
UPSTASH_REDIS_REST_TOKEN=$(_prompt_secret "UPSTASH_REDIS_REST_TOKEN"      "${UPSTASH_REDIS_REST_TOKEN:-}")
UPSTASH_VECTOR_REST_URL=$(_prompt_secret  "UPSTASH_VECTOR_REST_URL"       "${UPSTASH_VECTOR_REST_URL:-}")
UPSTASH_VECTOR_REST_TOKEN=$(_prompt_secret "UPSTASH_VECTOR_REST_TOKEN"    "${UPSTASH_VECTOR_REST_TOKEN:-}")
ANTHROPIC_API_KEY=$(_prompt_secret "ANTHROPIC_API_KEY"                    "${ANTHROPIC_API_KEY:-}")

echo ""
echo -e "  ${BOLD}Required — TWAK self-custody signing${NC}"
TW_ACCESS_ID=$(_prompt_secret  "TW_ACCESS_ID (Trust Wallet Agent Kit)"    "${TW_ACCESS_ID:-}")
TW_HMAC_SECRET=$(_prompt_secret "TW_HMAC_SECRET"                          "${TW_HMAC_SECRET:-}")

echo ""
echo -e "  ${BOLD}Risk caps${NC}"
EQUITY_FLOOR=$(_prompt         "EQUITY_FLOOR USD (halt if equity drops below)" "${EQUITY_FLOOR:-50}")
DAILY_LOSS_CAP_PCT=$(_prompt   "DAILY_LOSS_CAP_PCT (0-1, e.g. 0.05)"     "${DAILY_LOSS_CAP_PCT:-0.05}")
MAX_OPEN_EXPOSURE_PCT=$(_prompt "MAX_OPEN_EXPOSURE_PCT (0-1, e.g. 0.30)" "${MAX_OPEN_EXPOSURE_PCT:-0.30}")

echo ""
echo -e "  ${BOLD}Optional — Telegram alerts${NC}"
TELEGRAM_BOT_TOKEN=$(_prompt_secret "TELEGRAM_BOT_TOKEN (@BotFather → /newbot)" "${TELEGRAM_BOT_TOKEN:-}")
TELEGRAM_CHAT_ID=$(_prompt     "TELEGRAM_CHAT_ID (from @userinfobot)"    "${TELEGRAM_CHAT_ID:-}")

echo ""
echo -e "  ${BOLD}Optional — CMC x402 micropayments (USDC on Base)${NC}"
X402_PRIVATE_KEY=$(_prompt_secret "X402_PRIVATE_KEY (dedicated burner, fund 15 USDC)" "${X402_PRIVATE_KEY:-}")

echo ""
echo -e "  ${BOLD}Optional — hosted PWA URL (after vercel deploy)${NC}"
PWA_URL=$(_prompt              "PWA_URL (e.g. https://alien-trade.vercel.app)" "${PWA_URL:-}")
AGENT_URL=$(_prompt            "AGENT_URL (public agent endpoint for Convex)" "${AGENT_URL:-http://localhost:8000}")

# ── Step 3: Write .env.local ──────────────────────────────────────────────────
hdr "Step 3 — Writing .env.local"

cat > "$REPO_ROOT/.env.local" <<ENVEOF
# Generated by install.sh — $(date -u '+%Y-%m-%d %H:%M UTC')

# ── Data ──────────────────────────────────────────────────────────────────────
CMC_API_KEY=${CMC_API_KEY}

# ── Convex real-time bus ───────────────────────────────────────────────────────
CONVEX_URL=${CONVEX_URL}
VITE_CONVEX_URL=${CONVEX_URL}

# ── Upstash ────────────────────────────────────────────────────────────────────
UPSTASH_REDIS_REST_URL=${UPSTASH_REDIS_REST_URL}
UPSTASH_REDIS_REST_TOKEN=${UPSTASH_REDIS_REST_TOKEN}
UPSTASH_VECTOR_REST_URL=${UPSTASH_VECTOR_REST_URL}
UPSTASH_VECTOR_REST_TOKEN=${UPSTASH_VECTOR_REST_TOKEN}

# ── LLM ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# ── TWAK (Trust Wallet Agent Kit) ─────────────────────────────────────────────
TW_ACCESS_ID=${TW_ACCESS_ID}
TW_HMAC_SECRET=${TW_HMAC_SECRET}

# ── Execution & trading ────────────────────────────────────────────────────────
EXECUTION_BACKEND=twak
TRADING_MODE=paper
TOKEN_ALLOWLIST=ETH,CAKE,UNI,LINK,AAVE
AGENT_SYMBOL=ETH

# ── Risk caps ──────────────────────────────────────────────────────────────────
EQUITY_FLOOR=${EQUITY_FLOOR}
DAILY_LOSS_CAP_PCT=${DAILY_LOSS_CAP_PCT}
MAX_OPEN_EXPOSURE_PCT=${MAX_OPEN_EXPOSURE_PCT}

# ── Telegram alerts (optional) ────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}

# ── CMC x402 micropayments (optional) ─────────────────────────────────────────
X402_PRIVATE_KEY=${X402_PRIVATE_KEY}
X402_NETWORK=eip155:8453

# ── Hosted endpoints ───────────────────────────────────────────────────────────
PWA_URL=${PWA_URL}
AGENT_URL=${AGENT_URL}

# ── Second Brain ──────────────────────────────────────────────────────────────
SECOND_BRAIN=1
ENVEOF

ok ".env.local written"

# ── Step 4: Install Python deps ────────────────────────────────────────────────
hdr "Step 4 — Installing Python dependencies"
cd "$REPO_ROOT/core"
if [ -d ".venv" ]; then
  ok "venv already exists — syncing"
else
  uv venv .venv --python "$PYTHON_CMD"
  ok "venv created"
fi
uv pip install -e . --quiet
ok "Python deps installed (core/)"
cd "$REPO_ROOT"

# ── Step 5: Install JS deps ────────────────────────────────────────────────────
hdr "Step 5 — Installing JS dependencies"
bun install --cwd "$REPO_ROOT" --frozen-lockfile 2>/dev/null || bun install --cwd "$REPO_ROOT"
ok "JS deps installed"

# ── Step 6: Convex health check ────────────────────────────────────────────────
hdr "Step 6 — Convex health check"
if [ -z "$CONVEX_URL" ]; then
  warn "CONVEX_URL not set — skipping Convex health check"
  echo "  Run 'bunx convex dev' from the repo root to deploy your Convex functions."
else
  # Probe the Convex URL
  if curl -sf "${CONVEX_URL}/api/query" \
       -H 'Content-Type: application/json' \
       -d '{"path":"config:isHalted","args":{},"format":"json"}' \
       -o /dev/null --max-time 10; then
    ok "Convex endpoint reachable at ${CONVEX_URL}"
  else
    warn "Convex endpoint did not respond at ${CONVEX_URL}"
    echo "  Make sure 'bunx convex dev' has been run and the deployment URL is correct."
  fi
fi

# ── Step 7: Start agent in paper mode ─────────────────────────────────────────
hdr "Step 7 — Ready to launch"

echo ""
echo -e "  ${BOLD}To start the trading agent in paper mode:${NC}"
echo ""
echo -e "  ${CYAN}cd core${NC}"
echo -e "  ${CYAN}./.venv/Scripts/python.exe -m uvicorn agent.server:app --port 8000${NC}"
echo -e "  (or on Linux/Mac: ${CYAN}./.venv/bin/python -m uvicorn agent.server:app --port 8000${NC})"
echo ""
echo -e "  ${BOLD}To open the glass cockpit (PWA):${NC}"
echo -e "  ${CYAN}cd web && bun run dev${NC}   →   http://localhost:5173"
echo ""
echo -e "  ${BOLD}To run the full test suite:${NC}"
echo -e "  ${CYAN}core/.venv/Scripts/python.exe -m pytest agent/tests core/tests -q${NC}"
echo ""
echo -e "  ${BOLD}To run the walk-forward strategy retune:${NC}"
echo -e "  ${CYAN}cd core && .venv/Scripts/python.exe -m retune --symbol ETH --source binance --interval 1h${NC}"
echo ""

# ── Step 8: Print QR ──────────────────────────────────────────────────────────
if [ -n "$PWA_URL" ]; then
  hdr "Step 8 — Dashboard QR"
  # Try Python qrcode lib; graceful fallback
  "$PYTHON_CMD" - <<PYEOF 2>/dev/null || echo -e "  Dashboard: ${CYAN}${PWA_URL}${NC}"
import sys
url = "${PWA_URL}"
try:
    import qrcode
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    print("\n  Scan to open the Alien-Trade glass cockpit:\n")
    qr.print_ascii(invert=True)
    print(f"\n  {url}\n")
except ImportError:
    print(f"\n  Dashboard: {url}")
    print("  (pip install qrcode for a scannable QR code)\n")
PYEOF
fi

echo ""
ok "Alien-Trade onboarding complete."
echo -e "  ${BOLD}Next steps:${NC}"
echo "  1. Start the agent:  cd core && .venv/bin/python -m uvicorn agent.server:app --port 8000"
echo "  2. Open cockpit:     cd web && bun run dev"
echo "  3. Register on-chain before Jun 22: twak compete register"
echo "  4. Submit to DoraHacks with your BSC wallet + strategy writeup"
echo ""
