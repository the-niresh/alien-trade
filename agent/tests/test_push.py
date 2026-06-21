from unittest.mock import patch
from agent import push


def test_build_payload_shape():
    p = push.build_push_payload("Agent W", "CAKE funding negative", severity="warn", url="/agents")
    assert p == {"title": "Agent W", "body": "CAKE funding negative",
                 "severity": "warn", "url": "/agents"}


def test_send_push_returns_false_on_dead_subscription():
    sub = {"endpoint": "https://x", "keys": {"p256dh": "a", "auth": "b"}}
    with patch("agent.push.webpush", side_effect=Exception("410 Gone")):
        assert push.send_push(sub, {"title": "t", "body": "b"},
                              vapid={"private_key": "k", "subject": "mailto:x@y.z"}) is False
