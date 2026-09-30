import os
from pathlib import Path

_repo_root = Path(__file__).parent.parent


def _codes(value: str) -> tuple[str, ...]:
    return tuple(c.strip() for c in value.split(",") if c.strip())


OLLAMA_URL = os.environ.get("JOULIE_OLLAMA_URL", "http://localhost:11434")
# 14B scores 58% on the question bank against the 3B's 38% (evals/report.html), and
# roughly halves the fabricated-answer rate. 9GB leaves room for XTTS, Whisper and
# Chroma on a 24GB machine; an 18GB model does not. First token takes ~7s, not ~2s.
OLLAMA_MODEL = os.environ.get("JOULIE_OLLAMA_MODEL", "qwen2.5:14b-instruct-q4_K_M")

WHISPER_MODEL = os.environ.get("JOULIE_WHISPER_MODEL", "base")
# Languages whose transcription is redone with a larger Whisper, because base
# cannot write them. Forced to Hindi, base romanised the question ("Garm Pani ke
# Silendar"), and with a Devanagari prompt it hallucinated for 6.3s; small wrote
# correct Devanagari in 1.6s. Base found the right material for every other
# voiced language 0.6s faster than small, so only these pay for it — and English
# never does. Language detection always runs on WHISPER_MODEL.
WHISPER_STRONG_MODEL = os.environ.get("JOULIE_WHISPER_STRONG_MODEL", "small")
WHISPER_STRONG_LANGUAGES = _codes(os.environ.get("JOULIE_WHISPER_STRONG_LANGUAGES", "hi"))

TTS_MODEL = os.environ.get("JOULIE_TTS_MODEL", "tts_models/en/vctk/vits")
TTS_VOICE = os.environ.get("JOULIE_TTS_VOICE", "p306")
TTS_SPEED = float(os.environ.get("JOULIE_TTS_SPEED", "1.1"))

