"""Diagnostic: does answer length grow with conversation history?

evals/run_qbank.py gives every question a fresh Agent, so it measures a cold
one-shot answer — 60 words mean on this corpus. The live kiosk session
20260916T225408 averaged 136 generated tokens and reached 230, which is 40s of
synthesised speech per turn, a quarter of it cut off by the visitor. Those two
numbers disagree, and the difference is conversation history: the eval never
carries any.

This walks ONE Agent through a multi-turn visit, the way a real visitor does,
and records how long each answer runs. Compare arms to judge a SYSTEM_PROMPT
brevity change against the thing it is meant to fix, rather than against the
single-turn eval that cannot see it.

    python3 scripts/isolate_answerlength.py
    python3 scripts/isolate_answerlength.py --brief   # tightened prompt
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from joulie import config
from joulie.llm import Agent
from joulie.rag import Retriever

# A plausible kiosk visit: an opening question, then follow-ups that lean on
# what was already said, which is what makes the prompt grow.
_VISIT = [
    "How much cheaper is a hot water heat pump to run than a standard cylinder?",
    "What does one cost to install?",
    "Is there a grant for that?",
    "Am I eligible if I rent?",
    "What about solar - is it worth it in Auckland?",
    "How long until it pays for itself?",
    "Should I add a battery?",
    "What if I get an EV as well?",
    "How much would charging it add to my bill?",
    "Is there a cheaper plan for that?",
    "Who do I talk to about switching?",
    "What should I ask them?",
]

# ~2.45 spoken words per second, measured from session 20260916T225408.
_WORDS_PER_SECOND = 2.45

_BRIEF = (
    "\n\nKeep spoken answers to TWO or THREE sentences and under 120 words. "
    "Stop once the question is answered; do not add caveats the visitor did not ask for."
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", action="store_true",
                        help="Append the tightened brevity instruction to SYSTEM_PROMPT.")
    parser.add_argument("--turns", type=int, default=len(_VISIT))
    args = parser.parse_args()

    system_prompt = config.SYSTEM_PROMPT + (_BRIEF if args.brief else "")
    arm = "brief" if args.brief else "baseline"
    print(f"[answerlength] arm={arm} model={config.OLLAMA_MODEL} turns={args.turns}", flush=True)

    agent = Agent(system_prompt=system_prompt, retriever=Retriever())
    print(f"[answerlength] warm ({agent.warmup():.1f}s)", flush=True)

    rows = []
    for i in range(args.turns):
        question = _VISIT[i % len(_VISIT)]
        start = time.monotonic()
        answer = agent.reply(question)
        elapsed = time.monotonic() - start
        ev = agent.last_eval_stats
        st = agent.last_prompt_stats
        words = len(answer.split())
        row = {
            "turn": i + 1,
            "question": question,
            "words": words,
            "gen_tokens": ev.get("eval_count", 0),
            "speech_seconds": round(words / _WORDS_PER_SECOND, 1),
            "prompt_eval_count": ev.get("prompt_eval_count", 0),
            "prompt_eval_seconds": round(ev.get("prompt_eval_seconds", 0.0), 2),
            "history_turns": st.get("history_turns", 0),
            "seconds": round(elapsed, 1),
        }
        rows.append(row)
        print(f"  turn {row['turn']:>2}  hist={row['history_turns']:>2}  "
              f"{row['gen_tokens']:>3} tok / {row['words']:>3} words  "
              f"-> {row['speech_seconds']:>5.1f}s of speech  "
              f"(prompt {row['prompt_eval_count']:>4} tok, prefill {row['prompt_eval_seconds']:>5.2f}s)",
              flush=True)

    tokens = [r["gen_tokens"] for r in rows]
    speech = [r["speech_seconds"] for r in rows]
    print(f"\n  generated tokens: mean {sum(tokens)/len(tokens):.0f}  max {max(tokens)}")
    print(f"  speech per turn : mean {sum(speech)/len(speech):.1f}s  max {max(speech):.1f}s")
    print(f"  first 3 turns   : {sum(tokens[:3])/3:.0f} tok   "
          f"last 3 turns: {sum(tokens[-3:])/3:.0f} tok", flush=True)

    out = Path("logs") / f"isolate_answerlength_{arm}_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"arm": arm, "model": config.OLLAMA_MODEL, "rows": rows}, indent=2))
    print(f"\n[answerlength] wrote {out}", flush=True)


if __name__ == "__main__":
    main()
