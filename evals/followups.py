"""Multi-turn probe: does a follow-up still land when the RAG context is
dropped from history after its own turn?

run_qbank.py gives every question a fresh Agent, so it cannot see this. It is
the one thing JOULIE_LLM_RAG_PLACEMENT=question trades away: a follow-up sees
the previous answers but no longer the chunks that produced them, and an
anaphoric follow-up ("what does one cost to install?") retrieves poorly on its
own text. Each conversation below opens with a question the knowledge base
answers well, then leans on it.

    python3 evals/followups.py                    # both placements, A/B
    python3 evals/followups.py --placement question
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from joulie import config
from joulie.llm import Agent
from joulie.rag import Retriever

EVALS = Path(__file__).parent

CONVERSATIONS = [
    ["How much cheaper is a hot water heat pump to run than a standard electric cylinder?",
     "What does one cost to install?",
     "Is there a grant that helps with that?"],
    ["What's the payback period on rooftop solar for a typical Auckland home?",
     "Does adding a battery change that?",
     "What size system would suit a family of four?"],
    ["Am I still allowed to install gas in a new house in New Zealand?",
     "What about replacing my existing gas hob?",
     "How does induction compare on running cost?"],
    ["What percentage of New Zealand's electricity is renewable?",
     "Which companies generate most of it?",
     "Has that share changed much since 2020?"],
    ["What road user charges do I pay on an EV?",
     "How does that compare with what I'd spend on petrol?",
     "Are there rebates left for buying one?"],
    ["What's a smart meter?",
     "How do I find mine?",
     "Can it tell me my time-of-use prices?"],
]


def run(placement: str, retriever) -> list[dict]:
    print(f"\n=== placement={placement} ===")
    rows: list[dict] = []
    for c_idx, questions in enumerate(CONVERSATIONS, start=1):
        agent = Agent(retriever=retriever, rag_placement=placement)
        for t_idx, question in enumerate(questions, start=1):
            start = time.monotonic()
            answer = agent.reply(question)
            elapsed = time.monotonic() - start
            stats, ev = agent.last_prompt_stats, agent.last_eval_stats
            rows.append({
                "placement": placement,
                "conversation": c_idx,
                "turn": t_idx,
                "question": question,
                "answer": answer,
                "sources": [s.publisher for s in agent.last_sources],
                "seconds": round(elapsed, 1),
                "prompt_chars": stats.get("prompt_chars"),
                "prompt_eval_count": ev.get("prompt_eval_count"),
                "prompt_eval_seconds": round(ev.get("prompt_eval_seconds", 0), 2),
            })
            print(f"[followups] c{c_idx} t{t_idx} {elapsed:4.1f}s  "
                  f"prefill {rows[-1]['prompt_eval_seconds']:5.2f}s  {question}")
            print(f"            {answer[:160]}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--placement", choices=["question", "system", "both"], default="both")
    args = parser.parse_args()

    retriever = Retriever() if config.RAG_ENABLED and Retriever.available() else None
    if retriever is None:
        raise SystemExit("[followups] no retriever — this probe is meaningless without RAG")
    Agent(retriever=retriever).warmup()

    placements = ["question", "system"] if args.placement == "both" else [args.placement]
    rows = [r for p in placements for r in run(p, retriever)]
    out = EVALS / "followups.json"
    out.write_text(json.dumps(rows, indent=1))
    print(f"\n[followups] wrote {out}")

    if len(placements) == 2:
        print(f"\n{'':6s}{'question':>34s}{'system':>34s}")
        for c_idx, questions in enumerate(CONVERSATIONS, start=1):
            for t_idx in range(1, len(questions) + 1):
                pair = [next(r for r in rows if r["placement"] == p
                             and r["conversation"] == c_idx and r["turn"] == t_idx)
                        for p in ("question", "system")]
                print(f"c{c_idx}t{t_idx}  "
                      + "".join(f"{r['prompt_eval_seconds']:>10.2f}s prefill{r['seconds']:>12.1f}s"
                                for r in pair))


if __name__ == "__main__":
    main()
