from agent.agents.watchdog import find_stalled, default_cadence_ms

HOUR = 3600_000


def test_stalled_when_silent_beyond_factor():
    now = 100 * HOUR
    agents = [
        {"name": "fresh", "status": "active", "trigger": {"kind": "schedule", "spec": "1h"},
         "last_activity_ms": now - HOUR},
        {"name": "stale", "status": "active", "trigger": {"kind": "schedule", "spec": "1h"},
         "last_activity_ms": now - 5 * HOUR},
    ]
    stalled = [a["name"] for a in find_stalled(agents, now)]
    assert stalled == ["stale"]


def test_archived_agents_ignored():
    now = 100 * HOUR
    agents = [{"name": "z", "status": "archived", "trigger": {"kind": "schedule", "spec": "1h"},
               "last_activity_ms": now - 99 * HOUR}]
    assert find_stalled(agents, now) == []


def test_default_cadence_parses_hours_and_falls_back():
    assert default_cadence_ms({"kind": "schedule", "spec": "2h"}) == 2 * HOUR
    assert default_cadence_ms(None) == HOUR
