"""TalkController is deliberately free of HID and audio I/O, so the entire
visitor journey is testable here against a fake session."""

import pytest

from joulie.handset import TalkController


class FakeSession:
    """Mimics the SessionCore state transitions the controller depends on."""

    def __init__(self):
        self.calls: list[str] = []
        self._in_session = False
        self._recording = False
        self._processing = False

    # --- the Session protocol ------------------------------------------------
    @property
    def in_session(self) -> bool:
        return self._in_session

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def processing(self) -> bool:
        return self._processing

    def start_session(self) -> bool:
        self.calls.append("start_session")
        self._in_session = True
        return True

    def begin_recording(self) -> bool:
        self.calls.append("begin_recording")
        if self._processing or self._recording or not self._in_session:
            return False
        self._recording = True
        return True

    def interrupt(self) -> bool:
        self.calls.append("interrupt")
        return self._processing

    def end_session(self) -> None:
        self.calls.append("end_session")
        self._in_session = False
        self._recording = False
        self._processing = False

    # --- helpers for driving the fake ---------------------------------------
    def begin_answer(self):
        """What stream_finish_and_reply does: stop recording, start processing."""
        self._recording = False
        self._processing = True

    def finish_answer(self):
        self._processing = False


@pytest.fixture
def setup():
    session = FakeSession()
    turns: list[int] = []
    controller = TalkController(
        session,
        run_turn=lambda: turns.append(1) or session.begin_answer(),
        idle_timeout=45.0,
        silent_turns_to_end=2,
    )
    controller.set_initial_mic_state(live=False)
    return controller, session, turns


class TestSessionStart:
    def test_unmute_from_idle_starts_a_session_but_does_not_record(self, setup):
        controller, session, _ = setup
        controller.on_mic_live()
        assert session.calls == ["start_session"]

    def test_recording_starts_only_once_the_greeting_ends(self, setup):
        controller, session, _ = setup
        controller.on_mic_live()
        controller.on_greeting_finished()
        assert session.calls == ["start_session", "begin_recording"]
        assert session.recording

    def test_muting_during_the_greeting_leaves_the_session_armed(self, setup):
        controller, session, _ = setup
        controller.on_mic_live()
        controller.on_mic_muted()
        controller.on_greeting_finished()
        assert session.calls == ["start_session"]
        assert session.in_session and not session.recording

    def test_an_armed_session_records_on_the_next_unmute(self, setup):
        controller, session, _ = setup
        controller.on_mic_live()
        controller.on_mic_muted()
        controller.on_greeting_finished()
        controller.on_mic_live()
        assert session.recording


class TestTurns:
    def _to_listening(self, controller, session):
        controller.on_mic_live()
        controller.on_greeting_finished()
        session.calls.clear()

    def test_muting_while_recording_runs_the_turn(self, setup):
        controller, session, turns = setup
        self._to_listening(controller, session)
        controller.on_mic_muted()
        assert turns == [1]

    def test_muting_when_not_recording_does_not_run_a_turn(self, setup):
        controller, session, turns = setup
        controller.on_mic_live()
        controller.on_mic_muted()          # during the greeting
        assert turns == []

    def test_a_second_turn_runs_after_the_answer(self, setup):
        controller, session, turns = setup
        self._to_listening(controller, session)
        controller.on_mic_muted()
        session.finish_answer()
        controller.on_turn_finished(had_speech=True)
        controller.on_mic_live()
        assert session.recording
        controller.on_mic_muted()
        assert turns == [1, 1]

    def test_repeated_identical_reports_do_not_double_fire(self, setup):
        controller, session, turns = setup
        self._to_listening(controller, session)
        controller.on_mic_live()           # already live
        controller.on_mic_live()
        assert session.calls == []
        controller.on_mic_muted()
        controller.on_mic_muted()          # already muted
        assert turns == [1]


class TestBargeIn:
    def _answering(self, controller, session):
        controller.on_mic_live()
        controller.on_greeting_finished()
        controller.on_mic_muted()          # runs the turn -> processing
        session.calls.clear()

    def test_unmute_mid_answer_interrupts(self, setup):
        controller, session, _ = setup
        self._answering(controller, session)
        controller.on_mic_live()
        assert "interrupt" in session.calls

    def test_recording_is_deferred_until_the_turn_unwinds(self, setup):
        controller, session, _ = setup
        self._answering(controller, session)
        controller.on_mic_live()
        # begin_recording is refused while processing, so it must not be the
        # controller's job to call it yet.
        assert not session.recording
        session.finish_answer()
        controller.on_turn_finished(had_speech=True)
        assert session.recording

    def test_a_barge_in_the_visitor_takes_back_does_not_record(self, setup):
        controller, session, _ = setup
        self._answering(controller, session)
        controller.on_mic_live()
        controller.on_mic_muted()          # changed their mind
        session.finish_answer()
        controller.on_turn_finished(had_speech=True)
        assert not session.recording


class TestSessionEnd:
    def _listening(self, controller, session):
        controller.on_mic_live()
        controller.on_greeting_finished()
        session.calls.clear()

    def test_two_silent_turns_end_the_session(self, setup):
        controller, session, _ = setup
        self._listening(controller, session)
        controller.on_turn_finished(had_speech=False)
        assert session.in_session
        controller.on_turn_finished(had_speech=False)
        assert not session.in_session

    def test_a_successful_turn_resets_the_silent_counter(self, setup):
        controller, session, _ = setup
        self._listening(controller, session)
        controller.on_turn_finished(had_speech=False)
        controller.on_turn_finished(had_speech=True)
        controller.on_turn_finished(had_speech=False)
        assert session.in_session

    def test_idle_timeout_clears_an_abandoned_session(self, setup):
        controller, session, _ = setup
        self._listening(controller, session)
        controller.on_mic_muted()
        session.finish_answer()
        controller.on_turn_finished(had_speech=True)
        controller.tick(now=1000.0)        # arms the clock
        controller.tick(now=1000.0 + 44.0)
        assert session.in_session
        controller.tick(now=1000.0 + 46.0)
        assert not session.in_session

    def test_idle_timer_does_not_run_while_joulie_is_speaking(self, setup):
        controller, session, _ = setup
        self._listening(controller, session)
        controller.on_mic_muted()          # answering; mic muted the whole time
        controller.tick(now=1000.0)
        controller.tick(now=1000.0 + 600.0)
        assert session.in_session, "a long answer must not time out underneath the visitor"

    def test_idle_timer_does_not_run_while_the_mic_is_live(self, setup):
        controller, session, _ = setup
        self._listening(controller, session)
        controller.tick(now=1000.0)
        controller.tick(now=1000.0 + 600.0)
        assert session.in_session

    def test_no_timeout_when_there_is_no_session(self, setup):
        controller, session, _ = setup
        controller.tick(now=1000.0)
        controller.tick(now=1000.0 + 600.0)
        assert session.calls == []


class TestInitialState:
    def test_a_mic_left_live_does_not_start_a_session_by_itself(self, setup):
        controller, session, _ = setup
        controller.set_initial_mic_state(live=True)
        assert session.calls == []
        # Muting then unmuting is the visitor's first press pair.
        controller.on_mic_muted()
        controller.on_mic_live()
        assert session.calls == ["start_session"]

    def test_seeding_live_means_the_next_mute_is_seen(self, setup):
        controller, session, _ = setup
        controller.set_initial_mic_state(live=True)
        assert controller.mic_live
        controller.on_mic_muted()
        assert not controller.mic_live