XTTS_MODEL = os.environ.get("JOULIE_XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
XTTS_REF_WAV = os.environ.get("JOULIE_XTTS_REF_WAV", str(_repo_root / "specs" / "kiwi voice-30s.wav"))
XTTS_LANGUAGE = os.environ.get("JOULIE_XTTS_LANGUAGE", "en")
XTTS_SAMPLE_RATE = 24000
# Languages XTTS runs a warm-up inference for at startup. Each first use of a
# language loads its text-processing path (~1s, more for zh-cn's pypinyin);
# warming all fourteen would add 10-15s to boot, so the rest pay it on their
# first answer instead.
XTTS_WARMUP_LANGUAGES = _codes(os.environ.get("JOULIE_XTTS_WARMUP_LANGUAGES", "en,zh"))
# TTS.api's get_conditioning_latents() signature defaults to 6s of GPT conditioning,
# which is NOT what the shipped XTTS-v2 config asks for (gpt_cond_len 30,
# gpt_cond_chunk_len 4, max_ref_len 30) and would throw away all but the first six
# seconds of the reference. Pass the model's own values so the full clip is used.
XTTS_GPT_COND_LEN = int(os.environ.get("JOULIE_XTTS_GPT_COND_LEN", "30"))
XTTS_GPT_COND_CHUNK_LEN = int(os.environ.get("JOULIE_XTTS_GPT_COND_CHUNK_LEN", "4"))
XTTS_MAX_REF_LEN = int(os.environ.get("JOULIE_XTTS_MAX_REF_LEN", "30"))
# The reference peaks at about -9 dBFS; XTTS conditions on absolute level, so
# normalise on load rather than re-recording or pre-processing the WAV.
XTTS_SOUND_NORM_REFS = os.environ.get("JOULIE_XTTS_SOUND_NORM_REFS", "1") not in ("0", "false", "no")
# XTTS applies speed by interpolating the GPT latents, so a faster voice costs
# nothing to synthesise but shortens every answer. TTS_SPEED above only reaches
# the VITS fallback.
XTTS_SPEED = float(os.environ.get("JOULIE_XTTS_SPEED", "1.2"))

# Languages Joulie answers in (JTBD-03), as Whisper codes — joulie/language.py
# holds what each one needs. LANGUAGES are answered aloud in the cloned voice;
# TEXT_ONLY_LANGUAGES are answered on screen with a short spoken English note,
# for languages Joulie can understand but XTTS-v2 cannot voice (te reo Māori
# is "mi"). Anything Whisper detects outside both lists is treated as English.
# The default is every language XTTS-v2 can voice that joulie/language.py has an
# entry for. Hindi's answers are the weakest of these from Qwen2.5-14B — check
# them with a speaker before relying on it.
LANGUAGES = _codes(os.environ.get(
    "JOULIE_LANGUAGES", "en,zh,hi,es,fr,de,it,pt,nl,pl,ru,cs,hu,tr"))
TEXT_ONLY_LANGUAGES = _codes(os.environ.get("JOULIE_TEXT_ONLY_LANGUAGES", ""))
# A session switches language only on a confident detection of an utterance long
# enough to trust — Whisper's language ID on a one-word reply is close to a coin
# toss, and a false switch answers an English visitor in Mandarin.
LANG_SWITCH_MIN_PROB = float(os.environ.get("JOULIE_LANG_SWITCH_MIN_PROB", "0.7"))
LANG_SWITCH_MIN_SECONDS = float(os.environ.get("JOULIE_LANG_SWITCH_MIN_SECONDS", "1.5"))

GREETING_WAV = os.environ.get("JOULIE_GREETING_WAV", str(_repo_root / "assets" / "greeting.wav"))

SAMPLE_RATE = 16000

# The JBL Quantum Stream Talk's mute button drives the whole kiosk: unmuted means
# Joulie is listening. It reports state (not edges) as report 0x06 with a single
# payload byte — 0x01 live, 0x00 muted — measured against the audio stream, which
# the firmware gates to exact zeros when muted.
HANDSET_ENABLED = os.environ.get("JOULIE_HANDSET_ENABLED", "1") not in ("0", "false", "no")
HANDSET_VID = int(os.environ.get("JOULIE_HANDSET_VID", "0x0ECB"), 0)
HANDSET_PID = int(os.environ.get("JOULIE_HANDSET_PID", "0x20AF"), 0)
HANDSET_REPORT_ID = int(os.environ.get("JOULIE_HANDSET_REPORT_ID", "0x06"), 0)
# Seconds muted, with Joulie silent, before the session clears itself for the next
# visitor. The timer never runs while she is speaking — see TalkController.tick.
HANDSET_IDLE_TIMEOUT = float(os.environ.get("JOULIE_HANDSET_IDLE_TIMEOUT", "45"))
HANDSET_SILENT_TURNS_TO_END = int(os.environ.get("JOULIE_HANDSET_SILENT_TURNS_TO_END", "2"))
# How often the Gradio UI polls for handset-driven turns. Set to 0 to disable the
# poller entirely — useful for isolating it when diagnosing UI repaint problems.
HANDSET_UI_POLL_SECONDS = float(os.environ.get("JOULIE_HANDSET_UI_POLL_SECONDS", "0.4"))

# How often a turn emits a TurnEvent while waiting on the LLM. Without it the
# turn generator blocks on the token queue for the whole 6-10s to first token and
# the screen cannot show retrieval finishing or the pipeline advancing. Keep this
# ABOVE HANDSET_UI_POLL_SECONDS: a heartbeat faster than the poll produces events
# nobody ever renders.
UI_HEARTBEAT_SECONDS = float(os.environ.get("JOULIE_UI_HEARTBEAT_SECONDS", "0.5"))

# Reveals the Start Session and Stop Talking buttons, which the kiosk never shows
# — the mute button starts a session and End Session absorbs the barge-in. Without
# this there is no way to drive a session from a browser with no handset attached,
# so JOULIE_HANDSET_ENABLED=0 wants JOULIE_UI_DEBUG_CONTROLS=1 alongside it.
UI_DEBUG_CONTROLS = os.environ.get("JOULIE_UI_DEBUG_CONTROLS", "0") not in ("0", "false", "no")

KNOWLEDGE_BASE_PATH = os.environ.get("JOULIE_KB_PATH", str(_repo_root / "knowledge_base"))
CHROMA_PATH = os.environ.get("JOULIE_CHROMA_PATH", str(_repo_root / "chroma_db"))
CHROMA_COLLECTION = os.environ.get("JOULIE_CHROMA_COLLECTION", "joulie_kb")
EMBED_MODEL = os.environ.get("JOULIE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
# Every retrieved chunk is prefilled on each turn, and under
# LLM_RAG_PLACEMENT=question the retrieved block is the ONLY part of the prompt
# Ollama cannot serve from its KV cache — isolate_ragsize.py measured 3.22s of
# prefill at k=4 against a 0.21s floor with no context at all. k=6 reached ~5.8k
# prompt chars and ~1.8s to first token; k=3 saves ~0.47s isolated, ~0.7s live,
# and still keeps the authoritative/advocacy mix format_context depends on.
# It costs no measurable retrieval quality: figure recall moved 0.557 -> 0.526
# across the 107-question bank, against 0.557 -> 0.530 for re-running the SAME
# config, and the 95% CI on the paired per-question difference crosses zero for
# both. Halving CHUNK_SIZE was the alternative and is five times worse — see
# ingest.py. k=2 is untested; measure before taking it.
# Re-confirmed at k=3 against the full shipped config (run D, 2026-09-18):
# figure recall 0.545 against the baseline's 0.557, CI [-0.055, +0.036]. The
# aggregate is clean, but it is a trade, not a free win - T4Q1 ("what share of
# our electricity is renewable?") now answers with the primary-energy share,
# 45.5%, instead of the electricity share, 85.5%, on the question as asked,
# while getting it right on the rephrasing. Both figures are retrieved; the
# top-3 ordering decides which one leads.
# logs/latency-analysis.md, "Third pass" and "Accuracy check, 2026-09-18".
RAG_TOP_K = int(os.environ.get("JOULIE_RAG_TOP_K", "3"))
RAG_DISTANCE_THRESHOLD = float(os.environ.get("JOULIE_RAG_DISTANCE_THRESHOLD", "0.7"))
# Non-English questions (JTBD-03) are searched in a second collection: the same
# chunks, IDs and metadata as CHROMA_COLLECTION, re-embedded by a multilingual
# model — ingest.py keeps it mirrored. EMBED_MODEL is English-only and finds
# 0.21 of the English results from a translated question; this model finds 0.64
# across Mandarin, Hindi and eleven European languages, against 0.67 for its own
# English, so the gap is the model and not the language. multilingual-e5-small
# and -base scored 0.55 and 0.64, but their on-topic and off-topic distances
# overlap, so no threshold can keep small talk out of the prompt.
# evals/multilingual_retrieval.py; English turns never touch any of this.
MULTILINGUAL_EMBED_MODEL = os.environ.get(
    "JOULIE_MULTILINGUAL_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
MULTILINGUAL_CHROMA_COLLECTION = os.environ.get("JOULIE_MULTILINGUAL_CHROMA_COLLECTION", "joulie_kb_multilingual")
# This model's distances run on a different scale from EMBED_MODEL's. On-topic
# top-1 distance measured 0.37 at p90 and off-topic small talk no closer than
# 0.69, in every language tested; 0.55 splits the gap.
RAG_MULTILINGUAL_DISTANCE_THRESHOLD = float(os.environ.get("JOULIE_RAG_MULTILINGUAL_DISTANCE_THRESHOLD", "0.55"))
# Whisper codes the multilingual model was trained on. A session language
# outside this list (te reo Māori is not in it) retrieves on Whisper's English
# translation instead — slower and looser, but better than nothing.
RAG_MULTILINGUAL_LANGUAGES = _codes(os.environ.get(
    "JOULIE_RAG_MULTILINGUAL_LANGUAGES",
    "ar,bg,ca,cs,da,de,el,es,et,fa,fi,fr,gl,gu,he,hi,hr,hu,hy,id,it,ja,ka,ko,lt,lv,"
    "mk,mn,mr,ms,my,nl,no,pl,pt,ro,ru,sk,sl,sq,sr,sv,th,tr,uk,ur,vi,zh",
))
RAG_ENABLED = os.environ.get("JOULIE_RAG_ENABLED", "1") not in ("0", "false", "no")

# Where each turn's retrieved context is placed in the request.
#
# Ollama collates EVERY role=system message into one block at the TOP of the
# rendered prompt — verified on 0.32.1 with `"_debug_render_only": true`. A
# per-turn RAG block sent as a system message therefore lands in front of the
# entire conversation and shifts every history token behind it, so the KV
# prefix breaks on every single turn however history is trimmed. That, not the
# trim, was most of the prefill cost in logs/latency-analysis.md.
#
# "question" attaches the block to the current user message instead, and keeps
# only the bare question in history once the turn is done, so the prompt grows
# append-only and prefill stays flat. Measured over 12 turns: 3.4s flat,
# against 3.3->6.7s plus 8.9s trim turns for "system". "system" restores the
# old shape so the two stay A/B-able. What "question" gives up is that a
# follow-up no longer sees the previous turns' chunks, only the answers they
# produced — evals/followups.py is the probe for that.
LLM_RAG_PLACEMENT = os.environ.get("JOULIE_LLM_RAG_PLACEMENT", "question")

# History is trimmed in BLOCKS: let it grow to LLM_MAX_HISTORY_TURNS, then cut
# back to LLM_HISTORY_TRIM_TO in one go. A trim re-prefills everything after the
# system prompt (~10s at this model's ~185 tok/s), so with RAG out of history
# the cap is a backstop, not a working dial: a completed turn now costs only the
# question plus its answer (~140 tokens at a typical reply length, ~260 at the
# longest reply measured), the first trim lands at turn 18, and
# SessionCore.end_session() resets history per visitor — so a normal 10-15 turn
# visit never reaches a trim at all.
# 0 disables trimming entirely (unbounded history).
LLM_MAX_HISTORY_TURNS = int(os.environ.get("JOULIE_LLM_MAX_HISTORY_TURNS", "16"))
LLM_HISTORY_TRIM_TO = int(os.environ.get("JOULIE_LLM_HISTORY_TRIM_TO", "8"))

# Ollama defaults num_ctx to 4096 whatever the model declares (qwen2.5:14b
# declares 32768), and never warns when a prompt overruns it — it just drops
# messages off the front, which breaks the KV prefix by another route.
#
# Overrunning it is far worse than the turn-5 cliff this branch started on.
# isolate_ragplacement.py drove two arms into the limit at 6138/6139 tokens
# against num_ctx 6144 and both turns took **36-40s** — an order of magnitude
# worse than the ~10s re-prefill, because the context shift happens when the
# prompt is at its largest. At LLM_RAG_PLACEMENT=question the live session
# 20260916T225408 grew 168 tok/turn (max 259), which projects to 3927 tokens at
# the turn-18 trim — but a visitor whose answers run 300 tokens projects to
# 6434, past 6144. 8192 puts that tail safely inside the window.
# Costs KV cache, halved by OLLAMA_KV_CACHE_TYPE=q8_0: /api/ps measured 9309MB
# resident at 6144 against 9093MB at 4096 (+216MB per 2048 tokens), so 8192 is
# roughly +215MB again. Agent.stream warns at LLM_CTX_WARN_FRACTION of this.
LLM_NUM_CTX = int(os.environ.get("JOULIE_LLM_NUM_CTX", "8192"))

# Warn when a prompt gets close enough to num_ctx that the next turn could tip
# over. prompt_eval_count is already recorded per turn, so this costs nothing to
# check and turns a silent 40s turn into a logged one.
LLM_CTX_WARN_FRACTION = float(os.environ.get("JOULIE_LLM_CTX_WARN_FRACTION", "0.8"))

# Backstop against a runaway generation, NOT the dial for answer length. A hard
# token cap cuts mid-word, and session 20260916T225408 averaged 136 generated
# tokens with a maximum of 230 — a cap anywhere near the mean would truncate a
# spoken answer mid-sentence, which is worse for a kiosk visitor than a slow one.
# This sits above the whole observed distribution so it only ever catches a
# model that will not stop, which matters because an unbounded reply also eats
# the num_ctx headroom above. Answer length is shaped in SYSTEM_PROMPT instead,
# where the cost in figure recall is visible to evals/compare_runs.py.
# 0 disables the cap.
LLM_NUM_PREDICT = int(os.environ.get("JOULIE_LLM_NUM_PREDICT", "260"))

METRICS_ENABLED = os.environ.get("JOULIE_METRICS_ENABLED", "1") not in ("0", "false", "no")
METRICS_DIR = os.environ.get("JOULIE_METRICS_DIR", str(_repo_root / "logs"))
# Requires a passwordless-sudo NOPASSWD entry for powermetrics on the kiosk
# account (see README) — without it, PowerSampler disables itself and turn
# metrics simply come back without power/thermal fields.
POWER_SAMPLING_ENABLED = os.environ.get("JOULIE_POWER_SAMPLING_ENABLED", "1") not in ("0", "false", "no")
POWER_SAMPLE_INTERVAL_MS = int(os.environ.get("JOULIE_POWER_SAMPLE_INTERVAL_MS", "1000"))

GREETING = "Hi, I'm Joulie. How can I help?"

# Standby-screen copy. The kiosk is voice-only, so the screen's job here is to
# make the one physical action obvious and to show that the questions people
# actually want to ask are in scope — scenarios.md A7 asks for exactly this
# prompt, and A1's visitor arrives having read "Ask me about going electric" on
# the table sign, so the screen repeats it back to her.
KIOSK_ATTRACT_CTA = "Press the mic button (firmly) to talk to Joulie"
KIOSK_ATTRACT_CTA_BROWSER = "Press Start Session to talk to Joulie"
KIOSK_READY_CTA = "Just ask — Joulie is listening"
# "How do I compare power plans?" earns its place by matching a tools.py
# REGISTRY keyword, so a visitor who takes the suggestion gets a QR code on
# their first turn rather than discovering the feature by accident.
KIOSK_EXAMPLE_QUESTIONS: tuple[str, ...] = (
    "Ask me about going electric",
    "My gas hot water cylinder is dying — what should I replace it with?",
    "How do I compare power plans?",
)

# Longer disclaimer shown as UI text (not spoken) — the Gradio header renders this
# and the kiosk banner prints it at startup so both modes surface it.
DISCLAIMER = (
    "Joulie shares information about electrifying homes and businesses in New Zealand. "
    "Answers are informational and may be incomplete. "
    "For decisions, please consult a qualified professional."
)

SYSTEM_PROMPT = (
    "You are Joulie, a New Zealand electrification advisor. "
    "Answer in TWO to FOUR sentences. Under 200 words total. "
    "No preamble ('That's a great question'). No summary ('In summary'). "
    "No bullet points or asterisks. Just answer directly in warm, plain English. "
    "\n\n"
    "Attribution rules — critical:\n"
    "• Government sources (EECA, Electricity Authority, Commerce Commission, MBIE) "
    "are authoritative. State their facts plainly; cite the publisher when useful.\n"
    "• Rewiring Aotearoa is an advocacy charity, NOT a regulator. Attribute their "
    "claims explicitly, e.g. 'Rewiring Aotearoa argues …' or 'According to Rewiring …'. "
    "Never present Rewiring's positions as neutral fact.\n"
    "• Always name the year when quoting a statistic (e.g. 'in 2024, …'). "
    "Energy figures change year to year.\n"
    "• Regulator content is general information, not legal advice. For anything "
    "binding, tell the person to check with their retailer, lines company, or the "
    "official Electricity Industry Code.\n"
    "\n"
    "Tools — for numbers, redirect to an official tool. Say the tool NAME only; "
    "the kiosk screen shows the QR code. Never speak URLs aloud.\n"
    "• Compare power plans → 'Billy' (Electricity Authority)\n"
    "• Home energy savings → 'the EECA home energy savings calculator'\n"
    "• Household electrification savings → 'the Rewiring electric calculator'\n"
    "• Solar potential at your address → 'NIWA SolarView'\n"
    "• Sizing a solar system → 'the EECA solar power calculator'\n"
    "• Meter or ICP lookup → 'the EA \"Your meter\" tool'\n"
    "• Appliance efficiency → 'the EECA efficient appliance calculator'\n"
    "• Insulation and heating grants → 'the Warmer Kiwi Homes eligibility check'\n"
    "When you name a tool, add 'scan the QR code on screen'.\n"
    "\n"
    "Never recommend specific brands. If asked about an electrical hazard, "
    "tell the person to stop and call a registered electrician or emergency services. "
    "If you don't know, say so and offer to take a message for the Electrify the Hutt team."
)
