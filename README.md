# joulie
Joulie is a sovereign AI assistant for Electrifying Aotearoa
`Joulie stands for 'Just Offering Useful Local Ideas for Electrification'`

# Background
The project has been created by Hugh Walcott of Electrify the Hutt in support for Hutt City Council's objectives of reducing emissions and accelerating the clean energy transition in our community.

The intent is that Joulie becomes a battery-powered, standalone AI Advisory Agent that provides trusted, unbiased information to New Zealand residents and business owners considering the electrification of their homes and commercial premises. The agent will address a significant gap in the availability of accessible, credible, and conflict-of-interest-free electrification advice.

By leveraging an Apple Mac Mini M4, open-source large language models, and Retrieval Augmented Generation (RAG) technology, the project will build a curated knowledge base of verified New Zealand information and make it available through a conversational voice-and-text interface. The system is designed to operate fully offline, making it ideal for community expos, market stalls, and public events — as well as being embedded in a publicly accessible website.

# Installation
Joulie has been developed to be deloyablable and runnable as a phyton container, first clone the repository 
````
git clone https://github.com/hughwalcott/joulie.git
cd joulie 
```` 
Creat the virtual environment: 
```` 
python -m venv .venv
```` 
Activate the VM and Intall Dependencies: 
```` 
source .venv/bin/activate
pip install -r requirements.txt
```` 
`faster-whisper` pulls in `av` (PyAV), whose prebuilt wheel bundles its own
copy of FFmpeg. `torchcodec` (used by `torchaudio` to load XTTS's reference
wav) links against the system FFmpeg instead, so having both installed
duplicate-loads FFmpeg into the same process and macOS logs an `objc[...]:
Class AVFFrameReceiver is implemented in both ...` warning at startup —
harmless, but rebuild `av` from source against the same FFmpeg to get rid of
it and the ~20MB of duplicated libraries:
````
brew install ffmpeg pkg-config
PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig" pip install --no-binary av --force-reinstall --no-deps "av>=11"
````
Configure and run: 
```` 
python main.py
````
# Options: 
To run in kiosk mode: 
```` 
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --kiosk http://127.0.0.1:7860
````
Rerender the greeting / welcome message with defined speed.
````
 --render-greeting --speed 1.2 
 ````
 Test the generated greeting message:
 ````
 afplay assets/greeting.wav 
 ````
 Manually rebuild the knowledge base, specify chunk sizes?
 ````
 ingest.py --rebuild
 ````

## Dev kiosk controls
The local dev kiosk stands in for the production handset using your keyboard:
- **SPACE** (first press) — pick up the handset; Joulie greets you.
- **SPACE** (press and hold) — record an utterance; release to send.
- **ESC** — hang up and clear the conversation context.
- **Q** — quit.

You need a running [Ollama](https://ollama.com) instance with a model pulled. Defaults to `qwen2.5:14b-instruct-q4_K_M`; override with the `JOULIE_OLLAMA_MODEL` environment variable.

```
ollama pull qwen2.5:14b-instruct-q4_K_M
```

The model choice is measured, not assumed — see `evals/` for the question-bank harness and `evals/report.html` for the comparison against `llama3.2:3b` and `qwen3:14b`.

## Conversation history and retrieved context
Each turn's retrieved context rides on that turn's own user message and is **not** kept in
history (`JOULIE_LLM_RAG_PLACEMENT`, default `question`; `system` restores the old shape so
the two stay A/B-able). Ollama collates every `role: "system"` message into a single block
at the *top* of the rendered prompt, so sending context as a system message inserted ~560
tokens in front of the entire conversation on every turn and broke the KV prefix each time
— 3.3→6.7s of prefill against a flat 3.4s once the block moved onto the question. See
`scripts/isolate_ragplacement.py` and `logs/latency-analysis.md`.

With context out of history a completed turn costs only its question and answer (~140 tokens
at a typical reply length, ~260 at the longest measured), so `Agent` keeps up to
`JOULIE_LLM_MAX_HISTORY_TURNS` (default `16`) completed turns and cuts back to
`JOULIE_LLM_HISTORY_TRIM_TO` (default `8`) in one block once it exceeds that. A trim
re-prefills everything after the system prompt (~10s at this model's ~185 tok/s), so the cap
is a backstop for an unusually long visit rather than a working dial — a normal 10-15 turn
visit never reaches it, and `SessionCore.end_session()` resets history per visitor. Set the
cap to `0` to disable trimming entirely — at the default cap the first trim lands at turn 18.
`JOULIE_LLM_NUM_CTX` (default `6144`) has to stay above roughly `260 * cap + 1300` tokens, or
Ollama silently drops messages off the front and breaks the prefix by another route: a prompt
at the 16-turn cap measures ~3.2k tokens with typical replies and ~5.3k with the longest
measured, so `4096` would overflow a talkative visit.

What this trades away: a follow-up question sees the previous answers but no longer the
chunks behind them. `evals/followups.py` is the probe for that — `evals/run_qbank.py` gives
every question a fresh `Agent`, so it cannot see it.

## Per-turn and per-conversation performance metrics
Every turn's latency (STT, LLM time-to-first-token, TTS synth/RTF per chunk) and,
where available, GPU/CPU power draw, GPU clock frequency + active/idle residency,
and thermal-pressure state are written to `logs/sessions/<session_id>.jsonl`; a
roll-up `SessionSummary` (avg/max latency, whether any turn ran under thermal
throttling) is written to `logs/sessions/<session_id>_summary.json` when the
conversation ends. See `joulie/metrics.py` and `joulie/power.py`.

GPU frequency/residency exists to tell apart three things a power-draw number
alone can't distinguish: the GPU doing more real work (residency up, frequency
steady), the GPU throttled (frequency down, residency up to compensate for doing
the same work more slowly), and something other than Joulie's own turn keeping
the GPU busy (residency up independent of that turn's actual workload).

Each turn also records what was actually sent to Ollama: `prompt_chars` (total
size of the request), `rag_chunk_count`/`rag_context_chars` (what retrieval
added), and `history_turns` (how many turns survived the cap in
`JOULIE_LLM_MAX_HISTORY_TURNS` and made it into this request). This exists to
tell "turn position" apart from "input size" as the explanation for a latency
change — the cap bounds `history_turns`, but content-dependent RAG retrieval
can still make `prompt_chars` vary turn to turn even once history is flat.

Power/thermal capture uses `sudo powermetrics` running in the background for the
kiosk's lifetime. It needs a one-time, scoped passwordless-sudo entry on the kiosk
account — without it, `PowerSampler` disables itself automatically (no password
prompt, no hang) and turn metrics simply come back without power/thermal fields:

```
sudo visudo -f /etc/sudoers.d/joulie-powermetrics
```
```
<kiosk-username> ALL=(root) NOPASSWD: /usr/bin/powermetrics
```

Set `JOULIE_POWER_SAMPLING_ENABLED=0` to disable power sampling entirely, or
`JOULIE_METRICS_ENABLED=0` to disable all metrics capture.