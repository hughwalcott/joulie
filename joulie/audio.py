import queue
import subprocess
import tempfile
import threading

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from TTS.api import TTS

from joulie import config


class Recorder:
    def __init__(self, sample_rate: int = config.SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._frames: list[np.ndarray] = []
        self._queue: queue.Queue = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._running = False
        self._worker: threading.Thread | None = None

    def _callback(self, indata, frames, time, status):
        if status:
            print(f"[mic] {status}")
        self._queue.put(indata.copy())

    def _drain(self):
        while self._running:
            try:
                chunk = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            self._frames.append(chunk)

    def start(self):
        self._frames = []
        self._queue = queue.Queue()
        self._running = True
        self._worker = threading.Thread(target=self._drain, daemon=True)
        self._worker.start()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._worker is not None:
            self._worker.join(timeout=1.0)
        if not self._frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self._frames, axis=0).flatten()


class Transcriber:
    def __init__(self, model_name: str = config.WHISPER_MODEL):
        print(f"[stt] loading faster-whisper '{model_name}'...")
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        if audio.size == 0:
            return "", "en"
        segments, info = self.model.transcribe(
            audio,
            beam_size=1,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, info.language


class Speaker:
    def __init__(
        self,
        model_name: str = config.TTS_MODEL,
        voice: str = config.TTS_VOICE,
        speed: float = config.TTS_SPEED,
    ):
        print(f"[tts] loading Coqui '{model_name}'...")
        self.tts = TTS(model_name)
        self.voice = voice
        self.speed = speed
        # VITS exposes length_scale on the synthesizer; lower = faster delivery.
        synth = getattr(self.tts, "synthesizer", None)
        tts_model = getattr(synth, "tts_model", None) if synth else None
        tts_cfg = getattr(tts_model, "length_scale", None) if tts_model else None
        if tts_cfg is not None and speed > 0:
            tts_model.length_scale = 1.0 / speed

    def say(self, text: str):
        if not text.strip():
            return
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            self.tts.tts_to_file(text=text, speaker=self.voice, file_path=path)
            subprocess.run(["afplay", "-r", "1.0", path], check=False)
        finally:
            try:
                import os
                os.unlink(path)
            except OSError:
                pass
