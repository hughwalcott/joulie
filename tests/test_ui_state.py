"""The Gradio poller repaints on a timer. Emitting a value for every component
on every tick made the status pill visibly flicker several times a second, so
what matters here is that an unchanged pipeline yields an unchanged UiState."""

from joulie import config
from joulie.session_core import TurnEvent
from joulie.tools import REGISTRY
from joulie.rag import Retriever, Source
from joulie.ui import UiState, _sources_html, _stage_html, ui_state


class FakeRecorder:
    def __init__(self, mic_live):
        self.mic_live = mic_live


class FakeCore:
    def __init__(self, **kw):
        self.in_session = kw.get("in_session", False)
        self.recording = kw.get("recording", False)
        self.processing = kw.get("processing", False)
        self.last_event = kw.get("last_event")
        self.recorder = FakeRecorder(kw.get("mic_live", False))


class TestIdle:
    def test_no_session_is_idle_with_a_disabled_button(self):
        assert ui_state(FakeCore()) == UiState(
            "idle", "", "", "disabled", None, False, "disabled", (), "attract")

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

    def test_tool_surfaces_mid_answer(self):
        # A visitor who has to sit through the whole spoken answer before the QR
        # appears has usually stopped looking. The turn puts the tool on its
        # streaming events as soon as the reply names one, so it shows while
        # Joulie is still talking.
        tool = next(iter(REGISTRY.values()))
        event = TurnEvent(status="speaking", visitor="q", joulie="a", tool=tool)
        state = ui_state(FakeCore(in_session=True, processing=True, last_event=event))
        assert state.tool_id == tool.id

    def test_a_turn_that_names_no_tool_shows_none(self):
        # What keeps the previous answer's QR off the screen is the turn clearing
        # it on its own first event, not a processing gate here.
        event = TurnEvent(status="transcribing")
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
        # poll_handset zips UiState fields onto _poll_outputs positionally. That
        # list is now built from a name-keyed dict in build_app, so a field with
        # no component raises at startup — but the names still have to match, and
        # a rename that missed the dict would paint the wrong component.
        from dataclasses import fields
        assert [f.name for f in fields(UiState)] == [
            "status", "visitor", "joulie", "button", "tool_id", "mic_live",
            "end_button", "sources", "stage"]


class TestMicIndicator:
    def test_mic_state_is_reported_out_of_session(self):
        # The mute button is the one control that can start a session, so its
        # state has to be on screen before there is a session to show.
        assert ui_state(FakeCore(mic_live=True)).mic_live is True
        assert ui_state(FakeCore(mic_live=False)).mic_live is False

    def test_mic_state_is_reported_in_session(self):
        assert ui_state(FakeCore(in_session=True, mic_live=True)).mic_live is True

    def test_muting_the_mic_repaints(self):
        assert ui_state(FakeCore(mic_live=True)) != ui_state(FakeCore(mic_live=False))

    def test_a_core_without_a_recorder_is_reported_muted(self):
        core = FakeCore()
        del core.recorder
        assert ui_state(core).mic_live is False


class TestEndButton:
    """Kiosk mode hides Start/Stop/Tap-to-speak — the mute button does those
    jobs, and pressing them while muted records silence and trips the
    silent-turn counter — so End Session absorbs the barge-in."""

    def test_disabled_out_of_session(self):
        assert ui_state(FakeCore()).end_button == "disabled"

    def test_ends_when_in_session_and_quiet(self):
        assert ui_state(FakeCore(in_session=True)).end_button == "end"

    def test_stops_talking_while_answering(self):
        event = TurnEvent(status="speaking", visitor="q", joulie="a long answer")
        state = ui_state(FakeCore(in_session=True, processing=True, last_event=event))
        assert state.end_button == "stop"

    def test_reverts_to_end_once_the_answer_finishes(self):
        answering = ui_state(FakeCore(in_session=True, processing=True,
                                      last_event=TurnEvent(status="speaking")))
        done = ui_state(FakeCore(in_session=True,
                                 last_event=TurnEvent(status="listening")))
        assert (answering.end_button, done.end_button) == ("stop", "end")

    def test_recording_is_not_a_barge_in(self):
        # Recording means the visitor is talking, not Joulie — nothing to stop.
        assert ui_state(FakeCore(in_session=True, recording=True)).end_button == "end"


