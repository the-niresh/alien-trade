from agent.approval import ApprovalGate


class FakeBot:
    def __init__(self):
        self.sent = []
        self.enabled = True

    def send(self, text, **k):
        self.sent.append(text)
        return 1


def test_request_and_approve():
    g = ApprovalGate(bot=FakeBot())
    g.request("AT-REQ-1", ["convex/config.ts"], "needs a guard tweak")
    assert g.is_approved("AT-REQ-1") is False
    assert g.bot.sent and "AT-REQ-1" in g.bot.sent[0]
    g.ingest_text("approve AT-REQ-1")        # simulates a getUpdates reply
    assert g.is_approved("AT-REQ-1") is True


def test_yes_approves_latest():
    g = ApprovalGate(bot=FakeBot())
    g.request("AT-REQ-2", ["x"], "r")
    g.ingest_text("yes")
    assert g.is_approved("AT-REQ-2") is True


def test_unrelated_text_does_nothing():
    g = ApprovalGate(bot=FakeBot())
    g.request("AT-REQ-3", ["x"], "r")
    assert g.ingest_text("how's it going") is False
    assert g.is_approved("AT-REQ-3") is False


def test_reping_when_stale():
    g = ApprovalGate(bot=FakeBot())
    g.request("AT-REQ-4", ["x"], "r")
    assert g.re_ping_if_stale("AT-REQ-4", seconds=0) is True   # 0s → already stale
    assert len(g.bot.sent) == 2                                 # original + re-ping
