import sys
import threading
import time

from pynput import keyboard

from joulie import config
from joulie.handset import attach
from joulie.session_core import SessionCore

# Line-buffered stdout so kiosk-mode prints flush immediately.
sys.stdout.reconfigure(line_buffering=True)


class Kiosk:
    """
    Dev-mode kiosk loop. Stands in for the production handset:
      - SPACE (press and hold) = off-hook + record an utterance
      - SPACE released         = end-of-utterance, run a turn
      - ESC                    = on-hook, clear conversation context
      - Q                      = quit the kiosk

    Delegates all pipeline logic to SessionCore so the Gradio UI can share it.
    """

    def __init__(self):
        self.core = SessionCore()
        # Optional — returns None if the mic isn't present, leaving SPACE in charge.
        self.handset = attach(self.core)
        self._space_down = False
        self._quit = False
        self._lock = threading.Lock()

    def _drain_events(self):
        for _ in self.core.stream_finish_and_reply():
            pass  # SessionCore prints tagged logs; kiosk mode ignores events

    def _on_press(self, key):
        with self._lock:
            if key == keyboard.Key.space and not self._space_down:
                self._space_down = True
                if not self.core.in_session:
                    self.core.start_session()
                    return
                # Pressing SPACE while Joulie is talking is a barge-in, not a
                # record — begin_recording() would refuse anyway while processing.
                if self.core.processing:
                    self.core.interrupt()
                    return
                self.core.begin_recording()
            elif key == keyboard.Key.esc:
                self.core.end_session()
            elif hasattr(key, "char") and key.char == "q":
                self._quit = True
                return False

    def _on_release(self, key):
        if key == keyboard.Key.space:
            print("[kiosk] SPACE released")
        with self._lock:
            if key == keyboard.Key.space:
                self._space_down = False
                if self.core.recording:
                    threading.Thread(target=self._drain_events, daemon=True).start()

    def run(self):
        print("=" * 60)
        print("Joulie dev kiosk")
        print(f"  {config.DISCLAIMER}")
        print("-" * 60)
        if self.handset is not None:
            print("  MIC MUTE BUTTON       = the whole conversation:")
            print("      unmute            -> start session / start talking")
            print("      mute              -> send your question")
            print("      unmute mid-answer -> interrupt and ask the next thing")
            print("      leave muted       -> session clears itself")
            print("-" * 60)
        print("  SPACE (first press)   = pick up handset, hear greeting")
        print("  SPACE (hold)          = record an utterance")
        print("  SPACE (release)       = send it")
        print("  SPACE (while talking) = interrupt Joulie")
        print("  ESC                   = hang up, clear context")
        print("  Q                     = quit")
        print("=" * 60)

        print(f"[llm] warming up '{self.core.agent.model}'...")
        try:
            elapsed = self.core.warmup_llm()
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
            self.core.end_session()
            print("[kiosk] goodbye")
