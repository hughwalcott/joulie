import threading
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

import gradio as gr

from joulie import config
from joulie.handset import attach
from joulie.session_core import SessionCore
from joulie.tools import REGISTRY, qr_path


_FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
_QR_DIR = Path(__file__).parent.parent / "assets" / "qrcodes"


def _font_face_css() -> str:
    """Build @font-face blocks pointing at Gradio's /file= static handler for
    each Montserrat weight. Self-hosted so the kiosk works offline."""
    # 500 is deliberately absent: the type scale in _CSS uses 400/600/700 only,
    # so shipping it would be a font fetch nothing renders.
    weights = [400, 600, 700]
    blocks = []
    for w in weights:
        font_path = _FONTS_DIR / f"Montserrat-{w}.woff2"
        # Gradio 4.x serves allowed_paths at /file=<absolute-path>.
        url = f"/file={font_path}"
        blocks.append(
            f"@font-face {{ font-family: 'Montserrat'; font-style: normal; "
            f"font-weight: {w}; font-display: swap; "
            f"src: url('{url}') format('woff2'); }}"
        )
    return "\n".join(blocks)

_CSS = """
:root {
  --joulie-bg:      #212529;
  --joulie-panel:   #2b3036;
  --joulie-border:  #495057;
  --joulie-accent:  #FFC72C;
  --joulie-text:    #F8F9FA;
  --joulie-record:  #E62E2E;
  /* Was hardcoded in the status and mic dot rules; the state-frame and pill
   * fills below need it in a dozen more places. */
  --joulie-live:    #4ADE80;
  /* Standby. Deliberately NOT --joulie-panel: at the panel colour the status
   * pill was the same fill as every card and button on screen, which made a
   * read-only indicator look pressable. The blue cast separates it from the
   * neutral greys without adding a sixth hue. */
  --joulie-standby:        #39434F;
  --joulie-standby-border: #5A6B80;
}

/* Type scale. Six steps, and every font-size in this sheet resolves to one of
 * them — the sheet previously carried eight unrelated sizes plus one control
 * with no size at all, which is why the header read as three of the same thing.
 * Sized for a 960x640 panel read at arm's length and glanced at from further,
 * so the floor is 12px and body copy sits at 14-18px. */
:root {
  --fs-xs:  12px;
  --fs-sm:  14px;
  --fs-md:  16px;
  --fs-lg:  18px;
  --fs-xl:  22px;
  --fs-2xl: 30px;
  --fw-body: 400;
  --fw-semi: 600;
  --fw-bold: 700;
  --lh-tight: 1.25;
  --lh-snug:  1.4;
  --lh-body:  1.5;
}

/* Kiosk geometry. The target screen is a 960x640 touch panel, so the page must
 * fill it exactly and never scroll — a visitor cannot be expected to discover
 * that the QR code is below the fold. Everything that can grow (the answer, the
 * source list) scrolls inside its own pane instead.
 *
 * The body is sized by flex rather than a calc() against a measured header
 * height: Gradio's whole wrapper chain (.main > .wrap > .contain > the column)
 * is already display:flex, so the header takes what it needs and the body takes
 * the rest. That holds at any resolution, and survives the disclaimer wrapping
 * onto another line. */
:root {
  --joulie-pad: 10px;
}

html, body, gradio-app {
  height: 100%;
  overflow: hidden;
}
.gradio-container {
  background: var(--joulie-bg) !important;
  color: var(--joulie-text) !important;
  height: 100vh !important;
  max-width: 100% !important;
  width: 100% !important;
  margin: 0 !important;
  padding: var(--joulie-pad) !important;
  overflow: hidden !important;
}
/* Gradio's "Built with Gradio" footer is dead space on a kiosk. */
footer { display: none !important; }

/* Let the wrapper chain give its height through to the body row. Scoped with
 * child combinators from .gradio-container — .wrap and .contain are generic
 * Gradio class names that also appear inside individual components. */
.gradio-container > .main,
.gradio-container > .main > .wrap,
.gradio-container > .main > .wrap > .contain,
.gradio-container > .main > .wrap > .contain > div {
  min-height: 0 !important;
  flex: 1 1 auto !important;
}
#joulie-titles, #joulie-header { flex: 0 0 auto !important; }

/* Two-column body: transcript left, QR + sources right, so the tool panel is
 * beside the answer rather than under it. */
#joulie-main {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  flex-wrap: nowrap !important;
  gap: 10px !important;
  align-items: stretch !important;
}
#col-left, #col-right {
  height: 100%;
  min-width: 0 !important;
  overflow: hidden;
}
#col-right {
  overflow-y: auto;
}
/* The answer takes whatever the question leaves and scrolls on its own. */
#col-left { display: flex !important; flex-direction: column !important; }
/* Gradio groups consecutive inputs into a <form>, so the transcript boxes are
 * grandchildren of the column, not children — without this the answer box never
 * grows and the column ends in dead space. */
#col-left > .form {
  /* !important throughout: Gradio's own .form rule sets flex with !important,
     so specificity alone does not win here. */
  flex: 1 1 auto !important;
  min-height: 0 !important;
  display: flex !important;
  flex-direction: column !important;
}
#visitor-box, #record-btn { flex: 0 0 auto; }
#joulie-box {
  flex: 1 1 auto;
  min-height: 0;
  display: flex !important;
  flex-direction: column !important;
}
#joulie-box .wrap, #joulie-box > label { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }
#col-left textarea { resize: none !important; }
#joulie-box textarea {
  flex: 1 1 auto;
  height: 100% !important;
  overflow-y: auto !important;
}
.gradio-container *, body, button, textarea, input {
  font-family: 'Montserrat', -apple-system, "Inter", system-ui, sans-serif !important;
}

#joulie-title {
  font-size: var(--fs-2xl);
  font-weight: var(--fw-bold);
  line-height: var(--lh-tight);
  color: var(--joulie-accent);
  padding: 0 2px 2px 2px;
}
#joulie-disclaimer {
  font-size: var(--fs-sm);
  font-weight: var(--fw-body);
  color: var(--joulie-text);
  opacity: 0.7;
  margin-bottom: 0;
  line-height: var(--lh-snug);
  padding: 0 2px;
}

.gr-box, .gr-form, .gr-panel, .form, .block {
  background: var(--joulie-panel) !important;
  border: 1px solid var(--joulie-border) !important;
  border-radius: 12px !important;
}
textarea, .gr-textbox, input[type="text"] {
  background: var(--joulie-bg) !important;
  color: var(--joulie-text) !important;
  border: 1px solid var(--joulie-border) !important;
  border-radius: 8px !important;
  font-size: var(--fs-lg) !important;
  line-height: var(--lh-body) !important;
}
/* The answer outranks the question: it is what a visitor reads back, and the
 * box scrolls internally anyway, so the larger size costs no content. */
#joulie-box textarea {
  font-size: var(--fs-xl) !important;
}
#col-left textarea::placeholder {
  color: var(--joulie-text) !important;
  opacity: 0.4 !important;
}
label span, .gr-checkbox-group label {
  color: var(--joulie-text) !important;
  font-size: var(--fs-md) !important;
  font-weight: var(--fw-semi);
}

/* Session button — the row's only ACTION, so it is the only rectangular thing
 * in it (the two readouts beside it are a full pill and a small square chip).
 * Shape, not colour, is what separates the three at a glance. */
.joulie-session-btn > button {
  background: var(--joulie-accent) !important;
  color: var(--joulie-bg) !important;
  border: none !important;
  height: 48px !important;
  border-radius: 10px !important;
  font-size: var(--fs-md) !important;
  font-weight: var(--fw-bold) !important;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  transition: opacity 120ms ease, background 120ms ease !important;
}
/* Kiosk mode merges Stop Talking into this button, so the colour has to say
 * which job a press would do: gold ends the visit, red cuts Joulie off. */
.joulie-session-btn.stop > button {
  background: var(--joulie-record) !important;
  color: var(--joulie-text) !important;
}
.joulie-session-btn button:disabled {
  opacity: 0.4 !important;
  cursor: not-allowed !important;
}

/* Big record toggle. Instant colour swap when 'recording' class is applied. */
.joulie-record-btn > button {
  width: 100% !important;
  height: 96px !important;
  border-radius: 48px !important;
  background: var(--joulie-accent) !important;
  color: var(--joulie-bg) !important;
  font-size: var(--fs-xl) !important;
  font-weight: var(--fw-bold) !important;
  border: none !important;
  cursor: pointer !important;
  margin-top: 12px !important;
  transition: background 60ms ease, box-shadow 60ms ease, transform 60ms ease !important;
}
.joulie-record-btn.recording > button {
  background: var(--joulie-record) !important;
  color: var(--joulie-text) !important;
  box-shadow: 0 0 0 4px rgba(230,46,46,0.25) !important;
  transform: scale(0.98);
}
.joulie-record-btn.working > button {
  background: var(--joulie-border) !important;
  color: var(--joulie-text) !important;
  cursor: wait !important;
}
.joulie-record-btn button:disabled {
  opacity: 0.5 !important;
  cursor: not-allowed !important;
}

/* Tool panel — single HTML block with QR + caption. Rendered inside a
 * gr.HTML so hiding is controlled by Gradio's visible=False on the component. */
#tool-panel {
  margin-top: 0 !important;
  padding: 12px !important;
  background: var(--joulie-panel) !important;
  border: 1px solid var(--joulie-border) !important;
  border-radius: 12px !important;
}
#tool-panel-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.tool-qr {
  width: 132px;
  height: 132px;
  background: var(--joulie-text);
  padding: 8px;
  border-radius: 8px;
  flex-shrink: 0;
  display: block;
}
#tool-caption {
  color: var(--joulie-text);
  flex: 1;
}
#tool-caption .tool-name {
  color: var(--joulie-accent);
  font-size: var(--fs-lg);
  font-weight: var(--fw-bold);
  line-height: var(--lh-tight);
  margin-bottom: 5px;
}
#tool-caption .tool-desc {
  font-size: var(--fs-sm);
  line-height: var(--lh-snug);
  margin-bottom: 6px;
}
#tool-caption .tool-url {
  font-size: var(--fs-sm);
  opacity: 0.7;
  font-weight: var(--fw-semi);
}

/* The header row: one dominant state readout, one subordinate device readout,
 * one action, in that order left to right. The action is pushed to the far edge
 * so position also separates "what Joulie is doing" from "what I can press". */
#joulie-header {
  align-items: center !important;
}
#joulie-header > *:last-child {
  margin-left: auto !important;
  flex: 0 0 auto !important;
}

/* Status pill — the row's dominant element. The whole pill carries the state,
 * not just the dot: a 9px dot changing colour is invisible from more than about
 * a metre, and this screen is read over people's shoulders. Height is pinned at
 * 48px across every state so the row can never reflow — see the min-height note
 * below for what happens when this block is allowed to resize. */
#status-wrapper {
  display: flex !important;
  align-items: center !important;
}
/* While an event is in flight Gradio adds `pending`/`min` to a component's
 * children, and that styling carries a 96px min-height — which made this block
 * jump 40px -> 98px on every poll tick. The pill inside is a fixed 34px, so
 * nothing in here should ever reserve height. */
#status-wrapper,
#status-wrapper > div,
#status-wrapper .prose {
  min-height: 0 !important;
}
#joulie-status {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 48px;
  padding: 0 20px;
  border-radius: 24px;
  font-size: var(--fs-xl);
  font-weight: var(--fw-bold);
  line-height: var(--lh-tight);
  color: var(--joulie-text);
  background: var(--joulie-panel);
  border: 1px solid var(--joulie-border);
  white-space: nowrap;
  box-sizing: border-box;
  margin: 3px;
  transition: background 160ms ease, border-color 160ms ease;
}
#joulie-status::before {
  content: "";
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--joulie-border);
  flex-shrink: 0;
}
/* Full opacity rather than the old 0.7: the blue-grey is what sets standby apart
 * now, and fading it would put it back to reading as a dimmed button. */
#joulie-status[data-state="idle"] {
  background: var(--joulie-standby);
  border-color: var(--joulie-standby-border);
}
#joulie-status[data-state="idle"]::before {
  background: var(--joulie-standby-border);
}
#joulie-status[data-state="listening"] {
  background: rgba(74, 222, 128, 0.14);
  border-color: var(--joulie-live);
}
#joulie-status[data-state="recording"] {
  background: rgba(74, 222, 128, 0.22);
  border-color: var(--joulie-live);
}
#joulie-status[data-state="transcribing"],
#joulie-status[data-state="thinking"] {
  background: rgba(255, 199, 44, 0.16);
  border-color: var(--joulie-accent);
}
#joulie-status[data-state="speaking"] {
  background: rgba(255, 199, 44, 0.22);
  border-color: var(--joulie-accent);
}
#joulie-status[data-state="listening"]::before,
#joulie-status[data-state="recording"]::before { background: var(--joulie-live); }
#joulie-status[data-state="speaking"]::before  { background: var(--joulie-record); }
#joulie-status[data-state="transcribing"]::before,
#joulie-status[data-state="thinking"]::before  { background: var(--joulie-accent); }
/* Pulse the dot while capture / synthesis is in flight. */
#joulie-status[data-state="recording"]::before,
#joulie-status[data-state="speaking"]::before,
#joulie-status[data-state="thinking"]::before,
#joulie-status[data-state="transcribing"]::before {
  animation: joulie-pulse 1.2s ease-in-out infinite;
}
@keyframes joulie-pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.35; }
}

/* State frame — the whole screen becomes the indicator, which is the only thing
 * on a 960px panel that reads from across a room. Keyed off the data-state the
 * status pill already publishes, via :has(), so it costs no extra DOM and no
 * extra repaint: the ring is CSS reacting to an attribute the poller was going
 * to write anyway. Chrome-only, and the kiosk is Chrome --kiosk; elsewhere it
 * simply renders no ring. */
.gradio-container:has(#joulie-status[data-state="listening"]) {
  box-shadow: inset 0 0 0 2px var(--joulie-live) !important;
}
.gradio-container:has(#joulie-status[data-state="recording"]) {
  animation: joulie-frame-live 2s ease-in-out infinite;
}
.gradio-container:has(#joulie-status[data-state="transcribing"]),
.gradio-container:has(#joulie-status[data-state="thinking"]) {
  animation: joulie-frame-work 2s ease-in-out infinite;
}
.gradio-container:has(#joulie-status[data-state="speaking"]) {
  box-shadow: inset 0 0 0 4px var(--joulie-accent) !important;
}
/* The ring itself breathes, not the container's opacity — animating opacity here
 * would fade the entire interface in and out. !important is not available inside
 * @keyframes, but an animation already outranks a normal author declaration, so
 * these win over Gradio's theme the same way the two rules above do. */
@keyframes joulie-frame-live {
  0%, 100% { box-shadow: inset 0 0 0 8px var(--joulie-live); }
  50%      { box-shadow: inset 0 0 0 8px rgba(74, 222, 128, 0.30); }
}
@keyframes joulie-frame-work {
  0%, 100% { box-shadow: inset 0 0 0 4px var(--joulie-accent); }
  50%      { box-shadow: inset 0 0 0 4px rgba(255, 199, 44, 0.30); }
}

/* Mic pill — mirrors the hardware mute LED on screen. The mic's own light is
 * the authoritative indicator (the firmware drives it and we cannot); this
 * exists so the mic and the UI can be watched together on one screen. */
#mic-wrapper,
#mic-wrapper > div,
#mic-wrapper .prose {
  min-height: 0 !important;
}
#mic-wrapper {
  display: flex !important;
  align-items: center !important;
}
/* Deliberately a different SHAPE from the status pill, not just a different
 * colour: small, square-cornered and outlined rather than filled, so it reads as
 * a device readout sitting beside the state — the two were previously identical
 * geometry and indistinguishable at a glance. */
#joulie-mic {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 32px;
  padding: 0 12px;
  border-radius: 8px;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semi);
  line-height: var(--lh-tight);
  color: var(--joulie-text);
  background: transparent;
  border: 1px solid var(--joulie-border);
  white-space: nowrap;
  box-sizing: border-box;
  margin: 3px;
}
#joulie-mic::before {
  content: "";
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--joulie-border);
  flex-shrink: 0;
}
/* Live keeps the outlined chip — the mic is doing something, so it holds its box.
 * Muted drops the border and the fill entirely: an outlined box at any opacity
 * still reads as a button, and a bare label with a dot cannot. The two states
 * therefore differ in shape, not just in brightness. */
#joulie-mic[data-state="live"] {
  opacity: 1;
  border-color: var(--joulie-live);
  background: rgba(74, 222, 128, 0.10);
}
#joulie-mic[data-state="live"]::before  { background: var(--joulie-live); }
#joulie-mic[data-state="muted"] {
  opacity: 0.6;
  border-color: transparent;
  background: transparent;
}
#joulie-mic[data-state="muted"]::before { background: var(--joulie-record); }

/* Sources panel — what retrieval put in front of the model, under the QR. */
#sources-panel {
  margin-top: 10px !important;
  padding: 10px 12px !important;
  background: var(--joulie-panel) !important;
  border: 1px solid var(--joulie-border) !important;
  border-radius: 12px !important;
}
#sources-panel .sources-head {
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  opacity: 0.6;
  margin-bottom: 6px;
}
#sources-panel .source-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: var(--fs-sm);
  line-height: var(--lh-body);
}
#sources-panel .source-pub { font-weight: var(--fw-semi); }
/* Stance is not decoration. Rewiring Aotearoa is an advocacy charity, not a
 * regulator, and the panel must never let the two read alike. */
#sources-panel .source-stance {
  font-size: var(--fs-xs);
  font-weight: var(--fw-semi);
  padding: 1px 6px;
  border-radius: 8px;
  white-space: nowrap;
}
#sources-panel .source-stance[data-stance="authoritative"] {
  background: rgba(74, 222, 128, 0.16);
  color: #86EFAC;
}
#sources-panel .source-stance[data-stance="advocacy"] {
  background: rgba(255, 199, 44, 0.16);
  color: var(--joulie-accent);
}
#sources-panel .source-stance[data-stance="vendor"] {
  background: rgba(125, 185, 232, 0.16);
  color: #93C5FD;
}
#sources-panel .source-stance[data-stance="reference"] {
  background: rgba(248, 249, 250, 0.10);
  opacity: 0.75;
}

/* Stage panel — the top of the right-hand column, which was blank in every
 * state but "answer finished". It carries the invitation while idle, the on-air
 * indicator while the mic is open, and the pipeline tracker while a turn runs. */
#stage-panel {
  margin-top: 0 !important;
  padding: 14px !important;
  background: var(--joulie-panel) !important;
  border: 1px solid var(--joulie-border) !important;
  border-radius: 12px !important;
  margin-bottom: 10px !important;
}
/* Same remedy as #status-wrapper: while an event is in flight Gradio adds
 * `pending`/`min` to a component's children and that styling carries a 96px
 * min-height, which is what once made the status pill jump 40px -> 98px on every
 * poll tick. This is the tallest block on a 640px screen, so it matters more. */
#stage-panel,
#stage-panel > div,
#stage-panel .prose {
  min-height: 0 !important;
}
/* Heights are pinned per variant rather than on the panel. #col-right is
 * overflow-y:auto and is NOT a flex container, so a panel that grows with its
 * content pushes the QR below the fold — the one thing the kiosk geometry must
 * never do. Budget: ~520px of column, less ~158px of QR panel and ~90px of
 * sources, leaves ~260px here. */
.stage-body {
  height: 224px;
  box-sizing: border-box;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
/* Once Joulie is talking the tracker has nothing left to report, so it shrinks
 * out of the QR's way. */
.stage-body.stage-compact {
  height: auto;
}

.stage-eyebrow {
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  opacity: 0.6;
  margin-bottom: 8px;
}
.stage-cta {
  font-size: var(--fs-xl);
  font-weight: var(--fw-bold);
  line-height: var(--lh-tight);
  color: var(--joulie-accent);
  margin-bottom: 14px;
  animation: joulie-pulse 3.2s ease-in-out infinite;
}
.stage-q {
  font-size: var(--fs-md);
  font-weight: var(--fw-body);
  line-height: var(--lh-snug);
  margin-bottom: 8px;
  padding-left: 14px;
  position: relative;
}
.stage-q::before {
  content: "“";
  position: absolute;
  left: 0;
  color: var(--joulie-accent);
  font-weight: var(--fw-bold);
}
/* Mid-session the prompt is a reminder, not an invitation — it should not pulse
 * for attention while the visitor is reading the answer they just got. */
.stage-body.stage-dim .stage-cta {
  animation: none;
  font-size: var(--fs-lg);
  margin-bottom: 0;
}

/* On-air indicator. A breathing halo, NOT a level meter: Recorder.mic_live is a
 * 0.5s boolean window and the poller runs at 0.4s, so animated bars would be
 * decoration pretending to be data about the visitor's voice. */
.stage-onair {
  align-items: center;
  justify-content: center;
  text-align: center;
}
.onair-disc {
  width: 104px;
  height: 104px;
  border-radius: 50%;
  border: 3px solid var(--joulie-live);
  background: rgba(74, 222, 128, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  /* Sizing a glyph used as a graphic, not type — the one font-size in this sheet
   * that is deliberately outside the scale. */
  font-size: 40px;
  line-height: 1;
  animation: joulie-halo 2s ease-in-out infinite;
  margin-bottom: 14px;
}
@keyframes joulie-halo {
  0%, 100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.45); }
  50%      { box-shadow: 0 0 0 18px rgba(74, 222, 128, 0); }
}
.onair-word {
  font-size: var(--fs-2xl);
  font-weight: var(--fw-bold);
  letter-spacing: 0.04em;
  color: var(--joulie-live);
  line-height: var(--lh-tight);
}
.onair-hint {
  font-size: var(--fs-sm);
  opacity: 0.7;
  margin-top: 4px;
}

/* Pipeline tracker. Four real milestones, each advanced by an actual TurnEvent,
 * so the progress it shows is progress that happened — no timer-driven bar that
 * reaches 95% and stalls. The motion within the active step is the indeterminate
 * half, and it is pure CSS: putting it in the value would make `stage` differ on
 * every poll tick and repaint this panel 2.5x a second. */
.stage-step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: var(--fs-md);
  line-height: var(--lh-tight);
  padding: 7px 0;
}
.stage-step .step-mark {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--joulie-border);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  box-sizing: border-box;
}
.stage-step .step-label { flex: 1 1 auto; }
.stage-step[data-step="pending"] { opacity: 0.45; }
.stage-step[data-step="done"] .step-mark {
  border-color: var(--joulie-live);
  background: var(--joulie-live);
  color: var(--joulie-bg);
}
.stage-step[data-step="active"] {
  font-weight: var(--fw-bold);
  color: var(--joulie-accent);
}
.stage-step[data-step="active"] .step-mark {
  border-color: var(--joulie-accent);
  background: var(--joulie-accent);
}
/* The rail only exists on the active row, and the sweep is what tells a visitor
 * the wait is alive rather than hung. */
.stage-step .step-rail {
  height: 3px;
  border-radius: 2px;
  flex: 0 0 90px;
  background: rgba(255, 199, 44, 0.18);
  overflow: hidden;
  visibility: hidden;
}
.stage-step[data-step="active"] .step-rail { visibility: visible; }
.stage-step .step-rail::after {
  content: "";
  display: block;
  width: 40%;
  height: 100%;
  border-radius: 2px;
  background: var(--joulie-accent);
  animation: joulie-sweep 1.4s ease-in-out infinite;
}
@keyframes joulie-sweep {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(250%); }
}
"""

