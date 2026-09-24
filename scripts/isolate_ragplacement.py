"""Diagnostic: where does the per-turn RAG block belong in the request?

Ollama collates every role=system message into one block at the TOP of the
rendered prompt, so a per-turn context message sent as a system message is
inserted in front of the whole conversation and shifts every history token
behind it. The KV prefix then breaks on every turn, trim or no trim.

Three arms over the same 12-turn conversation, against /api/chat with no
Whisper, XTTS or ChromaDB in the process:

    A  system   — context as a system message, kept in history (the old shape)
    B  user     — context on the user message, kept in history
    C  question — context on the user message, dropped from history afterwards
                  (the shipped default, config.LLM_RAG_PLACEMENT)

A vs B isolates the hoisting; B vs C isolates carrying spent context forward.
Read prompt_eval_duration, never prompt_eval_count / duration: the count is the
whole prompt while the duration covers only the tokens that missed the cache,
so their ratio rises as the cache helps more. This model prefills at ~185 tok/s
when nothing is cached.

Usage:
    python3 scripts/isolate_ragplacement.py
"""

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from joulie import config

_QUESTIONS = [
    "What's the payback period on rooftop solar for a typical Auckland home?",
    "How does a heat pump hot water cylinder compare to a standard electric one?",
    "Is it worth switching from LPG to induction cooking?",
    "What rebates exist for EV chargers in New Zealand right now?",
    "How much does insulation retrofitting typically save on power bills?",
    "Should I get a home battery if I already have solar panels?",
    "What's the difference between a hybrid and a fully electric heat pump?",
    "How do time-of-use electricity plans work for EV owners?",
    "Can I get a Warmer Kiwi Homes grant for a heat pump?",
    "How do I find my ICP number?",
    "Are induction cooktops safe with pacemakers?",
    "What size solar system suits a four person household in Wellington?",
]

_WORDS = (
    "solar battery heat pump insulation tariff lines company retailer EECA grant "
    "kilowatt hour export rate winter peak hot water cylinder induction EV charger "
).split()


def _context_block(turn: int, target: int = 2300) -> str:
    """Sized and varied to match live `rag_context_chars` (2.0-2.5k, distinct
    every turn). Identical blocks would hand llama.cpp a prefix match retrieval
    would never produce in production."""
    parts, i = [f"[retrieved set {turn}]"], turn * 7
    while sum(len(w) + 1 for w in parts) < target:
        parts.append(_WORDS[i % len(_WORDS)] + ("." if i % 11 == 0 else ""))
        i += turn + 3
    return " ".join(parts)[:target]


def _wrap(context: str) -> str:
    return (
        "Relevant reference material from the New Zealand electrification knowledge base.\n\n"
        f"{context}\n\nUse this material to inform your answer. Do not invent numbers."
    )


def run_arm(arm: str, turns: int, model: str, url: str) -> list[dict]:
    print(f"\n=== arm: {arm} ===")
    history: list[list[dict]] = []
    results: list[dict] = []

    for i in range(turns):
        trimmed = False
        if arm in ("system", "user") and len(history) > config.LLM_MAX_HISTORY_TURNS:
            history, trimmed = history[-config.LLM_HISTORY_TRIM_TO:], True

        question, context = _QUESTIONS[i % len(_QUESTIONS)], _wrap(_context_block(i + 1))
        if arm == "system":
            current_turn = [{"role": "system", "content": context},
                            {"role": "user", "content": question}]
        elif arm == "user":
            current_turn = [{"role": "user", "content": f"{context}\n\nQuestion: {question}"}]
        else:
            current_turn = [{"role": "user", "content": question}]
        history.append(current_turn)

        messages = [{"role": "system", "content": config.SYSTEM_PROMPT}] + [
            m for turn in history for m in turn
        ]
        if arm == "question":
            messages[-1] = {"role": "user", "content": f"{context}\n\nQuestion: {question}"}

        start = time.monotonic()
        resp = requests.post(
            f"{url}/api/chat",
            json={"model": model, "messages": messages, "stream": True,
                  "options": {"num_ctx": config.LLM_NUM_CTX, "num_predict": 90}},
            timeout=300,
            stream=True,
        )
        resp.raise_for_status()
        ttft, parts, final = None, [], {}
        for raw in resp.iter_lines():
            if not raw:
                continue
            data = json.loads(raw)
            token = data.get("message", {}).get("content", "")
            if token and ttft is None:
                ttft = time.monotonic() - start
            parts.append(token)
            if data.get("done"):
                final = data
                break
        current_turn.append({"role": "assistant", "content": "".join(parts).strip()})

        row = {
            "arm": arm,
            "turn": i + 1,
            "history_turns": len(history),
            "trimmed": trimmed,
            "prompt_eval_count": final.get("prompt_eval_count"),
            "prompt_eval_seconds": round(final.get("prompt_eval_duration", 0) / 1e9, 2),
            "ttft_seconds": round(ttft or 0, 2),
        }
        results.append(row)
        print(f"  turn {row['turn']:>2}  hist={row['history_turns']}  "
              f"prompt={row['prompt_eval_count']:>5} tok  "
              f"prefill={row['prompt_eval_seconds']:>6.2f}s  ttft={row['ttft_seconds']:>6.2f}s"
              f"{'  TRIMMED' if trimmed else ''}")
    return results


def main() -> None:
    model, url = config.OLLAMA_MODEL, config.OLLAMA_URL.rstrip("/")
    turns = 12
    print(f"[isolate-rag] model={model} url={url} turns={turns}")
    requests.post(
        f"{url}/api/chat",
        json={"model": model, "messages": [{"role": "user", "content": "ok"}], "stream": False,
              "options": {"num_ctx": config.LLM_NUM_CTX, "num_predict": 1}},
        timeout=300,
    ).raise_for_status()

    runs = {arm: run_arm(arm, turns, model, url) for arm in ("system", "user", "question")}

    print(f"\n{'arm':>10}{'mean prefill':>16}{'worst turn':>14}{'prompt at t12':>16}")
    for arm, rows in runs.items():
        later = [r["prompt_eval_seconds"] for r in rows[1:]]
        print(f"{arm:>10}{sum(later) / len(later):>15.2f}s{max(later):>13.2f}s"
              f"{rows[-1]['prompt_eval_count']:>16}")

    out = Path("logs") / f"isolate_ragplacement_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"model": model, "turns": turns, "runs": runs}, indent=2))
    print(f"\n[isolate-rag] wrote {out}")


if __name__ == "__main__":
    main()
