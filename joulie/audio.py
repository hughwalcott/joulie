import queue
import threading
import wave
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from TTS.api import TTS

from joulie import config
from joulie.sentences import split_sentences

_DEVICE_RATE = int(sd.query_devices(kind="output")["default_samplerate"])


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


_SENT_DONE = object()
_AUDIO_DONE = object()


class Speaker:
    def __init__(
        self,
        model_name: str = config.TTS_MODEL,
        voice: str = config.TTS_VOICE,
        speed: float = config.TTS_SPEED,
    ):
        ref_wav = Path(config.XTTS_REF_WAV)
        if ref_wav.exists():
            import torch
            _mps = torch.backends.mps.is_available()
            _device = "mps" if _mps else "cpu"
            print(f"[tts] loading XTTS-v2 (device: {_device})...")
            self.tts = TTS(config.XTTS_MODEL)
            self._mode = "xtts"
            self._xtts_model = self.tts.synthesizer.tts_model
            if _mps:
                self._xtts_model = self._xtts_model.to("mps")
            self._xtts_sample_rate = config.XTTS_SAMPLE_RATE
            # Pre-compute speaker conditioning latents once — eliminates per-sentence
            # re-encoding of the reference WAV (the main source of 60s latency).
            print(f"[tts] computing speaker conditioning latents...")
            self._gpt_cond_latent, self._speaker_embedding = (
                self._xtts_model.get_conditioning_latents(audio_path=[str(ref_wav)])
            )
            # Warm up MPS kernel JIT — first inference is slow without this.
            print(f"[tts] warming up {_device} kernels...")
            self._xtts_model.inference(
                text="ok",
                language=config.XTTS_LANGUAGE,
                gpt_cond_latent=self._gpt_cond_latent,
                speaker_embedding=self._speaker_embedding,
            )
            print(f"[tts] XTTS-v2 ready (device: {_device}, output: {_DEVICE_RATE}Hz)")
        else:
            print(f"[tts] reference WAV not found — falling back to VITS '{model_name}'")
            self.tts = TTS(model_name)
            self._voice = voice
            self._mode = "vits"
            synth = getattr(self.tts, "synthesizer", None)
            tts_model = getattr(synth, "tts_model", None) if synth else None
            if tts_model is not None and speed > 0:
                tts_model.length_scale = 1.0 / speed

    def _synth_sentence(self, sentence: str) -> np.ndarray:
        if self._mode == "xtts":
            # Use cached conditioning latents — avoids re-encoding ref WAV each call.
            out = self._xtts_model.inference(
                text=sentence,
                language=config.XTTS_LANGUAGE,
                gpt_cond_latent=self._gpt_cond_latent,
                speaker_embedding=self._speaker_embedding,
            )
            wav = np.array(out["wav"], dtype=np.float32)
            return self._resample(wav, self._xtts_sample_rate)
        else:
            wav = self.tts.tts(text=sentence, speaker=self._voice)
            return self._resample(np.array(wav, dtype=np.float32), 22050)

    @staticmethod
    def _resample(audio: np.ndarray, src_rate: int) -> np.ndarray:
        if src_rate == _DEVICE_RATE:
            return audio
        ratio = _DEVICE_RATE / src_rate
        n_out = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, n_out)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def say(self, text: str) -> None:
        if not text.strip():
            return
        audio = self._synth_sentence(text)
        sd.play(audio, samplerate=_DEVICE_RATE)
        sd.wait()

    def say_stream(self, token_iter: Iterator[str]) -> None:
        sentence_q: queue.Queue = queue.Queue(maxsize=4)
        audio_q: queue.Queue = queue.Queue(maxsize=2)

        def accumulate():
            remainder = ""
            for token in token_iter:
                remainder += token
                sentences, remainder = split_sentences(remainder)
                for s in sentences:
                    sentence_q.put(s)
            if remainder.strip():
                sentence_q.put(remainder.strip())
            sentence_q.put(_SENT_DONE)

        def synthesise():
            while True:
                item = sentence_q.get()
                if item is _SENT_DONE:
                    break
                try:
                    audio = self._synth_sentence(item)
                    audio_q.put(audio)
                except Exception as exc:
                    print(f"[tts] synthesis error: {exc}")
            audio_q.put(_AUDIO_DONE)

        def play():
            while True:
                item = audio_q.get()
                if item is _AUDIO_DONE:
                    break
                sd.play(item, samplerate=_DEVICE_RATE)
                sd.wait()

        t_acc = threading.Thread(target=accumulate, daemon=True)
        t_syn = threading.Thread(target=synthesise, daemon=True)
        t_play = threading.Thread(target=play, daemon=True)
        t_acc.start(); t_syn.start(); t_play.start()
        t_acc.join(); t_syn.join(); t_play.join()

    def prerender_greeting(self, text: str, path: str) -> None:
        # Audio from _synth_sentence is already resampled to _DEVICE_RATE.
        audio = self._synth_sentence(text)
        pcm = (audio * 32767).astype(np.int16)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(_DEVICE_RATE)
            wf.writeframes(pcm.tobytes())
        print(f"[tts] greeting pre-rendered → {path}")

    def play_wav(self, path: str) -> None:
        with wave.open(path, "rb") as wf:
            rate = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
        sd.play(data, samplerate=rate)
        sd.wait()
