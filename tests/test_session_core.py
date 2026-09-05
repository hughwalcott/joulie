"""SessionCore's constructor opens the mic and loads XTTS, so the state-handling
methods are exercised against a stub instead. Calling the unbound method runs the
real body without paying for the hardware."""

import threading
from types import SimpleNamespace

from joulie.session_core import SessionCore, TurnEvent


class CoreStub:
    """Only what end_session touches."""

    def __init__(self, **kw):
        self.speaker = SimpleNamespace(stop=lambda: None)
        self.agent = SimpleNamespace(reset=lambda: None)
        self._lock = threading.Lock()
        self._in_session = kw.get("in_session", True)
        self._processing = kw.get("processing", False)
        self._recording = kw.get("recording", False)
        self.last_event = kw.get("last_event")


class TestEndSession:
    def test_clears_the_last_event_so_it_cannot_reach_the_next_visitor(self):
        stub = CoreStub(last_event=TurnEvent(visitor="how much is a heat pump?",
                                             joulie="about $7,000 installed"))
        SessionCore.end_session(stub)
        assert stub.last_event is None

    def test_leaves_the_session_flag_down(self):
        stub = CoreStub()
        SessionCore.end_session(stub)
        assert stub._in_session is False

    def test_forcibly_clears_a_stuck_turn(self):
        stub = CoreStub(processing=True, recording=True)
        SessionCore.end_session(stub)
        assert (stub._processing, stub._recording) == (False, False)

    def test_is_a_no_op_when_no_session_is_running(self):
        stub = CoreStub(in_session=False, last_event=TurnEvent(visitor="stale"))
        SessionCore.end_session(stub)
        # Nothing to clear, and nothing to trample: the early return leaves the
        # event alone rather than reaching past a session that isn't running.
        assert stub.last_event is not None
