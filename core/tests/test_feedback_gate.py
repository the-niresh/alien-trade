"""Human-feedback gate - deterministic setup-key + verdict (offline)."""
from __future__ import annotations

from risk.feedback import evaluate_feedback, setup_key


# ── setup_key ──────────────────────────────────────────────────────────────────

def test_setup_key_picks_dominant_signal_with_sign():
    sig = {"momentum": -0.7, "derivatives": 0.2, "sentiment": 0.1, "flow": 0.0}
    assert setup_key("chop", sig) == "chop|momentum-"


def test_setup_key_positive_sign():
    sig = {"momentum": 0.1, "derivatives": 0.0, "sentiment": 0.9, "flow": 0.0}
    assert setup_key("trend_up", sig) == "trend_up|sentiment+"


def test_setup_key_flat_when_no_signal():
    assert setup_key("chop", {"momentum": 0.0, "derivatives": 0.0}) == "chop|flat"
    assert setup_key("chop", {}) == "chop|flat"


def test_setup_key_stable_for_similar_setups():
    a = setup_key("high_vol", {"momentum": -0.55, "sentiment": -0.2})
    b = setup_key("high_vol", {"momentum": -0.82, "sentiment": -0.1})
    assert a == b == "high_vol|momentum-"


# ── evaluate_feedback ──────────────────────────────────────────────────────────

def test_empty_feedback_allows():
    v = evaluate_feedback([])
    assert not v.block and v.size_penalty == 0.0


def test_two_net_bad_blocks():
    v = evaluate_feedback([{"label": "bad"}, {"label": "bad"}])
    assert v.block and v.size_penalty == 1.0


def test_one_net_bad_halves():
    v = evaluate_feedback([{"label": "bad"}])
    assert not v.block and v.size_penalty == 0.5


def test_good_offsets_bad():
    # 2 bad, 2 good → net 0 → allow
    recs = [{"label": "bad"}, {"label": "bad"}, {"label": "good"}, {"label": "good"}]
    v = evaluate_feedback(recs)
    assert not v.block and v.size_penalty == 0.0


def test_good_majority_allows():
    recs = [{"label": "good"}, {"label": "good"}, {"label": "bad"}]
    v = evaluate_feedback(recs)
    assert not v.block and v.size_penalty == 0.0


def test_three_bad_one_good_still_blocks():
    recs = [{"label": "bad"}] * 3 + [{"label": "good"}]  # net 2 → block
    v = evaluate_feedback(recs)
    assert v.block
