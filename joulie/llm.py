import json
import time
from collections.abc import Iterator

import requests

from joulie import config


def _eval_stats(done: dict) -> dict:
    """Ollama's token accounting off a final /api/chat chunk.

    prompt_eval_count is the whole prompt whether or not the KV cache served
    it, so the count alone says nothing about reuse — it's the duration that
    gives it away (a cached prefix returns in milliseconds). Both are kept, and
    the derived rate is what's actually comparable across turns of different
    prompt sizes. Durations are nanoseconds; missing keys read as 0 rather than
    raising, since a stream that errored mid-flight still gets recorded.
    """
    prompt_tokens = done.get("prompt_eval_count") or 0
    prompt_seconds = (done.get("prompt_eval_duration") or 0) / 1e9
    gen_tokens = done.get("eval_count") or 0
    gen_seconds = (done.get("eval_duration") or 0) / 1e9
    return {
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_seconds": prompt_seconds,
        "prompt_eval_tokens_per_second": prompt_tokens / prompt_seconds if prompt_seconds else 0.0,
        "eval_count": gen_tokens,
        "eval_seconds": gen_seconds,
    }


class Agent:
    def __init__(
        self,
        model: str = config.OLLAMA_MODEL,
        url: str = config.OLLAMA_URL,
        system_prompt: str = config.SYSTEM_PROMPT,
        retriever=None,
        max_history_turns: int = config.LLM_MAX_HISTORY_TURNS,
        trim_to: int = config.LLM_HISTORY_TRIM_TO,
        num_ctx: int = config.LLM_NUM_CTX,
        num_predict: int = config.LLM_NUM_PREDICT,
        rag_placement: str = config.LLM_RAG_PLACEMENT,
    ):
        self.model = model
        self.url = url.rstrip("/")
        self.system_prompt = system_prompt
        self.retriever = retriever
        self.max_history_turns = max_history_turns
        # How far back a trim cuts, once one is triggered. Clamped into
        # [1, max_history_turns]: above the cap it would never fire, and at 0 it
        # would drop the whole conversation. trim_to == max_history_turns is the
        # old per-turn behaviour, kept reachable so it can be A/B'd.
        self.trim_to = max(1, min(trim_to, max_history_turns)) if max_history_turns > 0 else trim_to
        self.num_ctx = num_ctx
        # Runaway backstop only — see config.LLM_NUM_PREDICT. warmup() overrides
        # it with 1, and passing 0 leaves Ollama's own default in place.
        self.num_predict = num_predict
        # "question" sends each turn's retrieved context on that turn's own user
        # message and keeps it out of history; "system" sends it as a system
        # message, which Ollama hoists to the top of the prompt in front of all
        # history — breaking the KV prefix every turn. See config.LLM_RAG_PLACEMENT.
        self.rag_placement = rag_placement
        # One list per completed/in-flight turn (its user message, then its
        # assistant reply once streamed, preceded by a context message only under
        # rag_placement == "system"). Kept as turn-groups rather than a flat list
        # so trimming to the last N turns can never split a turn from its context.
        self.turns: list[list[dict]] = []
        # Publishers retrieval put in front of the model on the last turn.
        self.last_sources: tuple = ()
        # Prompt/RAG size for the turn just built — read by SessionCore right
        # after the turn completes, to test whether input size (not history
        # length) explains a latency change the history cap alone doesn't.
        self.last_prompt_stats: dict = {}
        # Ollama's own accounting for the turn just streamed, taken off the
        # final chunk. prompt_eval_* is the number that separates a reused KV
        # prefix from a full re-prefill — the same token count taking 2.4x
        # longer is what identified the turn-5 cliff, and nothing in the turn
        # timings alone can tell those two apart.
        self.last_eval_stats: dict = {}
        # Time to first token measured from the POST, set by stream().
        self.last_post_ttft_seconds: float = 0.0

    def reset(self):
        self.turns = []
        self.last_sources = ()
        self.last_prompt_stats = {}
        self.last_eval_stats = {}
        self.last_post_ttft_seconds = 0.0

    def _options(self, **extra) -> dict:
        opts = {"num_ctx": self.num_ctx} if self.num_ctx > 0 else {}
        if self.num_predict > 0:
            opts["num_predict"] = self.num_predict
        opts.update(extra)
        return opts

    def warmup(self) -> float:
        """Force Ollama to load weights + compile Metal shaders. Returns seconds."""
        start = time.monotonic()
        resp = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": "ok"}],
                "stream": False,
                # Same num_ctx as the real turns: Ollama sizes the KV cache when
                # it loads the model, so warming up without it would load at the
                # 4096 default and then reload on the first real question.
                "options": self._options(num_predict=1),
            },
            timeout=180,
        )
        resp.raise_for_status()
        return time.monotonic() - start

    def _build_messages(self, user_text: str) -> tuple[list[dict], list[dict]]:
        """Returns (messages to send, this turn's message list) — the caller
        appends the assistant reply to the latter once the response is complete."""
        context_text = ""
        rag_chunk_count = 0
        rag_context_chars = 0
        # Cleared per turn: a panel still showing the previous answer's sources
        # would attribute this answer to material it never saw.
        self.last_sources = ()
        retrieval_seconds = 0.0
        if self.retriever is not None:
            _retrieval_start = time.monotonic()
            chunks = self.retriever.retrieve(user_text)
            retrieval_seconds = time.monotonic() - _retrieval_start
            if chunks:
                rag_chunk_count = len(chunks)
                self.last_sources = self.retriever.summarise_sources(chunks)
                context_block = self.retriever.format_context(chunks)
                rag_context_chars = len(context_block)
                # Log which publishers/documents were surfaced — useful for
                # tuning retrieval and verifying the stance mix.
                pub_counts: dict[str, int] = {}
                for c in chunks:
                    pub_counts[c.get("publisher_short", "?")] = pub_counts.get(c.get("publisher_short", "?"), 0) + 1
                summary = ", ".join(f"{p}×{n}" for p, n in sorted(pub_counts.items()))
                print(f"[rag] injected {len(chunks)} chunks ({summary})")
                context_text = (
                    "Relevant reference material from the New Zealand electrification "
                    "knowledge base. Sources are grouped by stance — remember: "
                    "authoritative facts can be stated plainly; Rewiring's claims "
                    "must be attributed.\n\n"
                    f"{context_block}\n\n"
                    "Use this material to inform your answer. Do not invent numbers. "
                    "If the material doesn't answer the question, say so."
                )

        # Trim BEFORE adding the new turn, so the cap bounds prior turns and the
        # question being answered right now is always included on top of it.
        # Turns already in self.turns are never rewritten (only appended to, until
        # dropped here), so between trims the system prompt + surviving turns form
        # a stable, append-only prefix that Ollama/llama.cpp can serve from its KV
        # cache instead of reprocessing the whole conversation. That holds only
        # because context is no longer carried in history: under
        # rag_placement == "system" Ollama hoists every turn's block to the top of
        # the rendered prompt, and this list's order stops meaning anything.
        #
        # A trim is the one thing that prefix cannot survive: dropping the oldest
        # turn shifts every token after the system prompt, so the next request
        # re-prefills everything from there (~10s at this model's ~185 tok/s).
        # With RAG kept out of history a turn costs only its question and answer
        # (~140-260 tokens), so the cap sits high enough — the first trim lands
        # at turn 18 — that a kiosk visit normally ends before one fires.
        # See logs/latency-analysis.md.
        trimmed = False
        if self.max_history_turns > 0 and len(self.turns) > self.max_history_turns:
            self.turns = self.turns[-self.trim_to:]
            trimmed = True

        current_turn: list[dict] = []
        if context_text and self.rag_placement == "system":
            current_turn.append({"role": "system", "content": context_text})
        current_turn.append({"role": "user", "content": user_text})
        self.turns.append(current_turn)

        history = [msg for turn in self.turns for msg in turn]
        messages = [{"role": "system", "content": self.system_prompt}] + history
        if context_text and self.rag_placement != "system":
            # Rides along with this turn's question but is never stored: history
            # keeps the bare question, so the next turn's prompt extends this one
            # instead of inserting a fresh block ahead of it. Replaced rather than
            # mutated — the message object in self.turns must stay context-free.
            messages[-1] = {"role": "user", "content": f"{context_text}\n\n{user_text}"}
        self.last_prompt_stats = {
            "prompt_chars": sum(len(m["content"]) for m in messages),
            "rag_chunk_count": rag_chunk_count,
            "rag_context_chars": rag_context_chars,
            "history_turns": len(self.turns),
            # Flags the one turn in the block that dropped the KV prefix, so a
            # slow turn in the logs can be matched to its cause rather than
            # inferred from turn position.
            "history_trimmed": trimmed,
            # Retrieval was folded into llm_ttft_seconds, which is named for the
            # LLM. It measures ~0.26s live, so it was never the problem — but a
            # metric that hides another component is how the first two passes of
            # logs/latency-analysis.md went wrong.
            "retrieval_seconds": retrieval_seconds,
        }
        return messages, current_turn

    def stream(self, user_text: str) -> Iterator[str]:
        """Yield text tokens from Ollama as they arrive. Updates history when exhausted."""
        messages, current_turn = self._build_messages(user_text)
        stats = self.last_prompt_stats
        self.last_eval_stats = {}
        print(
            f"[llm] POST /api/chat (prompt: {stats['prompt_chars']} chars, "
            f"{stats['history_turns']} turns of history, "
            f"rag: {stats['rag_chunk_count']} chunks / {stats['rag_context_chars']} chars"
            f"{', history trimmed — KV prefix dropped' if stats['history_trimmed'] else ''})"
        )
        post_at = time.monotonic()
        resp = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": True,
                "options": self._options(),
            },
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()
        print("[llm] connection established, waiting for first token...")
        accumulated: list[str] = []
        first = True
        # The LLM leg on its own. SessionCore's llm_ttft_seconds runs from end of
        # utterance and so also carries STT, retrieval and prompt assembly; this
        # is the part Ollama is responsible for.
        self.last_post_ttft_seconds = 0.0
        try:
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                data = json.loads(raw_line)
                token = data.get("message", {}).get("content", "")
                if token:
                    if first:
                        self.last_post_ttft_seconds = time.monotonic() - post_at
                        print(f"[llm] first token received (+{self.last_post_ttft_seconds:.2f}s from POST)")
                        first = False
                    accumulated.append(token)
                    yield token
                if data.get("done"):
                    self.last_eval_stats = _eval_stats(data)
                    ev = self.last_eval_stats
                    print(
                        f"[llm] stream done ({len(accumulated)} tokens); "
                        f"prefill {ev['prompt_eval_count']} tok in "
                        f"{ev['prompt_eval_seconds']:.2f}s "
                        f"({ev['prompt_eval_tokens_per_second']:.0f} tok/s)"
                    )
                    self._warn_if_near_ctx(ev["prompt_eval_count"])
                    break
        finally:
            full_text = "".join(accumulated).strip()
            if full_text:
                current_turn.append({"role": "assistant", "content": full_text})

    def _warn_if_near_ctx(self, prompt_tokens: int) -> None:
        """Ollama never says it is about to overrun num_ctx — it silently drops
        messages off the front, which breaks the KV prefix and costs 36-40s on
        the turn it happens (isolate_ragplacement.py drove two arms into the
        limit; see logs/latency-analysis.md). prompt_eval_count is already in
        hand, so the warning is free and turns a mystery turn into a logged one."""
        if self.num_ctx <= 0 or not prompt_tokens:
            return
        used = prompt_tokens / self.num_ctx
        if used >= config.LLM_CTX_WARN_FRACTION:
            print(
                f"[llm] WARNING: prompt is {prompt_tokens}/{self.num_ctx} tokens "
                f"({used:.0%} of num_ctx). Ollama truncates from the front past "
                f"this, which breaks the KV prefix and costs ~40s on that turn. "
                f"Raise JOULIE_LLM_NUM_CTX or lower JOULIE_LLM_MAX_HISTORY_TURNS."
            )

    def reply(self, user_text: str) -> str:
        messages, current_turn = self._build_messages(user_text)
        resp = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": self._options(),
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        self.last_eval_stats = _eval_stats(data)
        self._warn_if_near_ctx(self.last_eval_stats["prompt_eval_count"])
        text = data.get("message", {}).get("content", "").strip()
        current_turn.append({"role": "assistant", "content": text})
        return text
