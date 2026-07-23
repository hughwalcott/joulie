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
    so the user can still pin individual env vars on top of --lite. XTTS-v2 is
    kept so the Kiwi voice still works — pair with --no-xtts for the tightest
    memory budget at the cost of voice cloning."""
    lite_defaults = {
        "JOULIE_OLLAMA_MODEL": "llama3.2:1b-instruct-q4_K_M",
        "JOULIE_RAG_TOP_K": "2",
        "JOULIE_WHISPER_MODEL": "tiny",
    }
    for key, value in lite_defaults.items():
        os.environ.setdefault(key, value)


def _apply_no_xtts():
    """Force the VITS fallback by pointing the reference WAV at a bogus path.
    Saves ~1.8GB vs XTTS-v2 but loses the Kiwi voice cloning."""
    os.environ.setdefault("JOULIE_XTTS_REF_WAV", "/__no_xtts__")


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
        help="Low-memory dev profile: 1B LLM, RAG top_k=2, tiny Whisper (keeps XTTS Kiwi voice)",
    )
    parser.add_argument(
        "--no-xtts",
        action="store_true",
        help="Force VITS fallback voice — saves ~1.8GB but drops the Kiwi voice cloning",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the Gradio web UI instead of the pynput terminal kiosk",
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
        print("[main] --lite mode: 1B LLM, RAG top_k=2, tiny Whisper")
    if args.no_xtts:
        _apply_no_xtts()
        print("[main] --no-xtts: forcing VITS fallback voice")

    # Import driver modules AFTER env vars are set — joulie.config reads them at import time.
    if args.ui:
        from joulie.ui import launch
        launch()
    else:
        from joulie.session import Kiosk
        Kiosk().run()


if __name__ == "__main__":
    main()