# Visitor-facing wording for each pipeline state. The keys are also the CSS
# data-state values that colour the dot, so they stay as the pipeline names them
# — only the labels speak the kiosk's language. "listening" is the in-session
# rest state (mic muted, nothing being captured); "recording" is the mic actually
# hearing the visitor, which to them reads as Joulie listening.
_STATUS_LABELS = {
    "idle":         "Standby",
    "listening":    "Ready",
    "recording":    "Listening",
    "transcribing": "Transcribing",
    "thinking":     "Thinking",
    "speaking":     "Answering",
}


def _status_html(state: str) -> str:
    label = _STATUS_LABELS.get(state, state.title())
    return f'<div id="joulie-status" data-state="{state}">{label}</div>'


_STANCE_LABELS = {
    "authoritative": "Government",
    "advocacy": "Advocacy",
    "vendor": "Manufacturer",
    "reference": "Reference",
}


def _sources_html(sources) -> str:
    """Render the publishers retrieval surfaced for this answer.

    Headed "Sources consulted", never "Citations": these are what was placed in
    the prompt, which is not a claim about what the answer actually used. Each
    row carries its stance so an advocacy source cannot be mistaken for a
    regulator — the same split format_context enforces for the model.
    """
    rows = "".join(
        '<div class="source-row">'
        f'<span class="source-pub">{s.publisher}</span>'
        f'<span class="source-stance" data-stance="{s.stance}">'
        f'{_STANCE_LABELS.get(s.stance, s.stance.title())}</span>'
        "</div>"
        for s in sources
    )
    return f'<div class="sources-head">Sources consulted</div>{rows}'


