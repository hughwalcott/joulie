"""Drive Joulie from the USB mic's mute button.

The JBL Quantum Stream Talk (VID 0x0ECB / PID 0x20AF) enumerates as a telephony
HID device. Its mute button reports *state*, not edges — report 0x06 with a
single payload byte, 0x01 live and 0x00 muted — and the firmware gates the audio
to exact zeros while muted, so the mic genuinely cannot hear the room. Both facts
were measured against the audio stream, not read from a spec.

Unmuted means "Joulie is listening", which makes the hardware mute LED an honest
indicator with nothing for us to drive. The whole kiosk runs off this one bit:
see TalkController for the state machine.
"""
import atexit
import queue
import threading
import time
from collections.abc import Callable
from typing import Optional, Protocol

from joulie import config


class Session(Protocol):
    """The slice of SessionCore that TalkController drives. Declared so the
    controller can be tested against a fake without audio or models."""

    @property
    def in_session(self) -> bool: ...
    @property
    def recording(self) -> bool: ...
    @property
    def processing(self) -> bool: ...
    def start_session(self) -> bool: ...
    def begin_recording(self) -> bool: ...
    def interrupt(self) -> bool: ...
    def end_session(self) -> None: ...


class TalkController:
    """Maps mute-button transitions onto session actions.

    Deliberately free of HID and audio I/O so the whole visitor journey is
    testable: feed it on_mic_live/on_mic_muted/on_greeting_finished/on_turn_finished
    and drive the idle timeout by passing an explicit `now` to tick().
    """

    def __init__(
        self,
        session: Session,
        run_turn: Callable[[], None],
        idle_timeout: float = config.HANDSET_IDLE_TIMEOUT,
        silent_turns_to_end: int = config.HANDSET_SILENT_TURNS_TO_END,
    ):
        self._session = session
        self._run_turn = run_turn
        self._idle_timeout = idle_timeout
        self._silent_turns_to_end = silent_turns_to_end

        # Set by attach() so the HID reader lives as long as the controller.
        self.handset: Optional["Handset"] = None
        self._mic_live = False
        self._greeting_pending = False
        # Set when the visitor barges in: begin_recording() is refused while the
        # interrupted turn unwinds, so the record is deferred to on_turn_finished.
        self._pending_record = False
        self._silent_turns = 0
        self._muted_since: Optional[float] = None
        self._lock = threading.RLock()

    @property
    def mic_live(self) -> bool:
        return self._mic_live

    def set_initial_mic_state(self, live: bool) -> None:
        """Seed state before the first HID report. The mic is normally muted
        between visitors, but it can be left live, and starting out wrong costs
        the next visitor a press."""
        with self._lock:
            self._mic_live = live
            self._muted_since = None
        print(f"[handset] initial mic state: {'live' if live else 'muted'}")

    # ------------------------------------------------------------------ events

    def on_mic_live(self) -> None:
        with self._lock:
            if self._mic_live:
                return
            self._mic_live = True
            self._muted_since = None
            print("[handset] mic live")

            if not self._session.in_session:
                print("[handset] starting session")
                self._greeting_pending = True
                self._session.start_session()
                return

            if self._session.processing:
                # Barge-in. The turn needs a moment to unwind before the recorder
                # will accept a start, so remember the intent.
                print("[handset] barge-in — stopping Joulie, will record")
                self._pending_record = True
                self._session.interrupt()
                return

            if self._greeting_pending or self._session.recording:
                return

            self._session.begin_recording()

    def on_mic_muted(self) -> None:
        with self._lock:
            if not self._mic_live:
                return
            self._mic_live = False
            # tick() arms the clock, so the idle timeout has a single time
            # source rather than mixing this handler's clock with tick's.
            self._muted_since = None
            self._pending_record = False
            print("[handset] mic muted")

            if self._session.recording:
                self._run_turn()

    def on_greeting_finished(self) -> None:
        with self._lock:
            if not self._greeting_pending:
                return
            self._greeting_pending = False
            # The mic state right now decides: a visitor who muted during the
            # greeting stays in session, armed, and unmuting starts the turn.
            if self._mic_live and self._session.in_session:
                self._session.begin_recording()
            else:
                print("[handset] greeting done but mic muted — armed, not recording")

    def on_turn_finished(self, had_speech: bool) -> None:
        with self._lock:
            if had_speech:
                self._silent_turns = 0
            else:
                self._silent_turns += 1
                print(f"[handset] silent turn {self._silent_turns}/{self._silent_turns_to_end}")
                if self._silent_turns >= self._silent_turns_to_end:
                    print(f"[handset] {self._silent_turns_to_end} silent turns — ending session")
                    self._pending_record = False
                    self._silent_turns = 0
                    self._session.end_session()
                    return

            if self._pending_record:
                self._pending_record = False
                if self._mic_live and self._session.in_session:
                    self._session.begin_recording()

    def tick(self, now: Optional[float] = None) -> None:
        """Expire an abandoned session. The timer only runs while the mic is
        muted AND Joulie is silent — a visitor listening to a long answer must
        never have the session time out underneath them."""
        with self._lock:
            if not self._session.in_session or self._mic_live:
                return
            if self._session.processing or self._session.recording:
                # Still answering; hold the clock rather than counting through it.
                self._muted_since = None
                return
            now = time.monotonic() if now is None else now
            if self._muted_since is None:
                self._muted_since = now
                return
            if now - self._muted_since >= self._idle_timeout:
                print(f"[handset] idle {self._idle_timeout:.0f}s — clearing session")
                self._muted_since = None
                self._silent_turns = 0
                self._pending_record = False
                self._session.end_session()


