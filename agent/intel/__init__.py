"""
Event Intelligence — the agent's real-time awareness of "what just happened".

Trading is event-driven: a hack, depeg, ETF approval, or regulator headline can move
a market overnight or in seconds. This layer turns news into (a) a hard RISK-OFF
signal when something dangerous breaks, and (b) a bounded sentiment nudge — both
bounded, point-in-time, off the LLM hot path, exactly like the social/forecast seams.

It is a *source of intelligence*: a proprietary, continuously-updated event stream the
operator can spectate (structured logs + cockpit channel + Telegram) and that the risk
layer can act on.
"""
from agent.intel.event_intel import (  # noqa: F401
    EventDigest, EventIntel, HeadlineScore, score_headline,
)
from agent.intel.brave_client import BraveSearchClient  # noqa: F401
