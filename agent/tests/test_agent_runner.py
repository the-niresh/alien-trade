from agent.agents import runner


class RecBridge:
    def __init__(self): self.calls = []
    def call(self, kind, path, args): self.calls.append((path, args)); return "run1"
    def append_event(self, **kw): self.calls.append(("event", kw))


def test_run_agent_records_run_and_heartbeat():
    rec = {"_id": "a1", "name": "W", "goal": "watch CAKE",
           "allowed_tools": ["get_price"], "mode": "paper"}
    b = RecBridge()

    def fake_loop(question, **kw):
        assert "watch CAKE" in question
        return {"answer": "CAKE flat", "grounded": True,
                "sources": [{"tool": "get_price", "args": {"token": "CAKE"}}]}

    out = runner.run_agent(rec, twak=None, skills=None, bridge=b, client=None,
                           loop_fn=fake_loop)
    assert out["ok"] is True
    assert "CAKE flat" in out["summary"]
    paths = [c[0] for c in b.calls]
    assert "agentRuns:record" in paths        # run persisted
    assert any(p == "event" for p in paths)    # one agent_events row


def test_run_agent_failure_becomes_error_event_not_raise():
    rec = {"_id": "a1", "name": "W", "goal": "g", "allowed_tools": [], "mode": "paper"}
    b = RecBridge()

    def boom(question, **kw): raise RuntimeError("tool down")

    out = runner.run_agent(rec, twak=None, skills=None, bridge=b, client=None, loop_fn=boom)
    assert out["ok"] is False
    assert "tool down" in out["summary"]
    assert any(c[0] == "agentRuns:record" and c[1]["ok"] is False for c in b.calls)