# The tracker's milestones, in order, against the pipeline status that makes each
# one current. "heard" has no status of its own — it is complete the moment any
# event of this turn lands, which is what the relocated transcribing event does.
_STEPS = (
    ("heard", "Heard you"),
    ("transcribing", "Transcribing"),
    ("thinking", "Thinking"),
    ("speaking", "Answering"),
)


def _steps_html(stage: str) -> str:
    """Render the four pipeline milestones with the current one active.

    Everything before the active step is done, everything after is pending, so
    the tracker can only ever move forwards — it is reporting events that already
    happened rather than predicting a completion time.
    """
    current = max((i for i, (key, _) in enumerate(_STEPS) if key == stage), default=0)
    rows = []
    for index, (_, label) in enumerate(_STEPS):
        if index < current:
            state, mark = "done", "✓"
        elif index == current:
            state, mark = "active", ""
        else:
            state, mark = "pending", ""
        rows.append(
            f'<div class="stage-step" data-step="{state}">'
            f'<span class="step-mark">{mark}</span>'
            f'<span class="step-label">{label}</span>'
            '<span class="step-rail"></span>'
            "</div>"
        )
    return "".join(rows)


def _stage_html(stage: str, kiosk_mode: bool) -> str:
    """What the top of the right-hand column shows for this pipeline state.

    Takes a bare state token, never anything time-derived: the poller diffs
    UiState field by field, so a value carrying an elapsed count or a frame index
    would differ on every tick and repaint this block several times a second.
    All motion lives in _CSS keyframes instead.
    """
    if stage == "ready":
        # No example questions here, for two reasons: a visitor mid-session has
        # already shown they know what to ask, and this state is the one that
        # coexists with the QR panel and the sources — a full card alongside both
        # would overrun the column and push the QR below the fold.
        return (
            '<div class="stage-body stage-compact stage-dim">'
            f'<div class="stage-cta">{config.KIOSK_READY_CTA}</div></div>'
        )

    if stage == "attract":
        cta = config.KIOSK_ATTRACT_CTA if kiosk_mode else config.KIOSK_ATTRACT_CTA_BROWSER
        questions = "".join(
            f'<div class="stage-q">{q}</div>' for q in config.KIOSK_EXAMPLE_QUESTIONS
        )
        return (
            '<div class="stage-body">'
            f'<div class="stage-cta">{cta}</div>'
            '<div class="stage-eyebrow">Try asking</div>'
            f"{questions}</div>"
        )

    if stage == "listening":
        return (
            '<div class="stage-body stage-onair">'
            '<div class="onair-disc">🎤</div>'
            '<div class="onair-word">LISTENING</div>'
            '<div class="onair-hint">Speak now — take your time.</div>'
            "</div>"
        )

    if stage == "speaking":
        # Every milestone is behind us, so the tracker collapses to a single line
        # and gives the vertical room back to the QR panel below it.
        return (
            '<div class="stage-body stage-compact">'
            '<div class="stage-step" data-step="active">'
            '<span class="step-mark"></span>'
            '<span class="step-label">Answering</span>'
            '<span class="step-rail"></span>'
            "</div></div>"
        )

    return f'<div class="stage-body">{_steps_html(stage)}</div>'


