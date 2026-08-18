"""
SkillHub - the two-tier CMC skill loader the research + co-pilot agents use.

  Tier 1 (curated):  run_curated(key, ctx) → pinned unique_name + correct params
                     → execute_skill. No discovery hop; deterministic; cheap.
  Tier 2 (dynamic):  find_skill(query) → pick a candidate → execute_skill. For
                     open-ended questions where no curated skill fits.

Off the hot path by construction (locked decision #1): the deterministic /core
decision never imports this. Offline-first: with no CMC_MCP_API_KEY the hub is
`enabled = False` and returns explicit offline markers, so the agents/tests/demo
run with zero network - exactly like ClaudeClient and CMCClient.

Each execute_skill is a paid platform call → a real x402 usage point in the
research loop (CMC/TWAK special-prize surface).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agent.skills.registry import CURATED, SkillContext, manifest
from agent.skills.transport import CmcSkillHubTransport, SkillHubError


@dataclass
class SkillHub:
    transport: CmcSkillHubTransport = field(default_factory=CmcSkillHubTransport)

    @property
    def enabled(self) -> bool:
        return self.transport.enabled

    # ── Tier 2: dynamic discovery ──────────────────────────────────────────────

    def find_skill(self, query: str, top_k: int = 5) -> list[dict]:
        """Ranked candidate skills for an open-ended query (the hub's own router).
        Offline → [] so callers fall back to curated/none without crashing."""
        if not self.enabled:
            return []
        try:
            payload = self.transport.call_tool("find_skill", {"query": query, "top_k": top_k})
        except SkillHubError:
            return []
        return payload.get("candidates", []) if isinstance(payload, dict) else []

    def execute_skill(self, unique_name: str, parameters: Optional[dict] = None) -> dict:
        """Run a skill by unique_name. Offline → an explicit offline marker (never
        a fabricated result). Errors are returned as a marker, not raised, so a
        Tier-1 advisory failure can never take down a caller (failure-matrix rule)."""
        if not self.enabled:
            return {"status": "offline", "unique_name": unique_name,
                    "parameters": parameters or {}}
        try:
            return self.transport.call_tool("execute_skill",
                                            {"unique_name": unique_name,
                                             "parameters": parameters or {}})
        except SkillHubError as e:
            return {"status": "error", "unique_name": unique_name, "error": str(e)}

    # ── Tier 1: curated ────────────────────────────────────────────────────────

    def run_curated(self, key: str, ctx: Optional[SkillContext] = None) -> dict:
        """Execute a pinned skill by our internal key, building params from `ctx`."""
        if key not in CURATED:
            raise KeyError(f"unknown curated skill {key!r}; one of {sorted(CURATED)}")
        skill = CURATED[key]
        params = skill.build(ctx or SkillContext())
        return self.execute_skill(skill.unique_name, params)

    @staticmethod
    def curated_keys() -> list[str]:
        return list(CURATED)

    @staticmethod
    def curated_manifest() -> str:
        """Injectable one-liner-per-skill manifest for the agent system prompt."""
        return manifest()
