# Joulie — Scenarios

Narrative user journeys that illustrate the Jobs To Be Done from [scope.md](scope.md). Each scenario is written as a short story so the team can walk through Joulie's behaviour from the perspective of a real person. The first set covers the **happy paths** for each persona; the second set **stresses the requirements** with awkward, edge, or failure conditions.

---

## A. Representative Scenarios

### A1. Mere at the Lower Hutt sustainability expo *(JTBD-01)*
Mere, a homeowner in Naenae, wanders past the Electrify the Hutt stall on a Saturday morning. She sees the Joulie kiosk on the table with a sign that says "Ask me about going electric." She picks up the handset, hears Joulie's short spoken disclaimer, and says, "My gas hot water cylinder is dying — what should I replace it with?" Joulie's Kiwi voice responds with a plain-language summary of heat-pump hot water versus resistive electric, and mentions typical running-cost differences for a household her size. She thanks Joulie, hangs the handset back on its cradle, and the kiosk resets for the next person.

### A2. Te Rangi runs a small panel-beating business *(JTBD-02)*
Te Rangi owns a workshop in Seaview and is tired of his LPG bill. At a chamber-of-commerce evening he asks Joulie, "What are the options for getting rid of gas in a panel-beating shop?" Joulie talks him through electric spray-booth heating, industrial heat pumps, and points him at commercial-scale considerations such as three-phase supply. It cites two NZ guidance documents on screen. Te Rangi takes a photo of the citations so he can show his electrician.

### A3. Aroha asks in te reo Māori *(JTBD-03)*
Aroha walks up, picks up the handset, and asks Joulie a question in te reo. Joulie detects the language, responds in te reo with the same factual content it would have offered in English, and continues the conversation in te reo until Aroha hangs up.

### A4. Question beyond Joulie's scope *(JTBD-04)*
Priya asks, "Can I get the council EV-charger subsidy if I'm renting?" Joulie says it doesn't have a confident answer on current subsidy eligibility and offers to record a spoken message for the Electrify the Hutt team. Priya says "yes please", speaks her question and a contact phone number, Joulie reads it back to confirm, and the recording is queued for the team to follow up.

### A5. End of conversation, clean slate *(JTBD-05)*
After Mere finishes (A1), the next visitor — a teenager curious about EVs — steps up. He picks up the handset and asks his question. Joulie has no memory of Mere's hot-water conversation; the context is fresh.

### A6. Setting up at a remote venue *(JTBD-06)*
Hemi, an Electrify the Hutt volunteer, takes Joulie to a community day at Eastbourne Hall, which has unreliable Wi-Fi. He plugs the Mac Mini into the portable battery, attaches the kiosk display, microphone, speaker, and handset, and switches it on. Joulie boots, loads its local models, and is ready to take questions — no network needed.

### A7. Single-action activation *(JTBD-07)*
A first-time visitor stares at the kiosk, unsure how to begin. A short on-screen prompt and a glowing light next to the handset say "Pick me up to talk to Joulie." She lifts the handset, hears a short greeting and disclaimer, talks, and gets an answer. When she's done, she hangs the handset back on the cradle and the conversation closes. No keyboard, no menus.

### A8. End-of-day operator review *(JTBD-08)*
At the end of the expo, Hemi opens the analytics view on a separate laptop. He sees 47 conversations, an average satisfaction score of 4.2/5, median response latency of 3.1 seconds, total runtime of 6 hours, and an estimated energy use of 180 Wh. He exports a CSV summary for the council report.

### A9. Spoken disclaimer at the start of every conversation *(JTBD-09)*
Every time a visitor picks up the handset, Joulie opens with: *"Kia ora — I'm Joulie. I share information about electrifying homes and businesses in Aotearoa. My answers are informational and may be incomplete. For decisions, please consult a qualified professional."* The same wording is also shown on the display for anyone who would rather read it.

### A10. Curator adds new EECA guidance *(JTBD-10, JTBD-11)*
A new EECA guide on home electrification is published. Hugh, the knowledge curator, drops the PDF into the ingestion folder and tags it with `source: EECA`, `trustTier: 1`, `publishedAt: 2026-05-20`. The next time Joulie boots, the document is chunked, embedded, and available for retrieval, with its provenance preserved so future citations point back to EECA. (Curator workflow is off-kiosk and uses a normal computer.)

