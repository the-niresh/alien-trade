from agent.copilot_agent import execute_tool


class B:
    def call(self, kind, path, args): return "agentX"


def test_create_agent_tool_validates_and_writes():
    out = execute_tool("create_agent",
                       {"name": "CAKE-Watcher", "goal": "watch CAKE",
                        "allowed_tools": ["get_price"]},
                       twak=None, skills=None, bridge=B())
    assert "CAKE-Watcher" in out and "agentX" in out


def test_create_agent_tool_rejects_unknown_tool():
    out = execute_tool("create_agent",
                       {"name": "x", "goal": "g", "allowed_tools": ["drain"]},
                       twak=None, skills=None, bridge=B())
    assert "unknown tool" in out.lower() or "error" in out.lower()
