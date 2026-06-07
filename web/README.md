# web — Dashboard PWA ✅ (Step 5 scaffold)

React + Vite + `vite-plugin-pwa` (manifest + service worker → installs on a phone
home screen via the terminal QR, no app store). Convex is the real-time bridge.

## Built

- Live PnL, drawdown, open exposure, circuit-breaker cards (Convex reactive `useQuery`)
- Kill switch toggle → `config:setHalted` mutation (halts agent within one cycle)
- Recent decisions feed (regime + verdict + size per cycle)

## Planned (later phases)

- PnL/drawdown time-series chart, signal attribution view
- Risk cap editor, Co-pilot chat (grounded in Second Brain — Step 6)
- shadcn/ui + Tailwind polish pass

## Setup

Set `VITE_CONVEX_URL` (see `.env.example`). The dashboard imports the generated
Convex API from `../convex/_generated/api`.

## Mobile access

After onboarding, the Python agent prints an ASCII QR code in the terminal pointing to the hosted PWA URL. Scan it → dashboard installs on home screen like a native app.

## Dev

```bash
cd web
bun install
bun dev
```

Built in Step 5 (Jun 15–18).