def _mic_html(live: bool) -> str:
    """Mic mute state as a pill. Derived from the audio stream, not the HID
    report, so it stays honest even when the mute button can't be opened."""
    state = "live" if live else "muted"
    label = "Mic live" if live else "Mic muted"
    return f'<div id="joulie-mic" data-state="{state}">{label}</div>'


# gr.update() shorthands so the handler code below stays readable.
def _record_idle():
    return gr.update(value="🎤 Tap to speak", elem_classes=["joulie-record-btn"], interactive=True)

def _record_recording():
    return gr.update(value="⏹ Tap to send", elem_classes=["joulie-record-btn", "recording"], interactive=True)

def _record_working():
    return gr.update(value="💭 Working…", elem_classes=["joulie-record-btn", "working"], interactive=False)

def _record_disabled():
    return gr.update(value="🎤 Tap to speak", elem_classes=["joulie-record-btn"], interactive=False)

def _session_enabled():
    return gr.update(interactive=True)

def _session_disabled():
    return gr.update(interactive=False)

# Kiosk mode collapses Stop Talking and End Session into one control, so its
# label has to track what a press would actually do.
# elem_classes is passed on every branch, not just "stop": gr.update leaves a
# class list alone when it isn't named, so omitting it would make the red fill
# stick after the barge-in was over.
_END_BUTTON = {
    "disabled": lambda: gr.update(value="End Session", interactive=False,
                                  elem_classes=["joulie-session-btn"]),
    "end":      lambda: gr.update(value="End Session", interactive=True,
                                  elem_classes=["joulie-session-btn"]),
    "stop":     lambda: gr.update(value="Stop Talking", interactive=True,
                                  elem_classes=["joulie-session-btn", "stop"]),
}


