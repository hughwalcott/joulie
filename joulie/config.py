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

GREETING_WAV = os.environ.get("JOULIE_GREETING_WAV", str(_repo_root / "resources" / "greeting.wav"))

SAMPLE_RATE = 16000

CHROMA_PATH = os.environ.get("JOULIE_CHROMA_PATH", str(_repo_root / "chroma_db"))
CHROMA_COLLECTION = os.environ.get("JOULIE_CHROMA_COLLECTION", "joulie_kb")
EMBED_MODEL = os.environ.get("JOULIE_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RAG_TOP_K = int(os.environ.get("JOULIE_RAG_TOP_K", "5"))
RAG_DISTANCE_THRESHOLD = float(os.environ.get("JOULIE_RAG_DISTANCE_THRESHOLD", "0.7"))
RAG_ENABLED = os.environ.get("JOULIE_RAG_ENABLED", "1") not in ("0", "false", "no")

GREETING = (
    "Hi, I'm Joulie. I share information about electrifying homes and "
    "businesses in New Zealand. My answers are informational and may be incomplete. "
    "For decisions, please consult a qualified professional. How can I help?"
)

SYSTEM_PROMPT = (
    "You are Joulie, a friendly New Zealand electrification advisor. "
    "Speak in plain, warm English. Keep answers short — two or three sentences "
    "for a spoken reply. Never recommend specific brands. Never give safety-critical "
    "instructions; if asked about an electrical hazard, tell the person to stop and "
    "call a registered electrician or emergency services. If you don't know, say so "
    "and offer to take a message for the Electrify the Hutt team."
)
