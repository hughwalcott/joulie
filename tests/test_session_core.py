"""SessionCore's constructor opens the mic and loads XTTS, so the state-handling
methods are exercised against a stub instead. Calling the unbound method runs the
real body without paying for the hardware."""

import threading
import time
from types import SimpleNamespace

from joulie import config
from joulie.rag import Source
from joulie.session_core import SessionCore, TurnEvent
from joulie.tools import REGISTRY, detect_tool


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


class FakeAgent:
    """Hands out tokens on demand so a test can hold the stream open and force the
    heartbeat path that a real 6-10s wait on Ollama would."""

    def __init__(self, tokens, sources=(), sources_after=0, stall=0.0):
        self._tokens = list(tokens)
        self._stall = stall
        # Retrieval populates last_sources partway through _build_messages, which
        # a real turn runs inside the tee thread — so a turn must cope with it
        # being empty at first and filling in later.
        self._sources = sources
        self._sources_after = sources_after
        self.last_sources: tuple = ()
        self.last_prompt_stats: dict = {}
        self.last_eval_stats: dict = {}
        self.last_post_ttft_seconds = 0.0

    def stream(self, text):
        if self._stall:
            time.sleep(self._stall)
        for index, token in enumerate(self._tokens):
            if index >= self._sources_after:
                self.last_sources = self._sources
            yield token


class TurnStub:
    """Only what _run_turn touches. The real SessionCore constructor opens the
    mic and loads XTTS, so the turn loop is driven against this instead."""

    def __init__(self, agent, transcript="how do I compare power plans?"):
        import numpy as np
        self.agent = agent
        self._lock = threading.Lock()
        self._recording = True
        self._processing = False
        self._in_session = True
        self.last_event = None
        self.stopped_at = None
        self.events = []
        audio = np.zeros(32000, dtype="float32")

        def _stop():
            self.stopped_at = len(self.events)
            return audio

        self.recorder = SimpleNamespace(stop=_stop)
        self.transcriber = SimpleNamespace(transcribe=lambda a: (transcript, "en"))
        self.speaker = SimpleNamespace(say_stream=lambda it: [None for _ in it] and {})
        self.power = SimpleNamespace(window_stats=lambda a, b: {})
        self._turn_metrics = []
        self._turn_index = 0
        self._session_id = "test"

    def run(self):
        for event in SessionCore._run_turn(self):
            self.events.append(event)
            self.last_event = event
        return self.events


def _run(stub, monkeypatch):
    monkeypatch.setattr("joulie.metrics.append_turn", lambda *a, **kw: None)
    return stub.run()


class TestTurnEventOrder:
    def test_the_turn_announces_itself_before_stopping_the_recorder(self, monkeypatch):
        # _processing is already True by then, so until an event of THIS turn
        # lands the screen still shows the previous turn's final state — the pill
        # read "Ready" while the button read "Working".
        stub = TurnStub(FakeAgent(["Use ", "Billy."]))
        events = _run(stub, monkeypatch)
        assert events[0].status == "transcribing"
        assert stub.stopped_at == 1, "recorder.stop() ran before the first event"

    def test_the_first_event_carries_no_tool_or_sources(self, monkeypatch):
        # This is what keeps the previous answer's QR and sources off the screen,
        # now that ui_state no longer gates them on processing.
        stub = TurnStub(FakeAgent(["Use ", "Billy."]))
        first = _run(stub, monkeypatch)[0]
        assert (first.tool, first.sources) == (None, ())

    def test_it_does_not_claim_to_be_answering_before_the_first_token(self, monkeypatch):
        stub = TurnStub(FakeAgent(["Use ", "Billy."]))
        events = _run(stub, monkeypatch)
        speaking = next(i for i, e in enumerate(events) if e.status == "speaking")
        assert events[speaking].joulie, "'Answering' must coincide with actual words"


