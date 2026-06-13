"""Thesis-ledger bridge methods (AWAKE_SPRINT §4.6)."""
import json

from agent.convex_bridge import ConvexBridge


def test_record_thesis_offline_shape():
    b = ConvexBridge(url="", control_token="tok")
    b.record_thesis(
        thesis_id="T1", claim="momentum works in trends", source="interview:X",
        regime="trend", status="untested", asset_results=json.dumps({"ETH": {"obj": 0.1}}),
    )
    call = b._offline_log[-1]
    assert call["path"] == "thesisLedger:record"
    a = call["args"]
    assert a["thesis_id"] == "T1" and a["status"] == "untested"
    assert a["ts_ms"] > 0                       # auto-filled timestamp
    assert a["control_token"] == "tok"          # guarded path → token attached


def test_record_thesis_defaults_nullable():
    b = ConvexBridge(url="")
    b.record_thesis(thesis_id="T2", claim="c", source="s")
    a = b._offline_log[-1]["args"]
    assert a["oos_objective"] is None and a["deflated_sharpe"] is None
    assert a["trial_n"] == 0


def test_recent_theses_offline_empty():
    b = ConvexBridge(url="")
    assert b.recent_theses() == []
