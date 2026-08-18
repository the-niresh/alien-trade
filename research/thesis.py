"""ThesisCard - the strict schema boundary on distillation output (AWAKE_SPRINT §4.2).

A thesis card is DATA, never instructions. The pydantic model rejects anything that
doesn't match the shape, and `proposed_rule` must COMPILE against the DSL (strategy.dsl)
- so a card can only ever express the whitelisted indicator grammar, never arbitrary
code. This is the typed half of the prompt-injection containment (CSO #3).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from strategy.dsl import DSLError, compile_rule


class ThesisCard(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields → rejected

    claim: str
    conditions: str
    regime: str
    asset_class: str
    testable: bool
    proposed_rule: dict          # {"entry": <dsl-expr>, "exit": <dsl-expr>}
    risk_notes: str
    source: str

    @field_validator("proposed_rule")
    @classmethod
    def _rule_must_compile(cls, v: dict) -> dict:
        if "entry" not in v or "exit" not in v:
            raise ValueError("proposed_rule must have 'entry' and 'exit'")
        try:
            compile_rule(v)      # raises DSLError on unknown identifiers / arbitrary code
        except DSLError as e:
            raise ValueError(f"proposed_rule does not compile: {e}") from e
        return v
