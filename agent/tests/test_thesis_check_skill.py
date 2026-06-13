from agent.skills.thesis_check import ThesisCheckSkill


class FakeBridge:
    def __init__(self, cards):
        self._cards = cards

    def recent_theses(self, limit=200):
        return self._cards


def test_returns_expected_shape_for_match():
    cards = [{
        "thesis_id": "T1", "claim": "momentum persists in confirmed uptrends",
        "status": "validated", "oos_objective": 0.42, "deflated_sharpe": 0.61,
        "source": "youtube:@chatwithtraders ep.300",
    }]
    out = ThesisCheckSkill(bridge=FakeBridge(cards)).compute("does momentum work in uptrends?")
    assert set(out) >= {"status", "oos_objective", "deflated_sharpe", "source", "verdict"}
    assert out["status"] == "validated" and out["verdict"] == "supported"


def test_falsified_maps_to_avoid():
    cards = [{"thesis_id": "T2", "claim": "rotate into the strongest asset every bar",
              "status": "FALSIFIED", "oos_objective": -2.3, "deflated_sharpe": 0.0,
              "source": "session:2026-06-12"}]
    out = ThesisCheckSkill(bridge=FakeBridge(cards)).compute("cross-sectional rotation")
    assert out["verdict"] == "avoid"


def test_no_cards_returns_unknown_stub():
    out = ThesisCheckSkill(bridge=FakeBridge([])).compute("anything")
    assert out["status"] == "untested" and out["verdict"] == "unknown"