def _tool_panel_html(tool) -> str:
    """Render QR + name + description as one HTML block. We use raw <img>
    rather than gr.Image because gradio_client 1.3.0's api_info builder
    crashes on the Image schema (TypeError: 'bool' is not iterable at
    gradio_client/utils.py:863, on 'additionalProperties: False')."""
    qr_url = f"/file={qr_path(tool.id)}"
    return (
        '<div id="tool-panel-inner">'
        f'<img class="tool-qr" src="{qr_url}" alt="QR code for {tool.name}">'
        '<div id="tool-caption">'
        f'<div class="tool-name">{tool.name}</div>'
        f'<div class="tool-desc">{tool.description}</div>'
        f'<div class="tool-url">Scan the QR to open · {tool.short_url}</div>'
        '</div>'
        '</div>'
    )


# Distinguishes "never painted" from a legitimately empty value on the first tick.
_MISSING = object()


@dataclass(frozen=True)
class UiState:
    """What the screen should show right now, as plain values. Derived from
    SessionCore so a handset-driven turn — which runs outside any request
    handler — can be polled and diffed rather than pushed."""
    status: str
    visitor: str
    joulie: str
    button: str
    tool_id: Optional[str]
    # Hardware mute state. Polled alongside the rest so the screen reflects the
    # mute button even out of session — that is the one control that can start
    # a session, so it must be visible before there is a session to show.
    mic_live: bool
    # "disabled" / "end" / "stop". In kiosk mode one button does both jobs, so
    # its label is state, not a constant.
    end_button: str
    # Publishers behind the current answer. Read straight off the event, with no
    # processing gate: the turn clears them itself at its first event, so what is
    # on screen always belongs to the turn in progress. The old gate was weaker —
    # it kept the previous answer's sources up until the next turn began.
    sources: tuple
    # What the right-hand stage panel shows. A bare state token, never anything
    # time-derived: the poller diffs this field, so a value carrying an elapsed
    # count would repaint the panel on every tick.
    stage: str


