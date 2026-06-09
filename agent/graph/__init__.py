"""
agent.graph — the orchestrator layer (LangGraph supervisor + the contracts every
agent speaks through). Contracts-first (AGENT_TEAM_PLAN §9.2): `contracts.py` is
the single, versioned home for every inter-agent payload and the failure matrix.
The supervisor graph (`supervisor.py`) is built on top in STEP 8.3.
"""
