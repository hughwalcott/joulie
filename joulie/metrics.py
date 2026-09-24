"""Per-turn latency/power capture and per-conversation performance summaries
(JTBD-08: "a summary, satisfaction score, and timing metrics captured" at the
end of each session — this covers the timing/power half)."""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from joulie import config


@dataclass
class TurnMetrics:
    turn_index: int
    started_at: float
    stt_seconds: float = 0.0
    # Time to first token measured from END OF UTTERANCE. It therefore folds in
    # STT, retrieval, prompt assembly and HTTP as well as prefill — it is the
    # number the visitor actually waits, and the series every session in
    # logs/latency-analysis.md is expressed in, so its meaning is kept stable.
    # The two fields below break it apart; see logs/latency-analysis.md
    # recommendation 6 ("Split llm_ttft_seconds").
    llm_ttft_seconds: float = 0.0
    # ChromaDB query + embedding for this turn, measured around retrieve().
    rag_retrieval_seconds: float = 0.0
    # Time to first token measured from the POST to /api/chat — the LLM leg
    # alone. llm_ttft_seconds minus this is everything Joulie does before Ollama
    # sees the request.
    llm_post_ttft_seconds: float = 0.0
    llm_total_seconds: float = 0.0
    llm_tokens: int = 0
    tts_ttfa_seconds: float = 0.0
    tts_chunk_synth_seconds: list = field(default_factory=list)
    tts_chunk_rtf: list = field(default_factory=list)
    turn_total_seconds: float = 0.0
    power: dict = field(default_factory=dict)
    # Size of what was actually sent to Ollama this turn — added to test
    # whether a latency change tracks input size rather than turn position
    # once history is capped (history_turns is the turn count *after*
    # trimming, i.e. what the cap actually left in the prompt).
    prompt_chars: int = 0
    rag_chunk_count: int = 0
    rag_context_chars: int = 0
    history_turns: int = 0
    # Whether this turn's trim dropped history (and with it Ollama's cached
    # prefix). Expected on one turn per block; the turn that pays the re-prefill.
    history_trimmed: bool = False
    # Ollama's own token accounting for this turn. prompt_eval_seconds is the
    # prefill — the part the KV cache can serve — measured server-side, so it
    # excludes STT, retrieval and HTTP that llm_ttft_seconds folds in.
    # prompt_eval_tokens_per_second is the comparable figure across turns of
    # different prompt sizes: a reused prefix runs several times faster than a
    # cold one at the same token count.
    prompt_eval_count: int = 0
    prompt_eval_seconds: float = 0.0
    prompt_eval_tokens_per_second: float = 0.0
    eval_count: int = 0
    eval_seconds: float = 0.0

    @property
    def tts_rtf_max(self) -> float:
        return max(self.tts_chunk_rtf, default=0.0)


@dataclass
class SessionSummary:
    session_id: str
    started_at: float
    ended_at: float
    num_turns: int
    avg_llm_ttft_seconds: float
    max_llm_ttft_seconds: float
    avg_tts_rtf: float
    max_tts_rtf: float
    total_duration_seconds: float
    throttled: bool


def _sessions_dir() -> Path:
    d = Path(config.METRICS_DIR) / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def append_turn(session_id: str, turn: TurnMetrics) -> None:
    if not config.METRICS_ENABLED:
        return
    path = _sessions_dir() / f"{session_id}.jsonl"
    with path.open("a") as f:
        f.write(json.dumps(asdict(turn)) + "\n")


def build_summary(session_id: str, started_at: float, turns: list[TurnMetrics]) -> SessionSummary:
    ended_at = time.time()
    ttfts = [t.llm_ttft_seconds for t in turns if t.llm_ttft_seconds]
    rtfs = [r for t in turns for r in t.tts_chunk_rtf]
    throttled = any(
        t.power.get("thermal_pressure_max") not in (None, "Nominal") for t in turns
    )
    return SessionSummary(
        session_id=session_id,
        started_at=started_at,
        ended_at=ended_at,
        num_turns=len(turns),
        avg_llm_ttft_seconds=sum(ttfts) / len(ttfts) if ttfts else 0.0,
        max_llm_ttft_seconds=max(ttfts, default=0.0),
        avg_tts_rtf=sum(rtfs) / len(rtfs) if rtfs else 0.0,
        max_tts_rtf=max(rtfs, default=0.0),
        total_duration_seconds=ended_at - started_at,
        throttled=throttled,
    )


def write_summary(summary: SessionSummary) -> None:
    if not config.METRICS_ENABLED:
        return
    path = _sessions_dir() / f"{summary.session_id}_summary.json"
    path.write_text(json.dumps(asdict(summary), indent=2))
