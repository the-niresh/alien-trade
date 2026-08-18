from agent.social.schema import SentimentReading
from agent.social.kol_intent import kol_intent, KolIntent


def _reading(symbol: str, score: float, conf: float) -> SentimentReading:
    return SentimentReading(symbol=symbol, score=score, confidence=conf, n_posts=5)


def test_bullish_eligible_opens_long_when_flat():
    out = kol_intent(_reading("ETH", 0.6, 0.8), holds_symbol=False)
    assert out.action == "open_long"
    assert out.symbol == "ETH"


def test_bullish_below_confidence_is_none():
    assert kol_intent(_reading("ETH", 0.6, 0.2), holds_symbol=False).action == "none"


def test_bearish_reduces_only_when_held():
    assert kol_intent(_reading("CAKE", -0.7, 0.9), holds_symbol=True).action == "reduce"
    assert kol_intent(_reading("CAKE", -0.7, 0.9), holds_symbol=False).action == "none"


def test_ineligible_token_never_trades():
    # BTC is NOT in the eligible allowlist - must be inert regardless of hype.
    assert kol_intent(_reading("BTC", 0.9, 0.9), holds_symbol=False).action == "none"


def test_neutral_is_none():
    assert kol_intent(_reading("ETH", 0.0, 0.9), holds_symbol=True).action == "none"
