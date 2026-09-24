"""Diagnostic: how much of TTFT is the per-turn RAG block?

With LLM_RAG_PLACEMENT=question the conversation prefix is append-only, so the
only tokens Ollama has to prefill each turn are the ones appended since the last
request: the previous answer, the bare previous question, and — the big one —
this turn's retrieved context block. Live sessions send ~2.3k chars of context
(RAG_TOP_K=4), which is ~540 tokens re-prefilled every single turn.

Four arms over the same 8-turn conversation, identical in every respect except
how much context rides along with the question:

    top_k=4  ~2300 chars   (the shipped default)
    top_k=3  ~1725 chars
    top_k=2  ~1150 chars
    top_k=0  no context    (floor: answer + question only)

Read prompt_eval_duration, not prompt_eval_count / duration — the count is the
whole prompt while the duration covers only the tokens that missed the cache.

Usage:
    python3 scripts/isolate_ragsize.py
"""

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from joulie import config
from scripts.isolate_ragplacement import _QUESTIONS, _context_block, _wrap

_CHARS_PER_CHUNK = 575  # live rag_context_chars / RAG_TOP_K, measured


def run_arm(top_k: int, turns: int, model: str, url: str) -> list[dict]:
    print(f"\n=== arm: top_k={top_k} ===", flush=True)
    history: list[list[dict]] = []
    results: list[dict] = []

    for i in range(turns):
        question = _QUESTIONS[i % len(_QUESTIONS)]
        context = _wrap(_context_block(i + 1, target=_CHARS_PER_CHUNK * top_k)) if top_k else ""

        current_turn = [{"role": "user", "content": question}]
        history.append(current_turn)
        messages = [{"role": "system", "content": config.SYSTEM_PROMPT}] + [
            m for turn in history for m in turn
        ]
        if context:
            messages[-1] = {"role": "user", "content": f"{context}\n\nQuestion: {question}"}

        start = time.monotonic()
        resp = requests.post(
            f"{url}/api/chat",
            json={"model": model, "messages": messages, "stream": True,
                  "options": {"num_ctx": config.LLM_NUM_CTX, "num_predict": 70}},
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
            "top_k": top_k,
            "turn": i + 1,
            "context_chars": len(context),
            "prompt_eval_count": final.get("prompt_eval_count"),
            "prompt_eval_seconds": round(final.get("prompt_eval_duration", 0) / 1e9, 2),
            "ttft_seconds": round(ttft or 0, 2),
        }
        results.append(row)
        print(f"  turn {row['turn']:>2}  ctx={row['context_chars']:>5}ch  "
              f"prompt={row['prompt_eval_count']:>5} tok  "
              f"prefill={row['prompt_eval_seconds']:>6.2f}s  ttft={row['ttft_seconds']:>6.2f}s", flush=True)
    return results


def main() -> None:
    model, url = config.OLLAMA_MODEL, config.OLLAMA_URL.rstrip("/")
    turns = 8
    print(f"[isolate-ragsize] model={model} turns={turns}", flush=True)
    requests.post(
        f"{url}/api/chat",
        json={"model": model, "messages": [{"role": "user", "content": "ok"}], "stream": False,
              "options": {"num_ctx": config.LLM_NUM_CTX, "num_predict": 1}},
        timeout=300,
    ).raise_for_status()

    runs = {str(k): run_arm(k, turns, model, url) for k in (4, 3, 2, 0)}

    print(f"\n{'top_k':>7}{'ctx chars':>12}{'mean prefill':>15}{'mean ttft':>12}", flush=True)
    for k, rows in runs.items():
        later = rows[1:]
        print(f"{k:>7}{later[0]['context_chars']:>12}"
              f"{sum(r['prompt_eval_seconds'] for r in later) / len(later):>14.2f}s"
              f"{sum(r['ttft_seconds'] for r in later) / len(later):>11.2f}s", flush=True)

    out = Path("logs") / f"isolate_ragsize_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"model": model, "turns": turns, "runs": runs}, indent=2))
    print(f"\n[isolate-ragsize] wrote {out}", flush=True)


if __name__ == "__main__":
    main()
