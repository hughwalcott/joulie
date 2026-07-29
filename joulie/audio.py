import queue
import re
import threading
import time
import wave
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from TTS.api import TTS

from joulie import config
from joulie.quiet import allow_xtts_checkpoint_unpickling, silenced_stdout
from joulie.sentences import Chunk, split_speakable

allow_xtts_checkpoint_unpickling()


# URL and markdown noise the LLM sometimes emits — we scrub these before TTS
# so Joulie doesn't read out "https colon slash slash …" or "asterisk asterisk".
_URL_RE = re.compile(
    r"https?://\S+"                                              # http:// https://
    r"|(?:www\.)[\w./-]+"                                        # www.foo.bar/baz
    r"|\b[\w-]+\.(?:govt\.nz|co\.nz|org\.nz|nz|com|org|net)(?:/\S*)?",  # foo.govt.nz/…
    re.IGNORECASE,
)
# Parens are stripped too: a scrubbed markdown link "[Billy](https://…)" would
# otherwise leave "Billy()" for XTTS to trip over, and spoken text never wants
# a parenthetical pause anyway.
_MARKDOWN_CHARS = str.maketrans("", "", "*_`~#[]<>()")
_WS_RE = re.compile(r"\s+")
# Punctuation left stranded once a URL is removed: "Visit ." / "see , and".
_ORPHAN_PUNCT_RE = re.compile(r"\s+([.,;:!?])")
_ALNUM_RE = re.compile(r"\w")

# XTTS lowercases its input before synthesis, so acronyms arrive as pronounceable
# words ("EECA" → "eeca") unless we respell them as spaced letters. Its number
# cleaner expands the digits but leaves units alone ("6.5 kW" → "six point five
# kw"), so units are spelled out here too. Order matters — kWh before kW.
_SPOKEN_FORMS = tuple(
    (re.compile(rf"\b{pattern}\b"), replacement)
    for pattern, replacement in (
        ("kWh", "kilowatt hours"),
        ("MWh", "megawatt hours"),
        ("kW", "kilowatts"),
        ("EECA", "E E C A"),
        ("MBIE", "M B I E"),
        ("ICP", "I C P"),
        ("QR", "Q R"),
        ("EV", "E V"),
        ("PV", "P V"),
        ("LED", "L E D"),
        ("EA", "E A"),
        ("NZ", "New Zealand"),
    )
)


def sanitize_for_speech(text: str) -> str:
    """Strip URLs and markdown decoration from a chunk before it reaches TTS and
    respell acronyms and units that XTTS would otherwise mangle. UI display keeps
    the original text; only the spoken stream is scrubbed.

    Returns "" for anything with no pronounceable content — a chunk that was just
    a URL scrubs down to "." and XTTS answers a lone full stop with babble.
    """
    text = _URL_RE.sub("", text)
    text = text.translate(_MARKDOWN_CHARS)
    for pattern, replacement in _SPOKEN_FORMS:
        text = pattern.sub(replacement, text)
    text = _ORPHAN_PUNCT_RE.sub(r"\1", text)
    text = _WS_RE.sub(" ", text).strip()
    if not _ALNUM_RE.search(text):
        return ""
    return text

_DEVICE_RATE = int(sd.query_devices(kind="output")["default_samplerate"])

# Silence inserted after each synthesised chunk. Sentences get the same ~120ms
# the pre-rendered greeting uses; a mid-sentence clause split gets less, so the
# latency-driven first-chunk break doesn't introduce a pause the text lacks.
_SENTENCE_GAP_S = 0.12
_CLAUSE_GAP_S = 0.05
# XTTS truncates its own tail, clipping the final consonant of every chunk.
_TAIL_PAD_S = 0.08


def _trailing_silence(boundary: str) -> np.ndarray:
    gap = _SENTENCE_GAP_S if boundary == "sentence" else _CLAUSE_GAP_S
    return np.zeros(int(_DEVICE_RATE * (_TAIL_PAD_S + gap)), dtype=np.float32)


