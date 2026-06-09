"""
Compress a CMC skill result envelope into one short line for an LLM prompt, and
build best-effort params for a dynamically-discovered skill from its input_schema.
Shared by the research agent (curated reads) and the co-pilot (dynamic find_skill).

The hub nests the real evidence pack two levels down:
    payload.result.output  (a JSON string)  ->  {result: {data: {summary, status, ...}}}
"""
from __future__ import annotations

import json
import re

# Fields that carry the asset/topic of a question — filled even when optional so a
# discovered skill actually scopes to what the operator asked about.
_IDENTITY_FIELDS = ("symbol", "slug", "query", "claim", "event", "event_query")

# Tickers we recognise in free-text questions (curated allowlist + common majors).
_KNOWN_SYMBOLS = {
    "BTC", "ETH", "BNB", "SOL", "CAKE", "UNI", "LINK", "AAVE",
    "XRP", "DOGE", "ADA", "AVAX", "DOT", "SUI", "LTC", "BCH",
}


def extract_skill_data(payload: dict) -> dict:
    """Dig the evidence-pack `data` dict out of the hub's nested envelope."""
    if not isinstance(payload, dict):
        return {}
    inner = payload.get("result", {})
    out = inner.get("output") if isinstance(inner, dict) else None
    if isinstance(out, str):
        try:
            ev = json.loads(out)
        except json.JSONDecodeError:
            return {}
        r = ev.get("result", {}) if isinstance(ev, dict) else {}
        return r.get("data", {}) if isinstance(r, dict) else {}
    if isinstance(inner, dict):
        r = inner.get("result", inner)
        if isinstance(r, dict) and isinstance(r.get("data"), dict):
            return r["data"]
    return {}


def skill_summary(payload: dict, label: str = "") -> str:
    """One compact line. '' for offline/error/empty so it never adds prompt noise."""
    if not isinstance(payload, dict) or payload.get("status") in ("offline", "error"):
        return ""
    data = extract_skill_data(payload)
    summary = data.get("summary") if isinstance(data, dict) else None
    if not summary:
        return ""
    status = data.get("status")
    prefix = f"[{label}] " if label else ""
    line = f"{prefix}{summary}"
    if status and status != "ok":
        line += f" (status={status})"
    return line[:240]


def detect_symbol(question: str, default: str = "BTC") -> str:
    """First recognised ticker in the question, else `default`."""
    for tok in re.findall(r"[A-Za-z]{2,6}", question or ""):
        if tok.upper() in _KNOWN_SYMBOLS:
            return tok.upper()
    return default


def params_from_schema(schema: dict, question: str, symbol: str) -> dict:
    """Best-effort params for a discovered skill: fill identity/required fields,
    pick enum defaults, and leave everything else to the server's own defaults.
    Wrong/missing fields just make execute_skill return an error we skip — so this
    stays deliberately simple rather than trying to be a general schema solver."""
    if not isinstance(schema, dict):
        return {}
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    params: dict = {}
    for name, spec in props.items():
        if not isinstance(spec, dict):
            continue
        if name not in _IDENTITY_FIELDS and name not in required:
            continue                                  # optional → server default
        val = _value_for(name, spec, question, symbol)
        if val is not None:
            params[name] = val
    return params


def _value_for(name: str, spec: dict, question: str, symbol: str):
    if "enum" in spec:
        return spec.get("default", spec["enum"][0])
    if name in ("symbol", "slug"):
        return symbol
    if name in ("query", "claim", "event", "event_query"):
        return (question or symbol)[:200]
    if spec.get("type") == "boolean":
        # Some skills require a control flag (e.g. `preview`); a preview is the
        # cheap, read-only mode that suits surfacing evidence.
        return spec.get("default", name == "preview")
    if "default" in spec:
        return None                                   # let the server default
    if spec.get("type") == "string":
        return symbol                                 # required string, no default
    return None                                       # required int/obj → omit, may error
