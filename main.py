import argparse
import os

# Silence the huggingface tokenizers fork warning. We intentionally use threads
# alongside tokenizers; the warning is noisy and not actionable for our usage.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# Quiet transformers' own logger (the source of the GPT2InferenceModel /
# attention-mask notices) — only respected if set before transformers loads.
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

# Suppress noisy library warnings before any ML imports load.
from joulie.quiet import silence_warnings
silence_warnings()


def _apply_lite_defaults():
    """Low-memory dev profile. Each setting is set only if not already overridden,
    so the user can still pin individual env vars on top of --lite."""
    lite_defaults = {
        "JOULIE_OLLAMA_MODEL": "llama3.2:1b-instruct-q4_K_M",
        "JOULIE_RAG_TOP_K": "2",
        "JOULIE_WHISPER_MODEL": "tiny",
        # Point XTTS reference at a non-existent path so Speaker falls back to VITS
        # (~1.8GB saved vs XTTS-v2). Kiwi accent is lost in lite mode — acceptable
        # for development on memory-constrained hardware.
        "JOULIE_XTTS_REF_WAV": "/__lite_mode_no_xtts__",
    }
    for key, value in lite_defaults.items():
        os.environ.setdefault(key, value)


def _render_greeting(speed: float):
    """Render the greeting WAV from config.GREETING using XTTS-v2 at the given speed.

    Synthesises sentence-by-sentence and concatenates — single-shot inference on
    long text causes XTTS GPT decoder drift (distortion mid-utterance, garbled
    tail). Peak-normalises before int16 quantisation to avoid clipping artefacts.
    """
    import wave
    import numpy as np
    from joulie import config
    from joulie.audio import Speaker, _DEVICE_RATE
    from joulie.sentences import split_sentences

    speaker = Speaker()
    if speaker._mode != "xtts":
        raise SystemExit(
            "XTTS-v2 not loaded — check JOULIE_XTTS_REF_WAV points to an existing WAV"
        )

    sentences, remainder = split_sentences(config.GREETING)
    if remainder.strip():
        sentences.append(remainder.strip())

    # Inter-sentence silence (~120ms) so concatenation doesn't sound rushed.
    gap = np.zeros(int(_DEVICE_RATE * 0.12), dtype=np.float32)
    pieces: list[np.ndarray] = []
    for i, sentence in enumerate(sentences, start=1):
        print(f"[tts] rendering sentence {i}/{len(sentences)}: {sentence[:60]}")
        out = speaker._xtts_model.inference(
            text=sentence,
            language=config.XTTS_LANGUAGE,
            gpt_cond_latent=speaker._gpt_cond_latent,
            speaker_embedding=speaker._speaker_embedding,
            speed=speed,
        )
        wav = np.array(out["wav"], dtype=np.float32)
        wav = speaker._resample(wav, speaker._xtts_sample_rate)
        pieces.append(wav)
        if i < len(sentences):
            pieces.append(gap)
    audio = np.concatenate(pieces)

    # Peak-normalise to -1 dBFS to prevent int16 clip without compressing dynamics.
    peak = float(np.max(np.abs(audio)))
    if peak > 0:
        audio = audio * (0.89 / peak)

    pcm = (audio * 32767).astype(np.int16)
    with wave.open(config.GREETING_WAV, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_DEVICE_RATE)
        wf.writeframes(pcm.tobytes())
    print(f"[tts] greeting rendered at {speed}x ({len(sentences)} sentences) → {config.GREETING_WAV}")


def main():
    parser = argparse.ArgumentParser(description="Joulie electrification advisor kiosk")
    parser.add_argument(
        "--lite",
        action="store_true",
        help="Low-memory dev profile: smaller LLM, fewer RAG chunks, VITS fallback TTS",
    )
    parser.add_argument(
        "--render-greeting",
        action="store_true",
        help="Re-render resources/greeting.wav from config.GREETING with XTTS-v2 and exit",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speech speed for --render-greeting (default 1.0; try 1.25 for snappier)",
    )
    args = parser.parse_args()

    if args.render_greeting:
        # Ignore --lite for rendering — the greeting should always use the cloned voice.
        _render_greeting(args.speed)
        return

    if args.lite:
        _apply_lite_defaults()
        print("[main] --lite mode: 1B LLM, RAG top_k=2, tiny Whisper, VITS fallback TTS")

    # Import Kiosk AFTER env vars are set — joulie.config reads them at import time.
    from joulie.session import Kiosk
    Kiosk().run()


if __name__ == "__main__":
    main()
