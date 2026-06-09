"""
CmcSkillHubTransport — minimal MCP Streamable-HTTP client for the CMC Crypto
Skill Hub, hand-rolled in raw httpx to match the codebase's REST-first house
style (no langchain / mcp SDK). The server (mcp.coinmarketcap.com/skill-hub) is
STATELESS: a single `tools/call` POST works with no initialize handshake and no
session id, and replies as Server-Sent Events whose `data:` line is the JSON-RPC
response. The real payload is `result.content[0].text` (a JSON string).

Offline-first like every other client here: with no CMC_MCP_API_KEY it is simply
`enabled = False`, and the SkillHub returns offline markers instead of calling.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

import httpx

DEFAULT_URL = "https://mcp.coinmarketcap.com/skill-hub/stream"


class SkillHubError(RuntimeError):
    """Transport- or tool-level failure from the skill hub."""


@dataclass
class CmcSkillHubTransport:
    url: str = field(default_factory=lambda: os.environ.get("CMC_SKILL_HUB_URL", DEFAULT_URL))
    api_key: str = field(default_factory=lambda: os.environ.get("CMC_MCP_API_KEY", ""))
    timeout: float = 300.0          # some skills take 30-300s (per hub docs)
    _id: int = field(default=0, init=False, repr=False)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    # ── JSON-RPC over Streamable HTTP ──────────────────────────────────────────

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        """Invoke one MCP tool (`find_skill` | `execute_skill`) and return the
        decoded payload dict. Raises SkillHubError on transport/JSON-RPC/tool error."""
        if not self.enabled:
            raise SkillHubError("CMC_MCP_API_KEY not set — skill hub offline")
        self._id += 1
        body = {
            "jsonrpc": "2.0", "id": self._id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        headers = {
            "X-CMC-MCP-API-KEY": self.api_key,
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as c:
                r = c.post(self.url, headers=headers, json=body)
                r.raise_for_status()
                rpc = _parse_response(r.text)
        except httpx.HTTPError as e:
            raise SkillHubError(f"skill hub HTTP error: {e}") from e

        if "error" in rpc:
            err = rpc["error"]
            raise SkillHubError(f"skill hub tool error {err.get('code')}: {err.get('message')}")
        return _extract_payload(rpc.get("result", {}))


# ── Response parsing ────────────────────────────────────────────────────────


def _parse_response(text: str) -> dict:
    """Decode the JSON-RPC response from an SSE stream (`event:`/`data:` lines)
    or a plain JSON body. The last `data:` line carries the final response."""
    payload: Optional[str] = None
    for line in text.splitlines():
        if line.startswith("data:"):
            payload = line[5:].strip()
    if payload is None:
        payload = text.strip()
    return json.loads(payload)


def _extract_payload(result: dict) -> dict:
    """MCP `tools/call` result → the tool's actual JSON payload. Tools here return
    `content: [{type:"text", text:"<json>"}]`; fall back to the raw result."""
    content = result.get("content")
    if isinstance(content, list) and content:
        text = content[0].get("text")
        if isinstance(text, str):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    return result