### A11. Developer clones and runs *(JTBD-12)*
A new contributor clones the repo, runs `python -m venv .venv`, activates it, installs `requirements.txt`, and runs the entry-point. Joulie launches locally and a developer harness lets them speak to it through their laptop microphone within seconds.

### A12. Regression caught by tests *(JTBD-13)*
A model swap doubles the median response latency in CI. The latency test fails, the PR is blocked, and the maintainer investigates before merging.

---

## B. Stress Scenarios

These journeys probe the edges of the requirements — where Joulie must degrade gracefully, refuse, or escalate.

### B1. The off-topic visitor
A man at the expo asks Joulie, "Who's going to win the Bledisloe Cup?" Joulie politely declines, explains it only answers questions about electrification in Aotearoa, and offers an example of what it *can* help with. The conversation stays friendly; he laughs and asks a real question about EV charging.

### B2. The sales-trap question
A vendor approaches and asks, "Which brand of heat pump should I buy?" Joulie does **not** name brands. It explains the criteria that matter (capacity, COP, noise rating, installer accreditation) and points to independent NZ guidance. The vendor leaves frustrated; this is the correct outcome.

### B3. The leading or loaded question
A visitor asks, "Isn't gas heating actually cheaper than electric?" Joulie does not parrot the premise. It gives the honest, citation-backed picture — including where gas may be cheaper in narrow cases and where electric wins on a whole-of-life basis — without taking an advocacy tone.

### B4. The medical or safety-critical question
Someone asks, "My switchboard is sparking — should I turn it off?" Joulie refuses to give a safety-critical instruction, tells the person to stop using the switchboard and call a registered electrician or emergency services, and surfaces the disclaimer prominently. It does **not** try to diagnose.

### B5. Power cut mid-conversation
Halfway through Te Rangi's question, the venue loses mains power. The battery takes over seamlessly; Joulie continues the response. Hemi notices the battery indicator drop and starts watching it.

### B6. Battery low warning
The battery hits 15%. The operator dashboard shows a warning; the kiosk continues serving visitors but pings Hemi to plug in or wrap up.

### B7. Microphone failure
The USB-C microphone (built into the handset) is bumped loose. Joulie detects no audio input, ends the current conversation gracefully with a spoken "Sorry — I can't hear you, please let a volunteer know," and the on-screen prompt shows a clear "Microphone unavailable" banner so Hemi can fix it. Because the system is voice-only, the kiosk is taken out of service until the hardware is reconnected — there is no text fallback while in kiosk mode.

### B8. Code-switching speaker
Aroha starts in te reo, then switches mid-sentence to English ("…engari, what about the upfront cost?"). Joulie keeps up, responds in the dominant language of the latest turn, and doesn't restart the conversation.

### B9. Two people talking at once
A couple both speak over each other into the microphone. Joulie transcribes what it can, asks a single clarifying question ("Sorry, I missed that — could one of you ask again?"), and continues.

### B10. Long rambling enquiry
A retiree spends 90 seconds describing his whole house, every appliance, and his late wife's preferences before asking a question. Joulie processes the full utterance, extracts the actual question, and answers it without complaining about the length.

### B11. The "gotcha" hallucination probe
A tech-savvy visitor asks, "What's the current Hutt City Council rebate for induction cooktops?" If the knowledge base has no document on this, Joulie says so explicitly — "I don't have a verified source for that" — and offers to forward the question. It does **not** invent a number.

### B12. Document conflicts
Two trusted documents disagree on the typical payback period for rooftop solar in Wellington. Joulie surfaces both ranges, attributes each to its source, and explains the difference (different assumptions about export pricing) rather than picking one silently.

### B13. Privacy probe
A visitor jokes, "What did the last person ask you?" Joulie confirms it has no memory of previous conversations and that nothing personal is retained.

### B14. Knowledge base ingestion of an untrusted source
The curator accidentally drops a blog post with no provenance into the ingestion folder. The pipeline refuses to index it because `source` and `trustTier` are missing, and logs the rejection for the curator to review.

### B15. After-hours follow-up backlog
The Electrify the Hutt team returns Monday morning to 23 recorded follow-up messages from the weekend expo. Each contains the audio of the original question, an auto-generated transcript, the timestamp, and (if the visitor offered one) a spoken contact phone number — enough to follow up without further chasing.

### B16. Energy budget overrun
A particularly busy hour pushes estimated energy use above the model's expected envelope. The analytics record flags it, so the team can investigate whether a model swap or a longer-than-expected RAG retrieval was responsible.
