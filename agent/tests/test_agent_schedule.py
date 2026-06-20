from agent.agents.schedule import due_agents, deliver_push

HOUR = 3600_000


def test_due_when_past_cadence():
    now = 100 * HOUR
    agents = [
        {"name": "a", "status": "active", "trigger": {"kind": "schedule", "spec": "1h"},
         "last_activity_ms": now - 2 * HOUR},
        {"name": "b", "status": "active", "trigger": {"kind": "schedule", "spec": "1h"},
         "last_activity_ms": now - 10_000},
    ]
    assert [a["name"] for a in due_agents(agents, now)] == ["a"]


def test_deliver_push_prunes_dead_subscriptions():
    subs = [{"_id": "s1", "endpoint": "e1", "p256dh": "x", "auth": "y"},
            {"_id": "s2", "endpoint": "e2", "p256dh": "x", "auth": "y"}]
    pruned = []
    class B:
        def call(self, kind, path, args):
            if path == "push:list": return subs
            if path == "push:remove": pruned.append(args["id"])
    def sender(sub, payload, *, vapid): return sub["endpoint"] == "e1"
    n = deliver_push(B(), {"title": "t", "body": "b"}, vapid={}, sender=sender)
    assert n == 1 and pruned == ["s2"]
