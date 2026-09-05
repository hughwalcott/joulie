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