# web — Dashboard PWA

React + Vite + shadcn/ui + Tailwind. Installable on mobile via QR code — no app store needed.

## Features

- Live PnL + drawdown chart (Convex real-time)
- Signal + regime view per cycle
- Kill switch toggle → writes `config.halted` to Convex
- Risk cap adjustments
- Co-pilot chat (grounded in Second Brain)

## Mobile access

After onboarding, the Python agent prints an ASCII QR code in the terminal pointing to the hosted PWA URL. Scan it → dashboard installs on home screen like a native app.

## Dev

```bash
cd web
bun install
bun dev
```

Built in Step 5 (Jun 15–18).