class TestHeartbeat:
    """Without heartbeats the turn blocks on the token queue for the whole 6-10s
    to first token and emits nothing, so the poller sees an unchanged UiState and
    the screen is frozen for the part of the turn that most needs to look alive."""

    def test_the_wait_emits_events(self, monkeypatch):
        monkeypatch.setattr(config, "UI_HEARTBEAT_SECONDS", 0.05)
        stub = TurnStub(FakeAgent(["Heat pumps."], stall=0.3))
        events = _run(stub, monkeypatch)
        beats = [e for e in events if e.status == "thinking" and e.visitor]
        assert len(beats) > 1, "the wait produced no heartbeats"

    def test_a_heartbeat_reports_thinking_not_answering(self, monkeypatch):
        monkeypatch.setattr(config, "UI_HEARTBEAT_SECONDS", 0.05)
        events = _run(TurnStub(FakeAgent(["a."], stall=0.3)), monkeypatch)
        assert all(not e.joulie for e in events if e.status == "thinking")

    def test_a_heartbeat_carries_the_question_so_it_cannot_blank_the_screen(self, monkeypatch):
        # ui_state rebuilds the whole screen from the latest event, so a field
        # left at its default erases what is on screen rather than leaving it.
        monkeypatch.setattr(config, "UI_HEARTBEAT_SECONDS", 0.05)
        stub = TurnStub(FakeAgent(["a."], stall=0.3), transcript="what about solar?")
        beats = [e for e in _run(stub, monkeypatch) if e.status == "thinking"]
        assert beats and all(e.visitor == "what about solar?" for e in beats)

    def test_a_stall_mid_answer_does_not_blank_the_answer(self, monkeypatch):
        # XTTS and Ollama contend for the same Metal device, so the token queue can
        # go quiet after the answer has started. A heartbeat there must carry the
        # words written so far.
        monkeypatch.setattr(config, "UI_HEARTBEAT_SECONDS", 0.05)

        class Stalling(FakeAgent):
            def stream(self, text):
                yield "Heat pumps "
                time.sleep(0.3)
                yield "are efficient."

        events = _run(TurnStub(Stalling([])), monkeypatch)
        started = False
        for event in events:
            if event.joulie:
                started = True
            elif started and event.status in ("thinking", "speaking"):
                raise AssertionError("an event blanked the answer mid-stream")
        assert started

    def test_sources_land_during_the_wait_not_after_it(self, monkeypatch):
        # The point of the whole exercise: retrieval finishes about a second in, so
        # the publishers are real content to read while waiting for the answer.
        monkeypatch.setattr(config, "UI_HEARTBEAT_SECONDS", 0.05)
        sources = (Source("EECA", "authoritative"),)
        stub = TurnStub(FakeAgent(["a."], sources=sources, stall=0.3))
        stub.agent.last_sources = ()

        def stream(text):
            stub.agent.last_sources = sources
            time.sleep(0.3)
            yield "a."

        stub.agent.stream = stream
        events = _run(stub, monkeypatch)
        beats = [e for e in events if e.status == "thinking" and e.visitor]
        assert beats and beats[-1].sources == sources


class TestTurnSources:
    def test_sources_are_cleared_before_the_stream_starts(self, monkeypatch):
        # Cleared from the thread that owns the turn, not left to _build_messages
        # in the tee thread: a heartbeat landing in that gap would otherwise read
        # the PREVIOUS visitor's publishers.
        agent = FakeAgent(["a."], sources=(Source("EECA", "authoritative"),))
        agent.last_sources = (Source("Rewiring Aotearoa", "advocacy"),)
        stub = TurnStub(agent)
        events = _run(stub, monkeypatch)
        assert all("Rewiring" not in str(e.sources) for e in events)

    def test_sources_reach_the_screen_before_the_answer_finishes(self, monkeypatch):
        sources = (Source("EECA", "authoritative"),)
        stub = TurnStub(FakeAgent(["Heat ", "pumps ", "help."], sources=sources))
        events = _run(stub, monkeypatch)
        mid = [e for e in events if e.status == "speaking"]
        assert mid and mid[-1].sources == sources
        assert events[-1].status == "listening"

    def test_sources_never_vanish_once_shown(self, monkeypatch):
        # Retrieval fills last_sources partway through, so an unlatched read would
        # paint the panel and then blank it again.
        sources = (Source("EECA", "authoritative"),)
        agent = FakeAgent(["a ", "b ", "c."], sources=sources, sources_after=1)
        events = _run(TurnStub(agent), monkeypatch)
        seen = [bool(e.sources) for e in events if e.status == "speaking"]
        assert seen == sorted(seen), f"sources flickered: {seen}"


class TestMidStreamToolDetection:
    def test_the_tool_surfaces_while_joulie_is_still_talking(self, monkeypatch):
        stub = TurnStub(FakeAgent(["You can compare power plans with Billy. ",
                                   "It is free."]))
        events = _run(stub, monkeypatch)
        speaking = [e for e in events if e.status == "speaking"]
        assert speaking[-1].tool is not None
        assert speaking[-1].tool.id == "billy"

    def test_it_lands_on_the_same_tool_as_the_completed_reply(self, monkeypatch):
        # The counterexample to locking the first match: "compare power plans"
        # scores 19 and wins after sentence one, but "home energy savings
        # calculator" scores 30 and is the tool the answer actually recommends.
        reply = ["You could compare power plans with Billy. ",
                 "Then use the home energy savings calculator to see what you'd save."]
        events = _run(TurnStub(FakeAgent(reply)), monkeypatch)
        speaking = [e for e in events if e.status == "speaking"]
        assert speaking[-1].tool.id == "eeca_home_savings"
        assert events[-1].tool.id == "eeca_home_savings", "final event must agree"

    def test_detection_is_monotone_so_the_panel_cannot_regress(self):
        # The property that makes re-running detect_tool on a growing reply safe:
        # appending text can only add keyword matches, so the winning score never
        # falls and the last call equals a single call on the whole reply.
        reply = ("You could compare power plans with Billy. Then use the home "
                 "energy savings calculator, or NIWA SolarView for your roof.")
        scores = [_best_score(reply[:end]) for end in range(1, len(reply) + 1)]
        assert scores == sorted(scores), "a longer reply lost a keyword match"
        # And the tool the incremental path ends on is the one a single call gives.
        assert detect_tool(reply) is detect_tool(reply)


def _best_score(text: str) -> int:
    """Length of the keyword detect_tool would match — its own ranking metric."""
    return max((len(kw) for tool in REGISTRY.values() for kw in tool.keywords
                if kw in text.lower()), default=0)
