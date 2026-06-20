from agent.agents import registry


class FakeBridge:
    def __init__(self): self.calls = []
    def call(self, kind, path, args):
        self.calls.append((kind, path, args))
        return "agent123" if path == "spawnedAgents:create" else None


def test_create_agent_calls_create_mutation():
    b = FakeBridge()
    out = registry.create_agent(b, {"name": "W", "goal": "g", "allowed_tools": ["get_price"],
                                    "trigger": None, "notify_policy": {"webpush": True, "severity_min": "info"},
                                    "mode": "paper"})
    assert out == "agent123"
    kind, path, args = b.calls[0]
    assert (kind, path) == ("mutation", "spawnedAgents:create")
    assert args["name"] == "W" and args["mode"] == "paper"


def test_archive_sets_status():
    b = FakeBridge()
    registry.archive(b, "agent123")
    assert b.calls[0] == ("mutation", "spawnedAgents:setStatus",
                          {"id": "agent123", "status": "archived"})
