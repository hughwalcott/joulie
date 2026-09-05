"""The Gradio poller repaints on a timer. Emitting a value for every component
on every tick made the status pill visibly flicker several times a second, so
what matters here is that an unchanged pipeline yields an unchanged UiState."""

from joulie.session_core import TurnEvent
from joulie.tools import REGISTRY
from joulie.ui import UiState, ui_state


class FakeCore:
    def __init__(self, **kw):
        self.in_session = kw.get("in_session", False)
        self.recording = kw.get("recording", False)
        self.processing = kw.get("processing", False)
        self.last_event = kw.get("last_event")


class TestIdle:
    def test_no_session_is_idle_with_a_disabled_button(self):
        assert ui_state(FakeCore()) == UiState("idle", "", "", "disabled", None)

    def test_a_stale_event_cannot_leak_into_the_idle_screen(self):
        stale = TurnEvent(status="speaking", visitor="hi", joulie="there")
        assert ui_state(FakeCore(last_event=stale)).visitor == ""

    def test_idle_is_stable_across_polls(self):
        core = FakeCore()
        assert ui_state(core) == ui_state(core)


class TestInSession:
    def test_listening_when_idle_in_session(self):
        state = ui_state(FakeCore(in_session=True))
        assert (state.status, state.button) == ("listening", "idle")

    def test_recording(self):
        state = ui_state(FakeCore(in_session=True, recording=True))
        assert (state.status, state.button) == ("recording", "recording")

    def test_processing_uses_the_event_status(self):
        event = TurnEvent(status="speaking", visitor="q", joulie="partial")
        state = ui_state(FakeCore(in_session=True, processing=True, last_event=event))
        assert (state.status, state.button) == ("speaking", "working")
        assert state.joulie == "partial"

    def test_processing_without_a_status_falls_back_to_thinking(self):
        event = TurnEvent(status="", visitor="q")
        state = ui_state(FakeCore(in_session=True, processing=True, last_event=event))
        assert state.status == "thinking"

    def test_stable_across_polls_mid_turn(self):
        core = FakeCore(in_session=True, processing=True,
                        last_event=TurnEvent(status="speaking", visitor="q", joulie="a"))
        assert ui_state(core) == ui_state(core), "an unchanged turn must not repaint"


class TestToolPanel:
    def test_tool_surfaces_once_the_turn_is_done(self):
        tool = next(iter(REGISTRY.values()))
        event = TurnEvent(status="listening", visitor="q", joulie="a", tool=tool)
        state = ui_state(FakeCore(in_session=True, last_event=event))
        assert state.tool_id == tool.id

    def test_tool_is_withheld_while_still_processing(self):
        event = TurnEvent(status="speaking", visitor="q", joulie="a", tool=next(iter(REGISTRY.values())))
        state = ui_state(FakeCore(in_session=True, processing=True, last_event=event))
        assert state.tool_id is None


class TestChangeDetection:
    def test_state_changes_when_the_reply_grows(self):
        base = dict(in_session=True, processing=True)
        first = ui_state(FakeCore(**base, last_event=TurnEvent(status="speaking", joulie="He")))
        second = ui_state(FakeCore(**base, last_event=TurnEvent(status="speaking", joulie="Heat")))
        assert first != second

    def test_state_changes_when_recording_starts(self):
        assert ui_state(FakeCore(in_session=True)) != ui_state(
            FakeCore(in_session=True, recording=True))

    def test_field_order_matches_the_output_components(self):
        # poll_handset zips UiState fields onto [status, visitor, joulie,
        # record_btn, tool_caption]; a reordering here would silently paint the
        # wrong component.
        from dataclasses import fields
        assert [f.name for f in fields(UiState)] == [
            "status", "visitor", "joulie", "button", "tool_id"]
