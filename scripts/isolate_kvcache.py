"""Diagnostic: does Joulie's history cap itself cause the turn-5 TTFT cliff?

Runs the same synthetic 8-turn conversation twice against /api/chat with no
Whisper, XTTS or ChromaDB in the process — once with the production history
cap (trim-before-append, config.LLM_MAX_HISTORY_TURNS) and once with the cap
disabled (unbounded, append-only history).

The discriminator is Ollama's own `prompt_eval_count` on the final streamed
chunk: it reports how many prompt tokens llama.cpp actually had to evaluate.
When consecutive requests share a prefix, the KV cache is reused and that
number collapses to just the new tokens; when the prefix changes, it equals
the whole prompt. Latency alone can't tell those apart — this can.

Usage:
    source .venv/bin/activate
    python scripts/isolate_kvcache.py
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
]

# Sized to match rag_context_chars in real sessions (~2.1-2.5k per turn).
_FILLER = (
    "New Zealand households considering electrification should weigh solar, "
    "battery storage, and heat pump upgrades against their own usage patterns. "
)


def _context_block(turn: int, target: int = 2300) -> str:
    # Turn-specific opener so each turn's context message is distinct, as a real
    # retrieval would be — identical blocks would hand llama.cpp a prefix match
    # it would never get in production.
    head = f"[retrieved set {turn}] "
    reps = (target - len(head)) // len(_FILLER) + 1
    return head + (_FILLER * reps)[: target - len(head)]


def run_arm(label: str, max_history_turns: int, turns: int, model: str, url: str) -> list[dict]:
    print(f"\n=== arm: {label} (max_history_turns={max_history_turns}) ===")
    history: list[list[dict]] = []
    results = []

    for i in range(turns):
        question = _QUESTIONS[i % len(_QUESTIONS)]

        # Identical trim-before-append shape to Agent._build_messages.
        if max_history_turns > 0 and len(history) > max_history_turns:
            history = history[-max_history_turns:]

        current_turn = [
            {"role": "system", "content": _context_block(i + 1)},
            {"role": "user", "content": question},
        ]
        history.append(current_turn)
        messages = [{"role": "system", "content": config.SYSTEM_PROMPT}] + [
            m for turn in history for m in turn
        ]
        prompt_chars = sum(len(m["content"]) for m in messages)

        t0 = time.monotonic()
        resp = requests.post(
            f"{url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {"num_predict": 100},
            },
            timeout=300,
            stream=True,
        )
        resp.raise_for_status()
        ttft = None
        parts: list[str] = []
        final: dict = {}
        for raw in resp.iter_lines():
            if not raw:
                continue
            data = json.loads(raw)
            tok = data.get("message", {}).get("content", "")
            if tok:
                if ttft is None:
                    ttft = time.monotonic() - t0
                parts.append(tok)
            if data.get("done"):
                final = data
                break
        reply = "".join(parts).strip()
        current_turn.append({"role": "assistant", "content": reply})

        pec = final.get("prompt_eval_count")
        ped = final.get("prompt_eval_duration", 0) / 1e9
        row = {
            "turn": i + 1,
            "history_turns": len(history),
            "prompt_chars": prompt_chars,
            "ttft_s": round(ttft or 0, 3),
            "prompt_eval_count": pec,
            "prompt_eval_s": round(ped, 3),
        }
        results.append(row)
        print(
            f"  turn {row['turn']:>2}  hist={row['history_turns']}  "
            f"prompt={prompt_chars:>6}ch  ttft={row['ttft_s']:>6.2f}s  "
            f"prompt_eval={pec} tok in {ped:>5.2f}s"
        )
    return results


def main():
    model = config.OLLAMA_MODEL
    url = config.OLLAMA_URL.rstrip("/")
    turns = 8
    print(f"[isolate-kv] model={model} url={url} turns={turns}")
    # Warm the model so arm A's turn 1 isn't paying a cold load the other arm won't.
    requests.post(
        f"{url}/api/chat",
        json={"model": model, "messages": [{"role": "user", "content": "ok"}],
              "stream": False, "options": {"num_predict": 1}},
        timeout=300,
    ).raise_for_status()

    # Capped arm runs FIRST deliberately: if the uncapped arm is still faster
    # from second position, with strictly larger prompts, no ordering or
    # machine-drift effect can account for it.
    capped = run_arm("history cap (production)", config.LLM_MAX_HISTORY_TURNS, turns, model, url)
    uncapped = run_arm("no cap (append-only)", 0, turns, model, url)

    out = Path("logs") / f"isolate_kvcache_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"model": model, "turns": turns,
                               "capped": capped, "uncapped": uncapped}, indent=2))
    print(f"\n[isolate-kv] wrote {out}")


if __name__ == "__main__":
    main()