class Recorder:
    """Long-lived microphone recorder.

    Opens ONE sd.InputStream at construction and keeps it running for the whole
    process lifetime. Recording is toggled via the _capturing flag inside the
    PortAudio callback — when True, frames are collected; when False, they're
    dropped. This entirely sidesteps macOS CoreAudio's tendency to hang on
    Pa_OpenStream / Pa_StopStream / Pa_AbortStream when a handle is opened or
    closed repeatedly. The mic indicator stays lit for the whole session, which
    is the expected kiosk behaviour anyway.
    """

    def __init__(self, sample_rate: int = config.SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._capturing = False
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        print(f"[mic] opening persistent InputStream @ {sample_rate}Hz")
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()
        print("[mic] InputStream ready (stays open for the process lifetime)")

    def _callback(self, indata, frames, time, status):
        if status:
            print(f"[mic] {status}")
        if not self._capturing:
            return
        # Copy — the buffer sd hands us is reused after the callback returns.
        chunk = indata.copy()
        with self._lock:
            self._frames.append(chunk)

    def start(self):
        with self._lock:
            self._frames = []
            self._capturing = True

    def stop(self) -> np.ndarray:
        with self._lock:
            self._capturing = False
            frames = self._frames
            self._frames = []
        if not frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(frames, axis=0).flatten()


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
            # Without the padding the VAD clips the leading word of an utterance
            # ("Hi, I'm Joulie" transcribed as "I'm Joulie"), which changes the
            # question the LLM is asked.
            vad_parameters={"speech_pad_ms": 400},
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
        self._interrupt = threading.Event()
        ref_wav = Path(config.XTTS_REF_WAV)
        if ref_wav.exists():
            import torch
            _mps = torch.backends.mps.is_available()
            _device = "mps" if _mps else "cpu"
            print(f"[tts] loading XTTS-v2 (device: {_device})...")
            with silenced_stdout():
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
            with silenced_stdout():
                self.tts = TTS(model_name)
            self._voice = voice
            self._mode = "vits"
            synth = getattr(self.tts, "synthesizer", None)
            tts_model = getattr(synth, "tts_model", None) if synth else None
            if tts_model is not None and speed > 0:
                tts_model.length_scale = 1.0 / speed

        # One persistent OutputStream for the process lifetime, for the same
        # macOS CoreAudio reasons documented on Recorder — and because opening a
        # stream per turn cost 100-500ms and swallowed the first frames of audio,
        # clipping the onset of Joulie's first word.
        print(f"[tts] opening persistent OutputStream @ {_DEVICE_RATE}Hz")
        self._out = sd.OutputStream(
            samplerate=_DEVICE_RATE,
            channels=1,
            dtype="float32",
        )
        self._out.start()
        print("[tts] OutputStream ready (stays open for the process lifetime)")

    def _synth_sentence(self, sentence: str) -> np.ndarray:
        if self._mode == "xtts":
            # Use cached conditioning latents — avoids re-encoding ref WAV each call.
            out = self._xtts_model.inference(
                text=sentence,
                language=config.XTTS_LANGUAGE,
                gpt_cond_latent=self._gpt_cond_latent,
                speaker_embedding=self._speaker_embedding,
                speed=config.XTTS_SPEED,
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

    def _write(self, audio: np.ndarray) -> None:
        """Write to the persistent stream in slices so stop() takes effect part
        way through a chunk instead of after it."""
        data = np.ascontiguousarray(audio, dtype=np.float32)
        block = _DEVICE_RATE // 4
        for i in range(0, len(data), block):
            if self._interrupt.is_set():
                return
            try:
                self._out.write(data[i:i + block])
            except Exception as exc:
                # stop() aborts the stream underneath an in-flight write, so
                # PortAudio raising here is the expected path, not a fault.
                if not self._interrupt.is_set():
                    print(f"[tts] write failed: {exc}")
                return

    def stop(self) -> None:
        """Barge-in: abandon whatever is playing. Safe to call from any thread —
        in-flight say/say_stream calls see the flag and unwind."""
        self._interrupt.set()
        try:
            self._out.abort()
            self._out.start()
        except Exception as exc:
            print(f"[tts] stop failed: {exc}")

    def say(self, text: str) -> None:
        if not text.strip():
            return
        self._interrupt.clear()
        self._write(self._synth_sentence(text))

    def say_stream(self, token_iter: Iterator[str]) -> None:
        print("[tts] streaming pipeline starting")
        self._interrupt.clear()
        t0 = time.monotonic()
        chunk_q: queue.Queue = queue.Queue(maxsize=8)
        audio_q: queue.Queue = queue.Queue(maxsize=4)

        def accumulate():
            remainder = ""
            count = 0
            for token in token_iter:
                if self._interrupt.is_set():
                    break
                remainder += token
                chunks, remainder = split_speakable(remainder, spoken=count)
                for c in chunks:
                    spoken = sanitize_for_speech(c.text)
                    if not spoken:
                        continue
                    count += 1
                    if count == 1:
                        print(f"[tts] +{time.monotonic() - t0:.2f}s first chunk queued")
                    print(f"[tts] chunk {count} [{c.boundary}]: {spoken[:60]}{'...' if len(spoken) > 60 else ''}")
                    chunk_q.put(Chunk(spoken, c.boundary))
            tail = sanitize_for_speech(remainder)
            if tail and not self._interrupt.is_set():
                count += 1
                print(f"[tts] chunk {count} (trailing): {tail[:60]}")
                chunk_q.put(Chunk(tail, "sentence"))
            print(f"[tts] accumulate done ({count} chunks)")
            chunk_q.put(_SENT_DONE)

        def synthesise():
            n = 0
            while True:
                item = chunk_q.get()
                if item is _SENT_DONE:
                    break
                if self._interrupt.is_set():
                    continue  # drain so accumulate() never blocks on a full queue
                n += 1
                try:
                    started = time.monotonic()
                    audio = self._synth_sentence(item.text)
                    synth_s = time.monotonic() - started
                    audio_s = max(audio.size / _DEVICE_RATE, 1e-6)
                    print(f"[tts] synth {n}: {synth_s:.2f}s -> {audio_s:.2f}s audio (RTF {synth_s / audio_s:.2f})")
                    audio_q.put(np.concatenate([audio, _trailing_silence(item.boundary)]))
                except Exception as exc:
                    print(f"[tts] synthesis error: {exc}")
            audio_q.put(_AUDIO_DONE)

        def play():
            n = 0
            while True:
                try:
                    item = audio_q.get_nowait()
                except queue.Empty:
                    # Synthesis is behind playback. Time the wait — this is the
                    # signature of a mid-answer stall, so it gets logged rather
                    # than silently producing dead air.
                    waited = time.monotonic()
                    item = audio_q.get()
                    starved = time.monotonic() - waited
                    if (n and starved > 0.05 and item is not _AUDIO_DONE
                            and not self._interrupt.is_set()):
                        print(f"[tts] STARVED {starved:.2f}s after chunk {n} — audible gap")
                if item is _AUDIO_DONE:
                    break
                if self._interrupt.is_set():
                    continue
                n += 1
                if n == 1:
                    print(f"[tts] +{time.monotonic() - t0:.2f}s FIRST AUDIO to device")
                self._write(item)
            print(f"[tts] playback done ({time.monotonic() - t0:.2f}s total)")

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
        self._interrupt.clear()
        self._write(self._resample(data, rate))