class TestSources:
    """The panel is headed "Sources consulted", not "Citations" — it reports
    what retrieval put in the prompt, which is not a claim about what the answer
    leaned on. Stance rides along so advocacy can't be read as regulator."""

    def test_no_sources_out_of_session(self):
        assert ui_state(FakeCore()).sources == ()

    def test_sources_surface_once_the_turn_is_done(self):
        sources = (Source("EECA", "authoritative"),)
        event = TurnEvent(status="listening", visitor="q", joulie="a", sources=sources)
        assert ui_state(FakeCore(in_session=True, last_event=event)).sources == sources

    def test_sources_surface_mid_turn(self):
        # Retrieval finishes about a second into a 6-10s wait, so the publishers
        # are the one piece of real content available while the visitor waits.
        sources = (Source("EECA", "authoritative"),)
        event = TurnEvent(status="thinking", visitor="q", sources=sources)
        state = ui_state(FakeCore(in_session=True, processing=True, last_event=event))
        assert state.sources == sources

    def test_the_previous_answers_sources_cannot_survive_into_a_new_turn(self):
        # This is what the old processing gate was for, and the replacement is
        # stricter: ui_state reads the event and nothing else, and a turn's first
        # event carries no sources — so the panel clears the moment a turn starts
        # rather than lingering until it reaches the LLM.
        state = ui_state(FakeCore(in_session=True, processing=True,
                                  last_event=TurnEvent(status="transcribing")))
        assert state.sources == ()

    def test_a_turn_without_rag_reports_none(self):
        event = TurnEvent(status="listening", visitor="q", joulie="a")
        assert ui_state(FakeCore(in_session=True, last_event=event)).sources == ()


class TestStage:
    """The stage panel fills the right-hand column, which was blank in every
    state but "answer finished". Its value is a bare state token — see
    test_stage_is_a_state_token_not_markup for why that matters."""

    def test_standby_invites(self):
        assert ui_state(FakeCore()).stage == "attract"

    def test_in_session_and_quiet_is_ready(self):
        assert ui_state(FakeCore(in_session=True)).stage == "ready"

    def test_recording_shows_the_on_air_panel(self):
        assert ui_state(FakeCore(in_session=True, recording=True)).stage == "listening"

    def test_processing_tracks_the_pipeline_stage(self):
        for status in ("transcribing", "thinking", "speaking"):
            state = ui_state(FakeCore(in_session=True, processing=True,
                                      last_event=TurnEvent(status=status)))
            assert state.stage == status

    def test_stage_is_a_state_token_not_markup(self):
        # Anything time-derived in this value — an elapsed count, a frame index —
        # would differ on every poll tick and repaint the panel 2.5x a second.
        # All the motion lives in CSS keyframes instead.
        cores = [FakeCore(), FakeCore(in_session=True),
                 FakeCore(in_session=True, recording=True),
                 FakeCore(in_session=True, processing=True,
                          last_event=TurnEvent(status="thinking"))]
        for core in cores:
            stage = ui_state(core).stage
            assert "<" not in stage and stage.isalpha()


