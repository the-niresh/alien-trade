"""Distill one corpus document → a structured ThesisCard (AWAKE_SPRINT §4.2).

The corpus text is wrapped in untrusted-content delimiters before being shown to the
LLM, and the LLM's output is validated by the strict ThesisCard schema (reject on parse
fail). The loop NEVER acts on the card's prose — only its (DSL-compiled) proposed_rule
is ever executed. The `llm` callable is injectable so distillation is unit-testable
offline and provider-agnostic.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Optional

from data.corpus.wisdom import distill_ready
from research.thesis import ThesisCard

_PROMPT = """You extract ONE testable trading thesis from the text below.
Return ONLY a JSON object with keys: claim, conditions, regime, asset_class,
testable (bool), proposed_rule (object with 'entry' and 'exit' string expressions
using only: close open high low volume ema<N> sma<N> roc roc<N> atr<N> funding
sentiment regime), risk_notes, source. No prose, no markdown fences.

{wrapped}
"""


class DistillError(ValueError):
    """Raised when LLM output cannot be parsed/validated into a ThesisCard."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    # tolerate ```json fences but nothing else
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise DistillError(f"output is not valid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise DistillError("output JSON is not an object")
    return obj


def distill(text: str, *, llm: Callable[[str], str], source: Optional[str] = None) -> ThesisCard:
    """Wrap untrusted text, call the LLM, validate strictly into a ThesisCard."""
    prompt = _PROMPT.format(wrapped=distill_ready(text))
    raw = llm(prompt)
    obj = _extract_json(raw)
    if source and not obj.get("source"):
        obj["source"] = source
    try:
        return ThesisCard(**obj)
    except Exception as e:  # noqa: BLE001 — surface as a single typed failure
        raise DistillError(f"output failed ThesisCard validation: {e}") from e