def _mic_live(core) -> bool:
    recorder = getattr(core, "recorder", None)
    return bool(recorder.mic_live) if recorder is not None else False


def ui_state(core) -> UiState:
    if not core.in_session:
        # Keyword arguments deliberately: this branch runs on the very first poll
        # tick, so a positional list that fell out of step with the dataclass
        # would raise inside the Timer callback rather than in a test.
        return UiState(status="idle", visitor="", joulie="", button="disabled",
                       tool_id=None, mic_live=_mic_live(core),
                       end_button="disabled", sources=(), stage="attract")

    event = core.last_event
    if core.recording:
        status, button, stage = "recording", "recording", "listening"
    elif core.processing:
        status = event.status if event and event.status else "thinking"
        button = "working"
        # Mapped through the tracker's own stages rather than trusting the status:
        # _run_turn's give-up paths ("too short", "no speech") yield
        # status="listening" while _processing is still set, and that would put the
        # on-air panel on screen with the mic closed.
        stage = status if status in ("transcribing", "thinking", "speaking") else "thinking"
    else:
        status, button, stage = "listening", "idle", "ready"

    tool = event.tool if event else None
    return UiState(
        status=status,
        visitor=event.visitor if event and event.visitor else "",
        joulie=event.joulie if event and event.joulie else "",
        button=button,
        tool_id=tool.id if tool is not None else None,
        mic_live=_mic_live(core),
        end_button="stop" if core.processing else "end",
        sources=event.sources if event else (),
        stage=stage,
    )


def _tool_panel_show(tool):
    return (gr.update(value=_tool_panel_html(tool), visible=True),)


def _tool_panel_hide():
    return (gr.update(value="", visible=False),)


