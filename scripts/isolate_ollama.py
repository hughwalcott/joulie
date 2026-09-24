"""One-shot diagnostic script: hammer Ollama's /api/chat directly, with no
Whisper, XTTS, or ChromaDB in the loop, to test whether Joulie's turn-5+
TTFT onset (see logs/sessions/*.jsonl, sessions 3-8; joulie/session_core.py
JTBD-08 diagnostics) lives inside Ollama/llama.cpp itself or depends on
contention with the rest of the pipeline sharing the machine's unified
memory.

Builds a synthetic conversation whose per-turn prompt sizes track the real
growth observed in session 8 (~4.7k -> ~15k chars by turn 4, then
plateauing) and issues the same request shape joulie.llm.Agent does — same
history cap, same POST /api/chat streaming call — with no artificial delay
beyond what generation itself takes. If the same TTFT jump reproduces here,
the cause is internal to Ollama; if it doesn't, that points at contention
with the rest of Joulie's pipeline instead.

Usage:
    source .venv/bin/activate
    python scripts/isolate_ollama.py
"""

import json
import sys
import time
from pathlib import Path

import requests

# Run as a plain script (`python scripts/isolate_ollama.py`), so the repo
# root — not this file's own directory — needs to be on sys.path for the
# `joulie` import below to resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from joulie import config

# Real prompt_chars observed in session 8 (logs/sessions/20260913T233426.jsonl)
# — reused here so each synthetic request is shaped like a real one, even
# though the content is filler. Repeats the last value for any extra turns.
_TARGET_PROMPT_CHARS = [
    4717, 8078, 11432, 14726, 13963, 11146, 10375, 10558, 11190, 14092, 14283, 14500,
]

_FILLER_SENTENCE = (
    "New Zealand households considering electrification should weigh solar, "
    "battery storage, and heat pump upgrades against their own usage patterns. "
)

_QUESTIONS = [
    "What's the payback period on rooftop solar for a typical Auckland home?",
    "How does a heat pump hot water cylinder compare to a standard electric one?",
    "Is it worth switching from LPG to induction cooking?",
    "What rebates exist for EV chargers in New Zealand right now?",
    "How much does insulation retrofitting typically save on power bills?",
    "Should I get a home battery if I already have solar panels?",
    "What's the difference between a hybrid and a fully electric heat pump?",
    "How do time-of-use electricity plans work for EV owners?",
    "Is off-grid solar realistic for a lifestyle block?",
    "What size solar system do I need for a 3-bedroom house?",
    "How long do EV batteries typically last in NZ conditions?",
    "Are there financing options for whole-home electrification?",
]


def _filler(target_chars: int, used_chars: int) -> str:
    """Pads a system message out to roughly target_chars, standing in for
    the RAG context block a real turn would carry."""
    pad_needed = max(0, target_chars - used_chars)
    if pad_needed == 0:
        return ""
    reps = pad_needed // len(_FILLER_SENTENCE) + 1
    return (_FILLER_SENTENCE * reps)[:pad_needed]


def run(
    model: str = config.OLLAMA_MODEL,
    url: str = config.OLLAMA_URL,
    turns: int = 12,
    max_history_turns: int = config.LLM_MAX_HISTORY_TURNS,
) -> list[dict]:
    print(f"[isolate] model={model} url={url} max_history_turns={max_history_turns}")
    history: list[list[dict]] = []
    session_start = time.monotonic()
    results = []

    for i in range(turns):
        question = _QUESTIONS[i % len(_QUESTIONS)]
        target = _TARGET_PROMPT_CHARS[min(i, len(_TARGET_PROMPT_CHARS) - 1)]

        # Same trim-before-append shape as Agent._build_messages, so history
        # size here matches what a real turn would actually send.
        if max_history_turns > 0 and len(history) > max_history_turns:
            history = history[-max_history_turns:]

        used = (
            len(config.SYSTEM_PROMPT)
            + sum(len(m["content"]) for turn in history for m in turn)
            + len(question)
        )
        context_text = _filler(target, used)
        current_turn: list[dict] = []
        if context_text:
            current_turn.append({"role": "system", "content": context_text})
        current_turn.append({"role": "user", "content": question})
        history.append(current_turn)

        messages = [{"role": "system", "content": config.SYSTEM_PROMPT}] + [
            m for turn in history for m in turn
        ]
        prompt_chars = sum(len(m["content"]) for m in messages)

        t0 = time.monotonic()
        resp = requests.post(
            f"{url}/api/chat",
            json={"model": model, "messages": messages, "stream": True},
            timeout=180,
            stream=True,
        )
        resp.raise_for_status()
        ttft = None
        reply_parts: list[str] = []
        token_count = 0
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            data = json.loads(raw_line)
            token = data.get("message", {}).get("content", "")
            if token:
                if ttft is None:
                    ttft = time.monotonic() - t0
                reply_parts.append(token)
                token_count += 1
            if data.get("done"):
                break
        total = time.monotonic() - t0
        reply = "".join(reply_parts).strip()
        current_turn.append({"role": "assistant", "content": reply})
        elapsed = time.monotonic() - session_start

        row = {
            "turn": i + 1,
            "elapsed_s": round(elapsed, 2),
            "prompt_chars": prompt_chars,
            "ttft_s": round(ttft, 3) if ttft is not None else None,
            "total_s": round(total, 3),
            "tokens": token_count,
        }
        results.append(row)
        print(
            f"[isolate] turn {row['turn']:2d}  +{row['elapsed_s']:6.1f}s  "
            f"prompt={row['prompt_chars']:6d} chars  "
            f"ttft={row['ttft_s'] if row['ttft_s'] is not None else float('nan'):6.2f}s  "
            f"total={row['total_s']:6.2f}s  tokens={row['tokens']}"
        )

    return results


if __name__ == "__main__":
    rows = run()
    out_dir = Path(config.METRICS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"isolate_ollama_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out_path.write_text(json.dumps(rows, indent=2))
    print(f"[isolate] wrote {out_path}")
