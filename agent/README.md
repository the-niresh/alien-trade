# agent — Live Runtime

FastAPI + LangGraph supervisor that runs the live trading loop.

Imports `/core` directly — zero duplicate strategy logic here.

## Responsibilities

- Scheduled decision loop (via Trigger.dev): fetch → signals → regime → risk → execute
- LangGraph supervisor managing sub-agents: research, strategist, reflection, co-pilot
- Executor: simulate-before-send → sign (TWAK) → send (BNB SDK) → confirm → reconcile
- Kill switch check: reads `convex/config.halted` every cycle

## What does NOT live here

- Strategy logic — that's in `core/`
- Signal computation — that's in `core/signals/`
- Risk sizing — that's in `core/risk/`

Built in Step 5 (Jun 15–18).
