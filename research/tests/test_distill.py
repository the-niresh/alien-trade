import json

import pytest

from research.distill import DistillError, distill
from research.thesis import ThesisCard


_VALID = {
    "claim": "momentum persists in confirmed uptrends",
    "conditions": "price above long EMA, positive ROC",
    "regime": "trend",
    "asset_class": "crypto",
    "testable": True,
    "proposed_rule": {"entry": "close>ema100 and roc>0", "exit": "close<ema50"},
    "risk_notes": "whipsaws in chop",
    "source": "youtube:@chatwithtraders ep.300",
}


def test_valid_card_parses():
    card = ThesisCard(**_VALID)
    assert card.testable and card.proposed_rule["entry"]


def test_proposed_rule_must_compile():
    bad = {**_VALID, "proposed_rule": {"entry": "close>moon_phase", "exit": "close<ema50"}}
    with pytest.raises(Exception):
        ThesisCard(**bad)              # unknown identifier → DSL rejects → validation error


def test_distill_rejects_nonconforming_output():
    # LLM returns text that is not the required schema → DistillError
    def bad_llm(prompt: str) -> str:
        return "sure! here is some prose with no JSON"
    with pytest.raises(DistillError):
        distill("some corpus text", llm=bad_llm)


def test_distill_happy_path():
    def good_llm(prompt: str) -> str:
        assert "BEGIN UNTRUSTED" in prompt   # untrusted wrapper applied
        return json.dumps(_VALID)
    card = distill("trader interview transcript…", llm=good_llm)
    assert isinstance(card, ThesisCard) and card.regime == "trend"