class Handset:
    """Reads the mute button off the mic's HID interface.

    One long-lived handle for the process lifetime and a blocking read on a
    daemon thread — the same shape as Recorder, and for the same reason. A
    non-blocking poll was measured dropping three presses in four.
    """

    # Consecutive read failures before the button is declared dead. One-off
    # errors are transient and must not cost the rest of the session.
    _MAX_READ_FAILURES = 20

    def __init__(
        self,
        on_live: Callable[[], None],
        on_muted: Callable[[], None],
        vid: int = config.HANDSET_VID,
        pid: int = config.HANDSET_PID,
        report_id: int = config.HANDSET_REPORT_ID,
    ):
        self._on_live = on_live
        self._on_muted = on_muted
        self._report_id = report_id
        self._stop = threading.Event()
        self._queue: queue.Queue = queue.Queue()
        self._device = None
        # Without this the reader thread outlives the device at interpreter
        # shutdown and reports a spurious read error.
        atexit.register(self.close)

        import hid

        # 0 is hid.enumerate's wildcard AND the id of several internal Apple HID
        # devices, so an unset id would otherwise open one of those and read
        # garbage off it. Never a valid target either way.
        if not vid or not pid:
            raise RuntimeError(f"invalid handset ids {vid:#06x}:{pid:#06x}")
        # Filter explicitly — enumerate's own matching still honours the wildcard.
        entries = [
            e for e in hid.enumerate(vid, pid)
            if e.get("vendor_id") == vid and e.get("product_id") == pid
        ]
        if not entries:
            raise RuntimeError(f"no HID device matching {vid:#06x}:{pid:#06x}")
        # Two collections share one path; a single handle receives every report.
        self._device = hid.device()
        self._device.open_path(entries[0]["path"])
        print(f"[handset] opened {self._device.get_product_string()!r}")
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        threading.Thread(target=self._dispatch_loop, daemon=True).start()

    def _read_loop(self) -> None:
        """Read reports and hand them straight to the dispatcher.

        This thread must do nothing slow. A callback can take hundreds of
        milliseconds — Speaker.stop() aborts and restarts a CoreAudio stream —
        and running one here would stall reading and drop the next press.
        """
        failures = 0
        while not self._stop.is_set():
            try:
                data = self._device.read(64, 200)
                failures = 0
            except Exception as exc:
                # A transient read error must not be fatal: returning here left
                # the button permanently dead for the rest of the session.
                if self._stop.is_set():
                    return
                failures += 1
                if failures <= 3:
                    print(f"[handset] read error ({failures}): {exc}")
                if failures >= self._MAX_READ_FAILURES:
                    print("[handset] giving up on the mute button — "
                          "keyboard and UI controls still work")
                    return
                time.sleep(0.1)
                continue
            if not data or len(data) < 2 or data[0] != self._report_id:
                continue
            self._queue.put(bool(data[1] & 0x01))

    def _dispatch_loop(self) -> None:
        while True:
            live = self._queue.get()
            if live is None:
                return
            try:
                (self._on_live if live else self._on_muted)()
            except Exception as exc:
                print(f"[handset] callback failed: {exc}")

    def close(self) -> None:
        self._stop.set()
        self._queue.put(None)
        if self._device is not None:
            try:
                self._device.close()
            except Exception:
                pass


def attach(core, poll_interval: float = 1.0) -> Optional[TalkController]:
    """Wire a SessionCore up to the mute button, for both the kiosk and the UI.

    Best-effort by design: if the mic is absent, hidapi is missing, or the open
    fails, log and return None so SPACE and the Gradio button keep working. The
    handset is an extra way in, never a dependency.
    """
    if not config.HANDSET_ENABLED:
        print("[handset] disabled by config")
        return None

    def run_turn():
        def drain():
            had_speech = True
            for event in core.stream_finish_and_reply():
                if event.error in ("no speech", "too short"):
                    had_speech = False
            controller.on_turn_finished(had_speech)
        threading.Thread(target=drain, daemon=True).start()

    controller = TalkController(core, run_turn)

    try:
        handset = Handset(controller.on_mic_live, controller.on_mic_muted)
    except Exception as exc:
        print(f"[handset] unavailable ({exc}) — keyboard and UI controls still work")
        return None

    core.on_greeting_finished = controller.on_greeting_finished
    # The mic reports state only on change, so seed from the audio path: a
    # hardware-muted mic sends exact zeros.
    recorder = getattr(core, "recorder", None)
    if recorder is not None:
        controller.set_initial_mic_state(recorder.mic_live)

    def ticker():
        while True:
            time.sleep(poll_interval)
            try:
                controller.tick()
            except Exception as exc:
                print(f"[handset] tick failed: {exc}")

    threading.Thread(target=ticker, daemon=True).start()
    controller.handset = handset
    print("[handset] ready — unmute the mic to start a session")
    return controller
