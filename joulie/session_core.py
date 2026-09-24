import queue
import threading
import time
from collections.abc import Iterator
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from joulie import config, metrics
from joulie.audio import Recorder, Speaker, Transcriber
from joulie.llm import Agent
from joulie.power import PowerSampler
from joulie.rag import Retriever
from joulie.sentences import split_sentences
from joulie.tools import Tool, detect_tool


@dataclass
class TurnEvent:
    """Update emitted during a conversational turn. UI drivers use these to
    reflect pipeline progress; kiosk mode can ignore them (SessionCore also
    prints tagged log lines for the terminal)."""
    status: str = ""              # transcribing / thinking / speaking / listening / idle
    visitor: Optional[str] = None
    joulie: Optional[str] = None  # cumulative reply text
    lang: Optional[str] = None
    error: Optional[str] = None
    # Populated once the reply completes if a tool from the registry was
    # detected in Joulie's response. UI drivers surface this as a QR panel.
    tool: Optional[Tool] = None
    # Publishers retrieval put in front of the model for this turn, surfaced
    # beside the QR panel. Empty when RAG is off or nothing cleared threshold.
    sources: tuple = ()


class SessionCore:
    """Pipeline logic shared between the pynput kiosk and the Gradio UI.
    Owns the recorder/transcriber/speaker/agent and the session state."""

    def __init__(self):
        self.recorder = Recorder()
        self.transcriber = Transcriber()
        self.speaker = Speaker()

        retriever = None
        if config.RAG_ENABLED and Retriever.available():
            retriever = Retriever()
        else:
            print("[rag] disabled or chroma_db not populated — running without RAG")
        self.agent = Agent(retriever=retriever)
        self.power = PowerSampler()

        # Metrics for the session currently in progress — reset in start_session,
        # flushed to a SessionSummary in end_session. See joulie/metrics.py.
        self._session_id: Optional[str] = None
        self._session_started_at: float = 0.0
        self._turn_metrics: list[metrics.TurnMetrics] = []
        self._turn_index: int = 0

        if not Path(config.GREETING_WAV).exists():
            try:
                self.speaker.prerender_greeting(config.GREETING, config.GREETING_WAV)
            except Exception as exc:
                print(f"[tts] greeting pre-render failed: {exc} — will synthesise live")

        self._recording = False
        self._in_session = False
        self._processing = False
        self._lock = threading.Lock()

        # Set by the handset driver: it must not start recording until the
        # greeting has finished playing, or the greeting lands in the recording.
        self.on_greeting_finished: Optional[Callable[[], None]] = None
        # Latest event of the current turn, regardless of which driver started
        # it. The Gradio UI polls this so handset-driven turns still render.
        self.last_event: Optional[TurnEvent] = None

    @property
    def in_session(self) -> bool:
        return self._in_session

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def processing(self) -> bool:
        return self._processing

    def warmup_llm(self) -> float:
        return self.agent.warmup()

    def start_session(self) -> bool:
        with self._lock:
            if self._in_session:
                return False
            self._in_session = True
        self.agent.reset()
        self._session_id = time.strftime("%Y%m%dT%H%M%S")
        self._session_started_at = time.time()
        self._turn_metrics = []
        self._turn_index = 0
        threading.Thread(target=self._play_greeting, daemon=True).start()
        return True

    def _play_greeting(self):
        print("\n[session] off-hook — starting conversation")
        try:
            if Path(config.GREETING_WAV).exists():
                self.speaker.play_wav(config.GREETING_WAV)
            else:
                self.speaker.say(config.GREETING)
        except Exception as exc:
            print(f"[session] greeting playback failed: {exc}")
        finally:
            # Fires even on playback failure — the driver still needs to move on.
            if self.on_greeting_finished is not None:
                try:
                    self.on_greeting_finished()
                except Exception as exc:
                    print(f"[session] greeting callback failed: {exc}")

    def interrupt(self) -> bool:
        """Barge-in — cut playback so the visitor doesn't have to sit through the
        rest of an answer. The turn's LLM stream unwinds on its own once the TTS
        threads see the flag. Returns True if there was something to stop."""
        if not self._processing:
            return False
        print("[session] barge-in — stopping playback")
        self.speaker.stop()
        return True

    def end_session(self):
        # Hanging up must silence Joulie immediately, before the state flip below
        # makes the in-flight turn unreachable.
        self.speaker.stop()
        with self._lock:
            if not self._in_session:
                return
            self._in_session = False
            # Force-clear stuck state so a hung turn can be abandoned.
            if self._processing:
                print("[session] forcibly clearing stuck turn state")
                self._processing = False
                self._recording = False
        print("[session] on-hook — clearing context")
        self.agent.reset()
        # Called unbound (not self._flush_session_summary()) so end_session keeps
        # working against the bare CoreStub in tests/test_session_core.py, which
        # only defines the attributes end_session historically touched.
        SessionCore._flush_session_summary(self)
        # The UI polls last_event and only blanks the screen while out of session,
        # so a surviving event would reappear the moment the next visitor starts
        # one — showing them the previous visitor's question and answer.
        self.last_event = None

    def _flush_session_summary(self) -> None:
        """Write the SessionSummary for the conversation that's ending
        (JTBD-08). No-op if this SessionCore was built without the metrics
        attrs (e.g. the bare stub in tests/test_session_core.py)."""
        turns = getattr(self, "_turn_metrics", None)
        session_id = getattr(self, "_session_id", None)
        if not turns or not session_id:
            return
        summary = metrics.build_summary(session_id, self._session_started_at, turns)
        metrics.write_summary(summary)
        print(
            f"[metrics] session {summary.session_id}: {summary.num_turns} turns, "
            f"avg_ttft={summary.avg_llm_ttft_seconds:.2f}s max_ttft={summary.max_llm_ttft_seconds:.2f}s "
            f"avg_tts_rtf={summary.avg_tts_rtf:.2f} max_tts_rtf={summary.max_tts_rtf:.2f} "
            f"throttled={summary.throttled}"
        )
        self._turn_metrics = []

    def begin_recording(self) -> bool:
        with self._lock:
            if not self._in_session or self._recording or self._processing:
                return False
            self._recording = True
        print("[mic] recording... (release to send)")
        try:
            self.recorder.start()
        except Exception as exc:
            print(f"[mic] recorder.start failed: {exc}")
            with self._lock:
                self._recording = False
            return False
        return True

    def stream_finish_and_reply(self) -> Iterator[TurnEvent]:
        """Run a turn, recording each event on last_event as it goes so drivers
        that don't consume the iterator directly (the Gradio poller) can follow
        a turn the handset started."""
        for event in self._run_turn():
            self.last_event = event
            yield event

    def _run_turn(self) -> Iterator[TurnEvent]:
        """Stop the recorder and run STT → LLM → TTS, yielding TurnEvents at each
        stage. Blocks for the whole turn duration (STT + LLM + full audio playback).
        Callers must invoke from a non-UI thread — the pynput kiosk dispatches to
        a worker thread; Gradio calls it from its own request-handler thread."""
        print(f"[core] stream_finish_and_reply entered (recording={self._recording}, processing={self._processing})")
        with self._lock:
            if not self._recording:
                print("[core] not recording — yielding early")
                yield TurnEvent(status="listening", error="not recording")
                return
            self._recording = False
            self._processing = True

        # Emitted before recorder.stop(), not after: _processing is already True,
        # and until an event of this turn lands the UI still reads the PREVIOUS
        # turn's final "listening" event — so the pill said "Ready" while the
        # button said "Working". This also clears the last answer's tool and
        # sources from the screen, which is what makes it safe to show them
        # mid-turn from here on.
        yield TurnEvent(status="transcribing")

        try:
            print("[mic] stopping...")
            audio = self.recorder.stop()
            # End of utterance — the zero point for the latency budget in
            # specs/design.md (median end-of-utterance -> start-of-speech <= 3s).
            turn_start = time.monotonic()
            turn_wall_start = time.time()
            tm = metrics.TurnMetrics(turn_index=self._turn_index + 1, started_at=turn_wall_start)
            print(f"[mic] captured {audio.size / config.SAMPLE_RATE:.1f}s of audio")
            if audio.size < config.SAMPLE_RATE * 0.3:
                print("[mic] too short, ignoring")
                yield TurnEvent(status="listening", error="too short")
                return

            print("[stt] transcribing...")
            text, lang = self.transcriber.transcribe(audio)
            tm.stt_seconds = time.monotonic() - turn_start
            print(f"[stt] +{tm.stt_seconds:.2f}s transcribe done")
            if not text:
                print("[stt] no speech detected")
                yield TurnEvent(status="listening", error="no speech")
                return

            print(f"[visitor] ({lang}) {text}")
            yield TurnEvent(status="thinking", visitor=text, lang=lang)

            # Tee the LLM token stream: TTS thread consumes one copy, UI updates from the other.
            ui_q: queue.Queue = queue.Queue()
            tts_q: queue.Queue = queue.Queue()

            def tee():
                first = True
                llm_start = time.monotonic()
                tokens = 0
                try:
                    for token in self.agent.stream(text):
                        tokens += 1
                        if first:
                            tm.llm_ttft_seconds = time.monotonic() - turn_start
                            print(f"[llm] +{tm.llm_ttft_seconds:.2f}s first token")
                            first = False
                        ui_q.put(token)
                        tts_q.put(token)
                except Exception as exc:
                    print(f"[llm] stream error: {exc}")
                finally:
                    tm.llm_total_seconds = time.monotonic() - llm_start
                    tm.llm_tokens = tokens
                    ui_q.put(None)
                    tts_q.put(None)

            def iter_tts():
                while True:
                    item = tts_q.get()
                    if item is None:
                        return
                    yield item

            def run_tts():
                try:
                    tts_stats = self.speaker.say_stream(iter_tts())
                    tm.tts_ttfa_seconds = tts_stats.get("ttfa_seconds") or 0.0
                    tm.tts_chunk_synth_seconds = tts_stats.get("chunk_synth_seconds", [])
                    tm.tts_chunk_rtf = tts_stats.get("chunk_rtf", [])
                except Exception as exc:
                    print(f"[tts] error: {exc}")

            # Cleared here rather than relying on Agent._build_messages, which does
            # it too but from inside the tee thread — so a heartbeat firing in the
            # gap between thread.start() and that clear would read the PREVIOUS
            # visitor's sources and attribute this answer to material it never saw.
            # Writing it from the thread that owns the turn closes that window: a
            # heartbeat can now only ever see () or this turn's own sources.
            self.agent.last_sources = ()

            threading.Thread(target=tee, daemon=True).start()
            tts_thread = threading.Thread(target=run_tts, daemon=True)
            tts_thread.start()

            reply = ""
            # Sticky: retrieval populates last_sources partway through the wait, so
            # an unlatched read would paint the panel, then blank it on the next
            # heartbeat that happened to land before the assignment.
            turn_sources: tuple = ()
            turn_tool: Optional[Tool] = None
            sentences_seen = 0
            while True:
                try:
                    item = ui_q.get(timeout=config.UI_HEARTBEAT_SECONDS)
                except queue.Empty:
                    # Heartbeats are what let the screen move during the 6-10s to
                    # first token. Every event has to be a COMPLETE snapshot —
                    # ui_state rebuilds the whole screen from last_event, so a
                    # field left at its default erases what is on screen rather
                    # than leaving it alone.
                    if not turn_sources:
                        turn_sources = self.agent.last_sources
                    yield TurnEvent(
                        status="speaking" if reply else "thinking",
                        visitor=text, joulie=reply, tool=turn_tool,
                        sources=turn_sources,
                    )
                    continue
                if item is None:
                    break
                reply += item
                if not turn_sources:
                    turn_sources = self.agent.last_sources
                # Re-run detection on the whole accumulated reply at each sentence
                # boundary, always taking the latest result. detect_tool scores by
                # matched-keyword length across the whole registry, so appending
                # text can only raise the winning score — the last call on the
                # complete reply is identical to running it once at the end. A
                # first-match lock would instead pin an incidental short keyword
                # ("niwa", "billy") over the tool the answer actually recommends.
                if any(p in item for p in ".?!"):
                    sentences, _ = split_sentences(reply)
                    if len(sentences) > sentences_seen:
                        sentences_seen = len(sentences)
                        turn_tool = detect_tool(reply) or turn_tool
                yield TurnEvent(status="speaking", visitor=text, joulie=reply,
                                tool=turn_tool, sources=turn_sources)

            # Block until audio playback completes so we don't cut off the tail.
            tts_thread.join()
            tm.turn_total_seconds = time.monotonic() - turn_start
            tm.power = self.power.window_stats(turn_wall_start, time.time())
            prompt_stats = self.agent.last_prompt_stats
            tm.prompt_chars = prompt_stats.get("prompt_chars", 0)
            tm.rag_chunk_count = prompt_stats.get("rag_chunk_count", 0)
            tm.rag_context_chars = prompt_stats.get("rag_context_chars", 0)
            tm.history_turns = prompt_stats.get("history_turns", 0)
            tm.history_trimmed = prompt_stats.get("history_trimmed", False)
            tm.rag_retrieval_seconds = prompt_stats.get("retrieval_seconds", 0.0)
            tm.llm_post_ttft_seconds = self.agent.last_post_ttft_seconds
            eval_stats = self.agent.last_eval_stats
            tm.prompt_eval_count = eval_stats.get("prompt_eval_count", 0)
            tm.prompt_eval_seconds = eval_stats.get("prompt_eval_seconds", 0.0)
            tm.prompt_eval_tokens_per_second = eval_stats.get("prompt_eval_tokens_per_second", 0.0)
            tm.eval_count = eval_stats.get("eval_count", 0)
            tm.eval_seconds = eval_stats.get("eval_seconds", 0.0)
            self._turn_metrics.append(tm)
            self._turn_index += 1
            metrics.append_turn(self._session_id, tm)
            power_bit = ""
            if tm.power:
                # .get(key, 0) only substitutes when the key is absent — window_stats
                # always includes these keys but with None if that line never
                # parsed (e.g. a macOS powermetrics version that phrases GPU
                # residency differently), so fall back explicitly instead.
                power_bit = (
                    f" gpu={tm.power.get('gpu_power_mw_avg') or 0:.0f}mW"
                    f" gpu_freq={tm.power.get('gpu_freq_mhz_avg') or 0:.0f}MHz"
                    f" gpu_active={tm.power.get('gpu_active_pct_avg') or 0:.0f}%"
                    f" mem={tm.power.get('mem_used_pct_avg') or 0:.0f}%"
                    f" swap={tm.power.get('swap_used_mb_max') or 0:.0f}MB"
                    f" thermal={tm.power.get('thermal_pressure_max')}"
                )
            print(
                f"[metrics] turn {tm.turn_index}: stt={tm.stt_seconds:.2f}s "
                f"rag={tm.rag_retrieval_seconds:.2f}s "
                f"ttft={tm.llm_ttft_seconds:.2f}s(llm {tm.llm_post_ttft_seconds:.2f}s) "
                f"ttfa={tm.tts_ttfa_seconds:.2f}s "
                f"max_rtf={tm.tts_rtf_max:.2f} prompt={tm.prompt_chars}chars "
                f"history={tm.history_turns}turns rag={tm.rag_chunk_count}chunks "
                f"prefill={tm.prompt_eval_count}tok/{tm.prompt_eval_seconds:.2f}s"
                f"({tm.prompt_eval_tokens_per_second:.0f}tok/s)"
                f"{' TRIMMED' if tm.history_trimmed else ''}"
                f"{power_bit}"
            )
            print(f"[turn] +{time.monotonic() - turn_start:.2f}s turn complete")
            print(f"[joulie] {reply}")
            detected = detect_tool(reply)
            if detected is not None:
                print(f"[tool] surfaced: {detected.id} ({detected.name})")
            else:
                print("[tool] no keyword match in reply — tool panel stays hidden")
            yield TurnEvent(status="listening", visitor=text, joulie=reply,
                            tool=detected, sources=self.agent.last_sources)

        except Exception as exc:
            print(f"[agent] error: {exc}")
            try:
                self.speaker.say("Sorry, I had trouble thinking just then. Please try again.")
            except Exception:
                pass
            yield TurnEvent(status="listening", error=str(exc))
        finally:
            with self._lock:
                self._processing = False
