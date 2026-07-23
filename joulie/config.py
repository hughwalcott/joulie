import os
from pathlib import Path

_repo_root = Path(__file__).parent.parent

OLLAMA_URL = os.environ.get("JOULIE_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("JOULIE_OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M")

WHISPER_MODEL = os.environ.get("JOULIE_WHISPER_MODEL", "base")

TTS_MODEL = os.environ.get("JOULIE_TTS_MODEL", "tts_models/en/vctk/vits")
TTS_VOICE = os.environ.get("JOULIE_TTS_VOICE", "p306")
TTS_SPEED = float(os.environ.get("JOULIE_TTS_SPEED", "1.05"))

XTTS_MODEL = os.environ.get("JOULIE_XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
XTTS_REF_WAV = os.environ.get("JOULIE_XTTS_REF_WAV", str(_repo_root / "specs" / "kiwi voice-15s.wav"))
XTTS_LANGUAGE = os.environ.get("JOULIE_XTTS_LANGUAGE", "en")
XTTS_SAMPLE_RATE = 24000

GREETING_WAV = os.environ.get("JOULIE_GREETING_WAV", str(_repo_root / "assets" / "greeting.wav"))

SAMPLE_RATE = 16000

KNOWLEDGE_BASE_PATH = os.environ.get("JOULIE_KB_PATH", str(_repo_root / "knowledge_base"))
CHROMA_PATH = os.environ.get("JOULIE_CHROMA_PATH", str(_repo_root / "chroma_db"))
CHROMA_COLLECTION = os.environ.get("JOULIE_CHROMA_COLLECTION", "joulie_kb")
EMBED_MODEL = os.environ.get("JOULIE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RAG_TOP_K = int(os.environ.get("JOULIE_RAG_TOP_K", "6"))
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
