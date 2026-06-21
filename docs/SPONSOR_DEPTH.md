# Sponsor Integration Depth

Three sponsor capabilities, each mapped to the real code path and a live artifact
a judge can verify in the cockpit.

## CMC Agent Hub — data & signals
- Signals S1–S4 derive from CMC OHLCV / funding+OI / social / on-chain flow:
  `core/signals/{momentum,derivatives,sentiment,onchain}.py`.
- x402 micropayments on every metered CMC call: `agent/x402_provider.py`.
- Live social/KOL ingest → `sentiment_state` → S3: `agent/social/live.py`,
  `agent/loop.py:_inject_sentiment`.
- **Live artifact:** the Notifications panel shows `Scout` events when a KOL
  reading triggers; the regime/signal panels show S1–S4 scores per cycle.

## Trust Wallet Agent Kit (TWAK) — self-custody signing
- Every swap is signed via TWAK; zero raw keys in code/logs: `agent/twak_cli.py`.
- Auth via `TW_ACCESS_ID` + `TW_HMAC_SECRET`; wallet password via env only.
- **Live artifact:** Sponsors view shows the last TWAK-signed tx hash linking to
  BscScan; the wallet-balance panel reads the TWAK-managed wallet.

## BNB AI Agent SDK — on-chain execution
- Spot longs execute as `twak swap` (the only scored path): `agent/executor.py`.
- On-chain receipt is the ledger source of truth (real fill price, real gas):
  `agent/loop.py:_handle_execution`, `convex/ledger.ts`.
- **Live artifact:** Trade History + Sponsors view show fill price, gas paid, and
  the BscScan tx for each on-chain fill.
