"""Run the Joulie test question bank through the real RAG + LLM pipeline.

Each question gets a fresh Agent (no conversation history) so answers reflect a
cold visitor asking one question, which is how the kiosk is actually used.

    python3 evals/run_qbank.py                       # config default model
    python3 evals/run_qbank.py --model qwen2.5:14b-instruct-q4_K_M

Results land in evals/results-<model-slug>.json for grading.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from joulie import config
from joulie.llm import Agent
from joulie.rag import Retriever

EVALS = Path(__file__).parent


def load_questions() -> list[dict]:
    questions: list[dict] = []
    for name in ("questions_1_5.json", "questions_6_12.json"):
        questions.extend(json.loads((EVALS / name).read_text()))
    return questions


# Rephrasings of a sample of questions, asked in a second pass to check whether
# Joulie gives a consistent answer to the same question worded differently.
CONSISTENCY_PROBES = {
    "T1Q1": "Is a heat pump hot water cylinder actually cheaper to run than my normal electric one?",
    "T1Q4": "I heard there's a government grant for insulation and heat pumps - what is it?",
    "T2Q5": "Am I still allowed to put gas into a new house in New Zealand?",
    "T3Q4": "What do I have to pay in road user charges if I drive an EV?",
    "T4Q1": "What percentage of our power is renewable?",
    "T4Q5": "Which companies generate most of New Zealand's electricity?",
    "T5Q13": "Has the government published a national energy strategy?",
    "T6Q6": "Do I need a battery with my solar panels?",
    "T11Q3": "Is a proper wall charger much quicker than a normal plug for an EV?",
    "T12Q1": "What's a smart meter?",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=config.OLLAMA_MODEL)
    parser.add_argument("--out", default=None)
    # Qwen3 is a hybrid reasoning model and emits <think> blocks by default, which
    # blow past the kiosk's two-to-four sentence spoken format. /no_think is Qwen's
    # own in-prompt switch, so this needs no change to joulie/llm.py.
    parser.add_argument("--no-think", action="store_true")
    args = parser.parse_args()

    model = args.model
    system_prompt = config.SYSTEM_PROMPT + ("\n\n/no_think" if args.no_think else "")
    slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
    out_path = Path(args.out) if args.out else EVALS / f"results-{slug}.json"

    questions = load_questions()
    print(f"[eval] {len(questions)} questions loaded")
    print(f"[eval] model={model} rag_enabled={config.RAG_ENABLED} top_k={config.RAG_TOP_K}")
    print(f"[eval] writing to {out_path}")

    retriever = Retriever() if config.RAG_ENABLED and Retriever.available() else None
    if retriever is None:
        print("[eval] WARNING: no retriever - answers will be model-only")

    warm = Agent(model=model, system_prompt=system_prompt, retriever=retriever).warmup()
    print(f"[eval] model warm ({warm:.1f}s)")

    results: list[dict] = []
    total = len(questions) + len(CONSISTENCY_PROBES)
    done = 0

    for q in questions:
        agent = Agent(model=model, system_prompt=system_prompt, retriever=retriever)
        chunks = retriever.retrieve(q["question"]) if retriever else []
        start = time.monotonic()
        try:
            answer = agent.reply(q["question"])
            error = None
        except Exception as exc:
            answer, error = "", repr(exc)
        elapsed = time.monotonic() - start
        done += 1
        results.append({
            **q,
            "answer": answer,
            "error": error,
            "seconds": round(elapsed, 1),
            "retrieved": [
                {
                    "publisher": c["publisher_short"],
                    "title": c["title"],
                    "stance": c["stance"],
                    "distance": round(c["distance"], 3),
                }
                for c in chunks
            ],
        })
        print(f"[eval] {done}/{total} {q['id']} ({elapsed:.1f}s, {len(chunks)} chunks)")
        out_path.write_text(json.dumps(results, indent=1))

    for qid, rephrased in CONSISTENCY_PROBES.items():
        agent = Agent(model=model, system_prompt=system_prompt, retriever=retriever)
        chunks = retriever.retrieve(rephrased) if retriever else []
        start = time.monotonic()
        try:
            answer = agent.reply(rephrased)
            error = None
        except Exception as exc:
            answer, error = "", repr(exc)
        elapsed = time.monotonic() - start
        done += 1
        results.append({
            "id": f"{qid}-rephrased",
            "topic": "consistency probe",
            "verifier": False,
            "question": rephrased,
            "expected": f"Should be consistent with {qid}",
            "answer": answer,
            "error": error,
            "seconds": round(elapsed, 1),
            "retrieved": [
                {
                    "publisher": c["publisher_short"],
                    "title": c["title"],
                    "stance": c["stance"],
                    "distance": round(c["distance"], 3),
                }
                for c in chunks
            ],
        })
        print(f"[eval] {done}/{total} {qid}-rephrased ({elapsed:.1f}s, {len(chunks)} chunks)")
        out_path.write_text(json.dumps(results, indent=1))

    print(f"[eval] complete -> {out_path}")


if __name__ == "__main__":
    main()
