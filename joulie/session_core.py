import queue
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from joulie import config
from joulie.audio import Recorder, Speaker, Transcriber
from joulie.llm import Agent
from joulie.rag import Retriever
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

        if not Path(config.GREETING_WAV).exists():
            try:
                self.speaker.prerender_greeting(config.GREETING, config.GREETING_WAV)
            except Exception as exc:
                print(f"[tts] greeting pre-render failed: {exc} — will synthesise live")

        self._recording = False
        self._in_session = False
        self._processing = False
        self._lock = threading.Lock()

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

        try:
            print("[mic] stopping...")
            audio = self.recorder.stop()
            # End of utterance — the zero point for the latency budget in
            # specs/design.md (median end-of-utterance -> start-of-speech <= 3s).
            turn_start = time.monotonic()
            print(f"[mic] captured {audio.size / config.SAMPLE_RATE:.1f}s of audio")
            if audio.size < config.SAMPLE_RATE * 0.3:
                print("[mic] too short, ignoring")
                yield TurnEvent(status="listening", error="too short")
                return

            yield TurnEvent(status="transcribing")
            print("[stt] transcribing...")
            text, lang = self.transcriber.transcribe(audio)
            print(f"[stt] +{time.monotonic() - turn_start:.2f}s transcribe done")
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
                try:
                    for token in self.agent.stream(text):
                        if first:
                            print(f"[llm] +{time.monotonic() - turn_start:.2f}s first token")
                            first = False
                        ui_q.put(token)
                        tts_q.put(token)
                except Exception as exc:
                    print(f"[llm] stream error: {exc}")
                finally:
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
                    self.speaker.say_stream(iter_tts())
                except Exception as exc:
                    print(f"[tts] error: {exc}")

            threading.Thread(target=tee, daemon=True).start()
            tts_thread = threading.Thread(target=run_tts, daemon=True)
            tts_thread.start()

            reply = ""
            yield TurnEvent(status="speaking", visitor=text, joulie="")
            while True:
                item = ui_q.get()
                if item is None:
                    break
                reply += item
                yield TurnEvent(status="speaking", visitor=text, joulie=reply)

            # Block until audio playback completes so we don't cut off the tail.
            tts_thread.join()
            print(f"[turn] +{time.monotonic() - turn_start:.2f}s turn complete")
            print(f"[joulie] {reply}")
            detected = detect_tool(reply)
            if detected is not None:
                print(f"[tool] surfaced: {detected.id} ({detected.name})")
            else:
                print("[tool] no keyword match in reply — tool panel stays hidden")
            yield TurnEvent(status="listening", visitor=text, joulie=reply, tool=detected)

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
