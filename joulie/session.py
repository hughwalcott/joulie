import sys
import threading
import time
from pathlib import Path

from pynput import keyboard

# Line-buffered stdout: keyboard-driven prints land immediately so we can see
# the pipeline progress in real time rather than waiting for a block flush.
sys.stdout.reconfigure(line_buffering=True)

from joulie import config
from joulie.audio import Recorder, Speaker, Transcriber
from joulie.llm import Agent
from joulie.rag import Retriever


class Kiosk:
    """
    Dev-mode kiosk loop. Stands in for the production handset:
      - SPACE (press and hold) = off-hook + record an utterance
      - SPACE released         = end-of-utterance, run a turn
      - ESC                    = on-hook, clear conversation context
      - Q                      = quit the kiosk

    Production will replace the keyboard with a USB handset hook switch.
    """

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
        self._processing = False  # True while STT/LLM/TTS pipeline is running
        self._quit = False
        self._space_down = False
        self._lock = threading.Lock()

    def _start_session(self):
        if self._in_session:
            return
        self._in_session = True
        self.agent.reset()
        # Play greeting on a background thread so the keyboard callback returns
        # immediately and the listener can process subsequent press/release events.
        # Without this, the pynput listener thread blocks for the ~10s greeting
        # playback and drops user keystrokes during that window.
        threading.Thread(target=self._play_greeting, daemon=True).start()

    def _play_greeting(self):
        print("\n[session] off-hook — starting conversation")
        try:
            if Path(config.GREETING_WAV).exists():
                self.speaker.play_wav(config.GREETING_WAV)
            else:
                self.speaker.say(config.GREETING)
        except Exception as exc:
            print(f"[session] greeting playback failed: {exc}")

    def _end_session(self):
        if not self._in_session:
            return
        print("[session] on-hook — clearing context")
        self.agent.reset()
        self._in_session = False
        # Force-clear processing so the kiosk recovers if a turn is stuck
        # (e.g. swap-thrash on low-memory hardware). The orphaned worker thread
        # will finish in the background and its output will be discarded.
        if self._processing:
            print("[session] forcibly clearing stuck turn state")
            self._processing = False
            self._recording = False

    def _begin_recording(self):
        if self._recording:
            return
        print("[mic] recording... (release SPACE to send)")
        self.recorder.start()
        self._recording = True

    def _finish_recording(self):
        if not self._recording:
            return
        if self._processing:
            print("[kiosk] still processing last turn, ignoring")
            # Even cleanup of the recorder must not block the keyboard thread —
            # Pa_StopStream on macOS CoreAudio can hang indefinitely.
            threading.Thread(target=self.recorder.stop, daemon=True).start()
            self._recording = False
            return
        self._recording = False
        self._processing = True
        # Move recorder.stop() off the keyboard thread. If PortAudio hangs in
        # stop(), only this worker hangs — the kiosk stays responsive.
        threading.Thread(target=self._stop_and_run, daemon=True).start()

    def _stop_and_run(self):
        try:
            print("[mic] stopping...")
            audio = self.recorder.stop()
            print(f"[mic] captured {audio.size / config.SAMPLE_RATE:.1f}s of audio")
            if audio.size < config.SAMPLE_RATE * 0.3:
                print("[mic] too short, ignoring")
                return
            self._run_turn(audio)
        except Exception as exc:
            print(f"[kiosk] stop_and_run error: {exc}")
        finally:
            self._processing = False

    def _run_turn(self, audio):
        try:
            print("[stt] transcribing...")
            text, lang = self.transcriber.transcribe(audio)
            if not text:
                print("[stt] no speech detected")
                return
            print(f"[visitor] ({lang}) {text}")
            print("[llm] sending to Ollama...")
            self.speaker.say_stream(self.agent.stream(text))
            print(f"[joulie] {self.agent.history[-1]['content']}")
        except Exception as exc:
            print(f"[agent] error: {exc}")
            try:
                self.speaker.say("Sorry, I had trouble thinking just then. Please try again.")
            except Exception:
                pass

    def _on_press(self, key):
        with self._lock:
            if key == keyboard.Key.space and not self._space_down:
                self._space_down = True
                if not self._in_session:
                    self._start_session()
                    return
                self._begin_recording()
            elif key == keyboard.Key.esc:
                self._end_session()
            elif hasattr(key, "char") and key.char == "q":
                self._quit = True
                return False

    def _on_release(self, key):
        if key == keyboard.Key.space:
            print("[kiosk] SPACE released")
        with self._lock:
            if key == keyboard.Key.space:
                self._space_down = False
                if self._recording:
                    self._finish_recording()
                else:
                    print("[kiosk] release ignored (no active recording)")

    def run(self):
        print("=" * 60)
        print("Joulie dev kiosk")
        print("  SPACE (first press)   = pick up handset, hear greeting")
        print("  SPACE (hold)          = record an utterance")
        print("  SPACE (release)       = send it")
        print("  ESC                   = hang up, clear context")
        print("  Q                     = quit")
        print("=" * 60)

        # Warm up Ollama after all model loading is done — by this point XTTS-v2
        # and the greeting WAV are already loaded, so the warmup reflects real
        # first-turn conditions and keeps the model hot just before the listener opens.
        print(f"[llm] warming up '{self.agent.model}'...")
        try:
            elapsed = self.agent.warmup()
            print(f"[llm] ready in {elapsed:.1f}s")
        except Exception as exc:
            print(f"[llm] warmup failed: {exc} — first turn may be slow")

        listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        listener.start()
        try:
            while not self._quit:
                time.sleep(0.1)
        finally:
            listener.stop()
            if self._recording:
                self.recorder.stop()
            self._end_session()
            print("[kiosk] goodbye")
