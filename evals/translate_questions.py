"""Drafts the multilingual question set evals/multilingual_retrieval.py scores
against: a spread of the English question bank, machine-translated by the local
LLM into every language XTTS-v2 can voice. Machine translations are good enough
to compare embedders against each other; they are not a substitute for a native
speaker's phrasing, so absolute numbers should be read with that in mind.

    python evals/translate_questions.py            # writes evals/questions_multilingual.json
"""

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from joulie import config  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "questions_multilingual.json"
MODEL = "qwen3:30b-a3b-instruct-2507-q4_K_M"
LANGUAGES = {
    "zh": "Simplified Chinese", "hi": "Hindi (Devanagari script)",
    "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
    "pt": "Portuguese", "nl": "Dutch", "pl": "Polish", "ru": "Russian",
    "cs": "Czech", "hu": "Hungarian", "tr": "Turkish",
}
SAMPLE = 24


def load_questions() -> list[dict]:
    questions = []
    for name in ("questions_1_5.json", "questions_6_12.json"):
        questions += json.loads((HERE / name).read_text())
    step = len(questions) / SAMPLE
    return [questions[int(i * step)] for i in range(SAMPLE)]


def translate(question: str) -> dict[str, str]:
    prompt = (
        "Translate this question, asked aloud by a visitor at a New Zealand "
        "energy advice kiosk, into each language below. Phrase it the way a "
        "native speaker would naturally say it. Keep proper names (EECA, Billy, "
        "Rewiring Aotearoa, NIWA, Warmer Kiwi Homes) as they are. Return only a "
        "JSON object mapping each language code to its translation.\n\n"
        + "\n".join(f"{code}: {name}" for code, name in LANGUAGES.items())
        + f"\n\nQuestion: {question}"
    )
    resp = requests.post(
        f"{config.OLLAMA_URL}/api/chat",
        json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
              "stream": False, "format": "json", "options": {"temperature": 0}},
        timeout=600,
    )
    resp.raise_for_status()
    out = json.loads(resp.json()["message"]["content"])
    missing = set(LANGUAGES) - set(out)
    if missing:
        raise ValueError(f"missing {sorted(missing)}")
    return {code: out[code].strip() for code in LANGUAGES}


def main():
    done = {q["id"]: q for q in json.loads(OUT.read_text())} if OUT.exists() else {}
    for q in load_questions():
        if q["id"] in done:
            continue
        for attempt in range(3):
            try:
                done[q["id"]] = {"id": q["id"], "topic": q["topic"],
                                 "en": q["question"], **translate(q["question"])}
                break
            except (ValueError, json.JSONDecodeError, requests.RequestException) as exc:
                print(f"[eval] {q['id']} attempt {attempt + 1}: {exc}")
        print(f"[eval] {q['id']}: {done.get(q['id'], {}).get('zh', 'FAILED')}")
        OUT.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1))
    print(f"[eval] {len(done)} questions -> {OUT}")


if __name__ == "__main__":
    main()