class TestStageHtml:
    def test_standby_names_the_one_physical_action(self):
        # Asserted against the config constant, not against particular wording:
        # the copy is a product decision that changes (it has already moved from
        # the handset to the mic's mute button).
        html = _stage_html("attract", kiosk_mode=True)
        assert config.KIOSK_ATTRACT_CTA in html

    def test_browser_mode_names_its_own_way_in(self):
        # The kiosk CTA points at hardware a browser tester does not have.
        html = _stage_html("attract", kiosk_mode=False)
        assert config.KIOSK_ATTRACT_CTA_BROWSER in html
        assert config.KIOSK_ATTRACT_CTA not in html

    def test_standby_offers_the_sign_wording_from_the_table(self):
        # Scenario A1's visitor arrives having read "Ask me about going electric",
        # so the screen repeats it back rather than leaving her to invent one.
        assert "Ask me about going electric" in _stage_html("attract", True)

    def test_every_example_question_is_offered(self):
        html = _stage_html("attract", kiosk_mode=True)
        for question in config.KIOSK_EXAMPLE_QUESTIONS:
            assert question in html

    def test_the_in_session_prompt_leaves_room_for_the_qr(self):
        # This is the state that coexists with both the QR panel and the sources,
        # and #col-right must not scroll — a full card here would push the QR
        # below the fold, which the kiosk geometry forbids.
        html = _stage_html("ready", kiosk_mode=True)
        assert config.KIOSK_READY_CTA in html
        assert "stage-compact" in html
        assert "Try asking" not in html

    def test_listening_is_legible_from_across_a_room(self):
        assert "LISTENING" in _stage_html("listening", kiosk_mode=True)

    def test_the_tracker_marks_earlier_steps_done_and_later_ones_pending(self):
        html = _stage_html("thinking", kiosk_mode=True)
        # Heard you + Transcribing behind it, Answering still ahead.
        assert html.count('data-step="done"') == 2
        assert html.count('data-step="active"') == 1
        assert html.count('data-step="pending"') == 1

    def test_the_tracker_only_ever_moves_forwards(self):
        # Each stage's active row must be at least as far along as the last, or the
        # panel would be reporting progress it has not made.
        positions = []
        for stage in ("transcribing", "thinking"):
            html = _stage_html(stage, kiosk_mode=True)
            positions.append(html.count('data-step="done"'))
        assert positions == sorted(positions)

    def test_answering_collapses_so_the_qr_has_room(self):
        # #col-right does not scroll by design, so the tracker gives its height
        # back once every milestone is behind it.
        html = _stage_html("speaking", kiosk_mode=True)
        assert "stage-compact" in html
        assert "Transcribing" not in html


class TestSourceSummary:
    def test_chunks_collapse_to_one_row_per_publisher(self):
        chunks = [{"publisher_short": "EECA", "stance": "authoritative"},
                  {"publisher_short": "EECA", "stance": "authoritative"},
                  {"publisher_short": "Rewiring Aotearoa", "stance": "advocacy"}]
        assert Retriever.summarise_sources(chunks) == (
            Source("EECA", "authoritative"), Source("Rewiring Aotearoa", "advocacy"))

    def test_most_retrieved_publisher_leads(self):
        chunks = [{"publisher_short": "Rewiring Aotearoa", "stance": "advocacy"},
                  {"publisher_short": "EECA", "stance": "authoritative"},
                  {"publisher_short": "EECA", "stance": "authoritative"}]
        assert Retriever.summarise_sources(chunks)[0].publisher == "EECA"

    def test_stance_is_never_dropped(self):
        chunks = [{"publisher_short": "Rewiring Aotearoa", "stance": "advocacy"}]
        assert Retriever.summarise_sources(chunks)[0].stance == "advocacy"

    def test_missing_publisher_is_not_silently_blank(self):
        assert Retriever.summarise_sources([{"stance": "authoritative"}])[0].publisher == "unknown"

    def test_no_chunks_means_no_sources(self):
        assert Retriever.summarise_sources([]) == ()


class TestSourcesHtml:
    def test_advocacy_is_labelled_distinctly_from_government(self):
        html = _sources_html((Source("EECA", "authoritative"),
                              Source("Rewiring Aotearoa", "advocacy")))
        assert 'data-stance="authoritative"' in html and ">Government<" in html
        assert 'data-stance="advocacy"' in html and ">Advocacy<" in html

    def test_heading_does_not_claim_citation(self):
        html = _sources_html((Source("EECA", "authoritative"),))
        assert "Sources consulted" in html
        assert "Citation" not in html
