import threading
import time

from pynput import keyboard

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

        self._recording = False
        self._in_session = False
        self._quit = False
        self._space_down = False
        self._lock = threading.Lock()

    def _start_session(self):
        if self._in_session:
            return
        self._in_session = True
        self.agent.reset()
        print("\n[session] off-hook — starting conversation")
        self.speaker.say(config.GREETING)

    def _end_session(self):
        if not self._in_session:
            return
        print("[session] on-hook — clearing context")
        self.agent.reset()
        self._in_session = False

    def _begin_recording(self):
        if self._recording:
            return
        print("[mic] recording... (release SPACE to send)")
        self.recorder.start()
        self._recording = True

    def _finish_recording(self):
        if not self._recording:
            return
        audio = self.recorder.stop()
        self._recording = False
        if audio.size < config.SAMPLE_RATE * 0.3:
            print("[mic] too short, ignoring")
            return
        print("[stt] transcribing...")
        text, lang = self.transcriber.transcribe(audio)
        if not text:
            print("[stt] no speech detected")
            return
        print(f"[visitor] ({lang}) {text}")
        try:
            reply = self.agent.reply(text)
        except Exception as exc:
            print(f"[agent] error: {exc}")
            self.speaker.say("Sorry, I had trouble thinking just then. Please try again.")
            return
        print(f"[joulie] {reply}")
        self.speaker.say(reply)

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
        with self._lock:
            if key == keyboard.Key.space:
                self._space_down = False
                if self._recording:
                    self._finish_recording()

    def run(self):
        print("=" * 60)
        print("Joulie dev kiosk")
        print("  SPACE (first press)   = pick up handset, hear greeting")
        print("  SPACE (hold)          = record an utterance")
        print("  SPACE (release)       = send it")
        print("  ESC                   = hang up, clear context")
        print("  Q                     = quit")
        print("=" * 60)
        print(f"[llm] warming up '{self.agent.model}' (first load can take 30–90s)...")
        try:
            elapsed = self.agent.warmup()
            print(f"[llm] ready in {elapsed:.1f}s")
        except Exception as exc:
            print(f"[llm] warmup failed: {exc} — first turn may hang or error")

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
