import os
from pathlib import Path

_repo_root = Path(__file__).parent.parent

OLLAMA_URL = os.environ.get("JOULIE_OLLAMA_URL", "http://localhost:11434")
# 14B scores 58% on the question bank against the 3B's 38% (evals/report.html), and
# roughly halves the fabricated-answer rate. 9GB leaves room for XTTS, Whisper and
# Chroma on a 24GB machine; an 18GB model does not. First token takes ~7s, not ~2s.
OLLAMA_MODEL = os.environ.get("JOULIE_OLLAMA_MODEL", "qwen2.5:14b-instruct-q4_K_M")

WHISPER_MODEL = os.environ.get("JOULIE_WHISPER_MODEL", "base")

TTS_MODEL = os.environ.get("JOULIE_TTS_MODEL", "tts_models/en/vctk/vits")
TTS_VOICE = os.environ.get("JOULIE_TTS_VOICE", "p306")
TTS_SPEED = float(os.environ.get("JOULIE_TTS_SPEED", "1.2"))

XTTS_MODEL = os.environ.get("JOULIE_XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
XTTS_REF_WAV = os.environ.get("JOULIE_XTTS_REF_WAV", str(_repo_root / "specs" / "kiwi voice-15s.wav"))
XTTS_LANGUAGE = os.environ.get("JOULIE_XTTS_LANGUAGE", "en")
XTTS_SAMPLE_RATE = 24000
# XTTS applies speed by interpolating the GPT latents, so a faster voice costs
# nothing to synthesise but shortens every answer. TTS_SPEED above only reaches
# the VITS fallback.
XTTS_SPEED = float(os.environ.get("JOULIE_XTTS_SPEED", "1.2"))

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

KNOWLEDGE_BASE_PATH = os.environ.get("JOULIE_KB_PATH", str(_repo_root / "knowledge_base"))
CHROMA_PATH = os.environ.get("JOULIE_CHROMA_PATH", str(_repo_root / "chroma_db"))
CHROMA_COLLECTION = os.environ.get("JOULIE_CHROMA_COLLECTION", "joulie_kb")
EMBED_MODEL = os.environ.get("JOULIE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
# Every retrieved chunk is prefilled on each turn; at k=6 the prompt reached
# ~5.8k chars and cost ~1.8s to first token. k=4 keeps the authoritative/advocacy
# mix format_context depends on at roughly half the prefill.
RAG_TOP_K = int(os.environ.get("JOULIE_RAG_TOP_K", "4"))
RAG_DISTANCE_THRESHOLD = float(os.environ.get("JOULIE_RAG_DISTANCE_THRESHOLD", "0.7"))
RAG_ENABLED = os.environ.get("JOULIE_RAG_ENABLED", "1") not in ("0", "false", "no")

GREETING = "Hi, I'm Joulie. How can I help?"

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