def build_app() -> gr.Blocks:
    core = SessionCore()
    # Warm up the LLM in the background so the first turn isn't cold-starting.
    threading.Thread(target=core.warmup_llm, daemon=True).start()
    # The mic's mute button can drive a whole session on its own, against this
    # same core. None when the mic isn't plugged in or the button can't be opened.
    handset = attach(core)
    # The mute button is the only way in, so the screen carries no control that
    # duplicates it. They aren't merely redundant: the firmware gates a muted mic
    # to exact zeros, so "Tap to speak" while muted records silence, and two of
    # those trip the silent-turn counter in TalkController and end the visitor's
    # session.
    #
    # Start Session and Stop Talking are now hidden in BOTH modes, so
    # JOULIE_HANDSET_ENABLED=0 alone no longer gives a browser a way to start a
    # session — pair it with JOULIE_UI_DEBUG_CONTROLS=1 for that.
    kiosk_mode = handset is not None
    if kiosk_mode:
        print("[ui] mute button active — on-screen session controls hidden")
    if config.UI_DEBUG_CONTROLS:
        print("[ui] debug controls visible — Start Session / Stop Talking shown")

    # Prepend @font-face rules so Montserrat is available before the rest of the CSS applies.
    full_css = _font_face_css() + "\n" + _CSS
    with gr.Blocks(css=full_css, theme=gr.themes.Base(), title="Joulie") as app:
        gr.HTML(
            f"""
            <div id="joulie-title">⚡ Joulie — NZ Electrification Advisor</div>
            <div id="joulie-disclaimer">{config.DISCLAIMER}</div>
            """,
            elem_id="joulie-titles",
        )

        with gr.Row(elem_id="joulie-header"):
            status = gr.HTML(_status_html("idle"), elem_id="status-wrapper")
            mic = gr.HTML(_mic_html(False), elem_id="mic-wrapper")
            # Initial state: Start is the active affordance, End is dimmed/disabled.
            # In kiosk mode Start and Stop are hidden rather than removed, so the
            # handlers and output tuples below stay identical across both modes.
            # Hidden in both modes. Both duplicate controls the visitor already
            # has: the mute button starts a session, and End Session becomes Stop
            # Talking while Joulie is answering, so a separate barge-in button was
            # a third route to a job two things already did. Only
            # JOULIE_UI_DEBUG_CONTROLS brings them back, for driving a session
            # from a browser with no handset attached.
            #
            # Kept as components rather than deleted: do_start_session writes
            # start_btn in its output tuple, so removing them would ripple through
            # handlers that have nothing to do with the header's looks.
            start_btn = gr.Button(
                "Start Session",
                elem_classes=["joulie-session-btn"],
                interactive=True,
                visible=config.UI_DEBUG_CONTROLS,
            )
            stop_btn = gr.Button(
                "Stop Talking",
                elem_classes=["joulie-session-btn"],
                interactive=True,
                visible=config.UI_DEBUG_CONTROLS,
            )
            end_btn = gr.Button(
                "End Session",
                elem_classes=["joulie-session-btn"],
                interactive=False,
            )

        # Transcript left, QR + sources right. min_width is pinned below Gradio's
        # 320px default so the two columns can never wrap onto separate rows at
        # 960px wide — a wrap would put the QR back under the answer.
        with gr.Row(elem_id="joulie-main"):
            with gr.Column(scale=55, min_width=160, elem_id="col-left"):
                # Placeholders rather than a state-driven empty state: they show
                # exactly while the value is empty, which is the standby
                # condition, so they cost no plumbing.
                visitor = gr.Textbox(label="Visitor", lines=2, interactive=False,
                                     elem_id="visitor-box",
                                     placeholder="Your question will appear here")
                joulie = gr.Textbox(label="Joulie", lines=6, interactive=False,
                                    elem_id="joulie-box",
                                    placeholder="Joulie's answer will appear here")
                # Inside the column, not below the row: the page has
                # overflow:hidden, so a control outside the 100vh grid would be
                # clipped rather than scrolled to in non-kiosk mode.
                record_btn = gr.Button("🎤 Tap to speak", elem_id="record-btn",
                                       elem_classes=["joulie-record-btn"],
                                       interactive=False, visible=not kiosk_mode)
            with gr.Column(scale=45, min_width=160, elem_id="col-right"):
                # Declared first so it sits ABOVE the QR in the DOM. Note it is
                # appended LAST to _poll_outputs below — DOM order and the
                # field-zip order are independent, and conflating them paints the
                # wrong component.
                stage_panel = gr.HTML(_stage_html("attract", kiosk_mode),
                                      elem_id="stage-panel")
                # Recommended-tool panel — QR + name + description as one HTML
                # block. Hidden until Joulie names a tool in the reply
                # (detect_tool matches a keyword). Single component avoids the
                # gradio_client 1.3.0 api_info crash on gr.Image's schema.
                tool_caption = gr.HTML(visible=False, elem_id="tool-panel")
                sources_panel = gr.HTML(visible=False, elem_id="sources-panel")


        # ---- handlers ---------------------------------------------------------

        # Common tuple order for handlers that touch the tool panel too:
        #   status, visitor, joulie, record_btn, tool_caption
        _turn_outputs = [status, visitor, joulie, record_btn, tool_caption]

        def do_start_session():
            core.start_session()
            (hide_cap,) = _tool_panel_hide()
            return (
                _status_html("listening"),
                "", "",
                _record_idle(),
                _session_disabled(),  # Start
                _session_enabled(),   # End
                hide_cap,
            )

        def do_stop():
            core.interrupt()

        def do_end_or_stop():
            """The only session control. Interrupt takes precedence: end_session()
            stops playback too, so a visitor cutting a long-winded answer short
            with one button would otherwise lose the session with it. Paints
            nothing — the poller owns the screen."""
            if core.processing:
                core.interrupt()
            else:
                core.end_session()

        def do_record_toggle():
            """Single toggle. Yields optimistic UI updates BEFORE calling into
            SessionCore so the button colour flips within a browser frame — the
            actual recorder.start()/stop() can take 100-500ms on macOS."""
            print(f"[ui] record_btn clicked (in_session={core.in_session}, recording={core.recording}, processing={core.processing})")
            if not core.in_session:
                (hide_cap,) = _tool_panel_hide()
                yield _status_html("idle"), "", "", _record_disabled(), hide_cap
                return

            if not core.recording:
                # Hide any prior tool panel from the previous turn, flip to recording.
                (hide_cap,) = _tool_panel_hide()
                yield _status_html("recording"), "", "", _record_recording(), hide_cap
                if not core.begin_recording():
                    yield _status_html("listening"), "", "", _record_idle(), hide_cap
                return

            # Stop path.
            print("[ui] entering stop path")
            visitor_text = ""
            joulie_text = ""
            (hide_cap,) = _tool_panel_hide()
            yield _status_html("transcribing"), visitor_text, joulie_text, _record_working(), hide_cap
            print("[ui] about to call stream_finish_and_reply")
            final_tool = None
            for event in core.stream_finish_and_reply():
                if event.visitor is not None:
                    visitor_text = event.visitor
                if event.joulie is not None:
                    joulie_text = event.joulie
                if event.tool is not None:
                    final_tool = event.tool
                label_state = event.status or "speaking"
                yield _status_html(label_state), visitor_text, joulie_text, gr.update(), gr.update()
            # Turn done — restore idle record button and reveal tool panel if one was detected.
            if final_tool is not None:
                (show_cap,) = _tool_panel_show(final_tool)
            else:
                (show_cap,) = _tool_panel_hide()
            yield _status_html("listening"), visitor_text, joulie_text, _record_idle(), show_cap

        _session_outputs = [status, visitor, joulie, record_btn, start_btn, end_btn, tool_caption]
        start_btn.click(
            do_start_session,
            outputs=_session_outputs,
            queue=False,
        )
        # queue=False is load-bearing: the turn generator occupies the queue for
        # the whole answer, so a queued barge-in would only run once the answer
        # it was meant to cut short had already finished.
        stop_btn.click(
            do_stop,
            outputs=None,
            queue=False,
        )
        # Bound the same way in both modes now that the separate Stop Talking
        # button is gone: this one control has to absorb the barge-in wherever it
        # is shown, or removing that button would have removed the function.
        # queue=False for the same reason as stop_btn above.
        end_btn.click(do_end_or_stop, outputs=None, queue=False)
        record_btn.click(
            do_record_toggle,
            outputs=_turn_outputs,
        )

        # The mic pill, the end button and the two right-hand panels are polled,
        # never pushed by the turn handlers, so they sit outside _turn_outputs —
        # which is also do_record_toggle's output list, and that generator yields
        # fixed-width tuples at every yield site.
        #
        # Keyed by field name rather than assembled by hand: poll_handset zips
        # fields(UiState) onto this list positionally, and a mismatch paints the
        # wrong component. Built this way, adding a field without a component
        # raises here at startup instead of silently misaligning the screen.
        _poll_components = {
            "status": status,
            "visitor": visitor,
            "joulie": joulie,
            "button": record_btn,
            "tool_id": tool_caption,
            "mic_live": mic,
            "end_button": end_btn,
            "sources": sources_panel,
            "stage": stage_panel,
        }
        _poll_outputs = [_poll_components[f.name] for f in fields(UiState)]

        # Polling is gated on the interval alone, not on the handset: the mute
        # button may fail to open (hidapi missing, device busy) while the mic
        # itself still works, and the pill must keep telling the truth.
        if config.HANDSET_UI_POLL_SECONDS > 0:
            # A handset-driven turn runs entirely outside any request handler, so
            # nothing would repaint the browser. Poll the turn state the core
            # records instead of trying to push from a background thread.
            #
            # Only ever emit components that actually changed. Returning a fresh
            # value for all five on every tick makes Gradio re-render them
            # several times a second, which the status pill shows as a visible
            # height flicker.
            # One cache per browser session, keyed by session hash. A single
            # process-wide cache meant a reload — or a second screen — started
            # from the component defaults while the cache still claimed those
            # values were painted, so the new client sat on a blank session
            # until something happened to change. Bounded because a kiosk left
            # running accumulates a session per reload.
            _painted: dict[str, dict[str, object]] = {}
            _buttons = {
                "disabled": _record_disabled,
                "idle": _record_idle,
                "recording": _record_recording,
                "working": _record_working,
            }
            _render = {
                "status": _status_html,
                "visitor": lambda v: v,
                "joulie": lambda v: v,
                "button": lambda b: _buttons[b](),
                # Looked up from the registry rather than smuggled across from
                # poll_handset in a mutable cell: that cell was a second,
                # independent read of core.last_event, which another thread
                # reassigns on every token — so it could disagree with the
                # tool_id this same tick was built from and hand a None to
                # _tool_panel_show. The tool surfaces for the whole answer now,
                # which would have made that window the length of a reply.
                "tool_id": lambda t: _tool_panel_show(REGISTRY[t])[0]
                if t is not None else _tool_panel_hide()[0],
                "mic_live": _mic_html,
                # Unconditional: the poller is the only thing that writes this
                # button now, in either mode. It used to be a no-op outside kiosk
                # mode because the click handlers owned end_btn there.
                "end_button": lambda m: _END_BUTTON[m](),
                "sources": lambda src: gr.update(
                    value=_sources_html(src) if src else "", visible=bool(src)),
                "stage": lambda s: _stage_html(s, kiosk_mode),
            }

            def poll_handset(request: gr.Request):
                if len(_painted) > 8:
                    _painted.clear()
                painted = _painted.setdefault(request.session_hash, {})
                state = ui_state(core)
                out = []
                for f in fields(UiState):
                    value = getattr(state, f.name)
                    if painted.get(f.name, _MISSING) == value:
                        out.append(gr.update())
                    else:
                        painted[f.name] = value
                        out.append(_render[f.name](value))
                return tuple(out)

            # The click handlers write these components too, so drop their cached
            # values when they do or the poller will think a stale value is still
            # on screen. Only these five: clearing the whole dict also re-emitted
            # the panels no click handler touches, which is a full repaint of the
            # right-hand column on every tap.
            _CLICK_PAINTED = ("status", "visitor", "joulie", "button", "tool_id")

            def invalidate_cache():
                for painted in _painted.values():
                    for field in _CLICK_PAINTED:
                        painted.pop(field, None)

            for btn in (start_btn, end_btn, record_btn):
                btn.click(invalidate_cache, outputs=None, queue=False)

            # queue=False is load-bearing, not an optimisation. A queued event
            # makes Gradio mark its output components `pending`, and .pending
            # carries a min-height — so a queued poll visibly grew the status
            # pill from 40px to 98px on every tick. show_progress only hides the
            # progress text; it does not stop the pending class.
            gr.Timer(config.HANDSET_UI_POLL_SECONDS).tick(
                poll_handset,
                outputs=_poll_outputs,
                queue=False,
                show_progress="hidden",
            )

    return app


def launch(host: str = "127.0.0.1", port: int = 7860):
    app = build_app()
    print(f"[ui] Gradio running at http://{host}:{port}")
    print(f"[ui] Kiosk mode: open Chrome --kiosk http://{host}:{port}")
    app.launch(
        server_name=host,
        server_port=port,
        share=False,
        inbrowser=False,
        quiet=True,
        # Allow Gradio's /file= handler to serve Montserrat WOFF2s and QR PNGs
        # from the assets directories. Both are consumed by CSS/HTML in the UI.
        allowed_paths=[str(_FONTS_DIR), str(_QR_DIR)],
    )
