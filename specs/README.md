# Project Brief
Combine a Mac Mini (with M4 chip) and open source LLM to develop a battery-powered agent that we can take to an electrification expo so it can respond factually to questions about business or commercial electrification in New Zealand. 

## Why this project exists
Joulie, is an energy efficiency and energy intelligent agent that speaks kiwi and is entheastically helping home and business owners tansition their energy use to clean renewable energy, ensuring people can both save money and help the environment. 

### Maori data sovereignty principles: 
- Rangatiratanga (Authority): We aim to exercise control over agent's compute and data ecosystems, from knowldge interface down to silicon.
- Whakapapa (Relationships): We aim to choose our own knowledge base based on trusted authories, genealogy and heritage.
- Kotahitanga (Collective Benefit): Our agent will be designed to provide benefits to individual and collectives, supporting clean energy transitions for people's homes and businesses.
- Manaakitanga (Reciprocity): We aim to give back to our communities, preventing harm to our whenua and supporting free  and informed consent to the energy transition movement.
- Kaitiakitanga (Guardianship): Our agent and it's data will be kept within Aoteroa New Zealand, ensuring it is managed responsibly as a resource aligned to tikanga (cultural protocols) and mātauranga (knowledge). 

## Current scope
### Speach to Text:
- Ability to capture audio from either a Macbook inbuilt microphone (devtest), or Mac Mini's USB-C connected microphone (production). 
- Ability to convert Speach to Text (STT) for request processing. 

### Request Processing:
- Ability to detect the language spoken from the converted audio so as to contimue conversation in the spoken language
- Ability to agentic processing of the request using various large language models optimised for a MacMini with M4 chip architecture. 
- Ability to apply Retrival Augumented Generation (RAG) to the inference.
- Ability to encode and store curated New Zealand electrification documents for the agent knowledge base. 

### Text to Speach
- Ability to convert agenticly processed Text to Speach (TTS) styled to a broard kiwi audience and the Jourlie persona
- Ability to stream the audio to either a Macbook inbuilt speaker (devtest), or Mac Mini's USB-C connected speaker (production)

### User Interface
- Ability to active the Joulie agent by turning on the microphone or the spacebar is press. 
- Ability to provide a text input field as a backup for users who prefer typing over the microphone.
- Ability to see both the STT ingested and TTS responded in a kiosk styled interface via a connected LCD display
- The user interface will present a disclaimer to users acknowledging that responses are informational and not guaranteed to be complete or accurate.
- Ability to direct follow-up questions to the team by email
- Ability to close a conversation, clearing the context memory when the mmicrophone is turned off or the spacebar is pressed. 

### Analytics: 
- Ability to summerise a Jourlie/human conversation for qualitative analysis.
- Ability to capture a statisfication score (0-5) on how helpful the information was for quantitative analysis.
- Ability to measure and log the duration and timestamps of each conversation.
- Ability to measure and log the time taken to respond to each spoken request. 
- Ability to estimate the energy used per conversation.

## Current design recommendations
- Compute hardware will be an Apple Mac Mini M4 with 24GB+ unified memory
- Whisper.cpp for STT
- Coqui.ai for TTS
- Ollama for the self hosted AI workflow and RAG
- LangChain for retrieval and generation pipeline
- ChromaDB for vectorised knowledge base
- Gradio for user interface (Chrome with --kiosk flag)

## Deployable Packaging
- All code to be managed within the Git repo: https://github.com/hughwalcott/joulie.git
- Define package dependencies in a requirements.txt file. 

## Useful References
