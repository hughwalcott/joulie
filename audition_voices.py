"""Interactive Coqui VCTK voice tester.

Loads the TTS model once, then lets you audition speakers, speeds, and
arbitrary text without paying the ~30s load cost each time.

Usage:
    source .venv/bin/activate
    python audition_voices.py

At the prompt:
    <enter>                  replay last sample
    p273                     switch speaker, replay
    p273 1.2                 switch speaker and speed, replay
    : some text to speak     speak custom text with current voice/speed
    list                     show curated shortlist
    quit                     exit
"""
import subprocess
import tempfile

from TTS.api import TTS

# Curated shortlist — warmer/livelier than the default p225. VCTK has no NZ
# accent, so these are stand-ins until we move to XTTS-v2 voice cloning.
SHORTLIST = [
    "p273",  # warm female, brighter delivery
    "p236",  # mid female, energetic
    "p267",  # female, lower & steady
    "p306",  # female, expressive
    "p287",  # male, warm
    "p326",  # male, lively
    "p347",  # male, deeper Kiwi-ish cadence
]

DEFAULT_TEXT = (
    "Kia ora, I'm Joulie. Let's chat about electrifying your home — "
    "heat pumps, electric vehicles, solar, the lot. Ask me anything."
)


def speak(tts, text, voice, speed):
    tts.synthesizer.tts_model.length_scale = 1.0 / speed
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    tts.tts_to_file(text=text, speaker=voice, file_path=path)
    subprocess.run(["afplay", path], check=False)


def main():
    print("[tts] loading Coqui VCTK (one-time ~30s)...")
    tts = TTS("tts_models/en/vctk/vits")
    print("[tts] ready\n")

    voice = "p273"
    speed = 1.2
    text = DEFAULT_TEXT

    print(f"shortlist: {' '.join(SHORTLIST)}")
    print(f"current: voice={voice} speed={speed}\n")
    speak(tts, text, voice, speed)

    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if line in ("quit", "exit", "q"):
            break
        if line == "list":
            print(" ".join(SHORTLIST))
            continue
        if line.startswith(":"):
            text = line[1:].strip() or DEFAULT_TEXT
            speak(tts, text, voice, speed)
            continue
        if not line:
            speak(tts, text, voice, speed)
            continue

        parts = line.split()
        voice = parts[0]
        if len(parts) > 1:
            try:
                speed = float(parts[1])
            except ValueError:
                print(f"bad speed: {parts[1]}")
                continue
        print(f"voice={voice} speed={speed}")
        try:
            speak(tts, text, voice, speed)
        except Exception as exc:
            print(f"error: {exc}")


if __name__ == "__main__":
    main()
