import threading
from pathlib import Path

import gradio as gr

from joulie import config
from joulie.session_core import SessionCore
from joulie.tools import qr_path


_FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
_QR_DIR = Path(__file__).parent.parent / "assets" / "qrcodes"


def _font_face_css() -> str:
    """Build @font-face blocks pointing at Gradio's /file= static handler for
    each Montserrat weight. Self-hosted so the kiosk works offline."""
    weights = [400, 500, 600, 700]
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
}

.gradio-container {
  background: var(--joulie-bg) !important;
  color: var(--joulie-text) !important;
  min-height: 100vh;
  max-width: 900px !important;
  margin: 0 auto !important;
}
.gradio-container *, body, button, textarea, input {
  font-family: 'Montserrat', -apple-system, "Inter", system-ui, sans-serif !important;
}

#joulie-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--joulie-accent);
  padding: 24px 10px 4px 10px;
}
#joulie-disclaimer {
  font-size: 18px;
  color: var(--joulie-text);
  opacity: 0.7;
  margin-bottom: 16px;
  line-height: 1.5;
  padding: 24px 10px 4px 10px;
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
  font-size: 18px !important;
  line-height: 1.5 !important;
}
label span, .gr-checkbox-group label {
  color: var(--joulie-text) !important;
  font-weight: 600;
}

/* Session buttons — always gold; disabled state just fades. */
.joulie-session-btn > button {
  background: var(--joulie-accent) !important;
  color: var(--joulie-bg) !important;
  border: none !important;
  font-weight: 600 !important;
  transition: opacity 120ms ease !important;
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
  font-size: 22px !important;
  font-weight: 700 !important;
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
  margin-top: 12px !important;
  padding: 16px !important;
  background: var(--joulie-panel) !important;
  border: 1px solid var(--joulie-border) !important;
  border-radius: 12px !important;
}
#tool-panel-inner {
  display: flex;
  align-items: center;
  gap: 20px;
}
.tool-qr {
  width: 180px;
  height: 180px;
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
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
}
#tool-caption .tool-desc {
  font-size: 16px;
  line-height: 1.5;
  margin-bottom: 10px;
}
#tool-caption .tool-url {
  font-size: 13px;
  opacity: 0.7;
  font-weight: 500;
}

/* Status pill — plain text label with a coloured dot indicator. Text-only
 * keeps the box height rock-steady across states; the dot changes colour
 * to signal Recording/Speaking/etc. */
#status-wrapper {
  display: flex !important;
  align-items: center !important;
}
#joulie-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 14px;
  border-radius: 17px;
  font-size: 15px;
  font-weight: 500;
  color: var(--joulie-text);
  background: var(--joulie-panel);
  white-space: nowrap;
  box-sizing: border-box;
  margin: 3px;
}
#joulie-status::before {
  content: "";
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--joulie-border);
  flex-shrink: 0;
}
#joulie-status[data-state="listening"]::before { background: #4ADE80; }
#joulie-status[data-state="recording"]::before,
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
"""

_STATUS_LABELS = {
    "idle":         "Idle",
    "transcribing": "Transcribing",
    "thinking":     "Thinking",
    "speaking":     "Speaking",
    "listening":    "Listening",
    "recording":    "Recording",
}


def _status_html(state: str) -> str:
    label = _STATUS_LABELS.get(state, state.title())
    return f'<div id="joulie-status" data-state="{state}">{label}</div>'


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


def _tool_panel_show(tool):
    return (gr.update(value=_tool_panel_html(tool), visible=True),)


def _tool_panel_hide():
    return (gr.update(value="", visible=False),)


def build_app() -> gr.Blocks:
    core = SessionCore()
    # Warm up the LLM in the background so the first turn isn't cold-starting.
    threading.Thread(target=core.warmup_llm, daemon=True).start()

    # Prepend @font-face rules so Montserrat is available before the rest of the CSS applies.
    full_css = _font_face_css() + "\n" + _CSS
    with gr.Blocks(css=full_css, theme=gr.themes.Base(), title="Joulie") as app:
        gr.HTML(
            f"""
            <div id="joulie-title">⚡ Joulie — NZ Electrification Advisor</div>
            <div id="joulie-disclaimer">{config.DISCLAIMER}</div>
            """
        )

        with gr.Row():
            status = gr.HTML(_status_html("idle"), elem_id="status-wrapper")
            # Initial state: Start is the active affordance, End is dimmed/disabled.
            start_btn = gr.Button(
                "Start Session",
                elem_classes=["joulie-session-btn"],
                interactive=True,
            )
            stop_btn = gr.Button(
                "Stop Talking",
                elem_classes=["joulie-session-btn"],
                interactive=True,
            )
            end_btn = gr.Button(
                "End Session",
                elem_classes=["joulie-session-btn"],
                interactive=False,
            )

        visitor = gr.Textbox(label="Visitor", lines=2, interactive=False)
        joulie = gr.Textbox(label="Joulie", lines=6, interactive=False)

        # Recommended-tool panel — QR + name + description as one HTML block.
        # Hidden until Joulie names a tool in the reply (detect_tool matches
        # a keyword). Single component avoids the gradio_client 1.3.0 api_info
        # crash on gr.Image's schema.
        tool_caption = gr.HTML(visible=False, elem_id="tool-panel")

        # Record button starts disabled — a session must be started first.
        record_btn = gr.Button("🎤 Tap to speak", elem_classes=["joulie-record-btn"], interactive=False)

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

        def do_end_session():
            core.end_session()
            (hide_cap,) = _tool_panel_hide()
            return (
                _status_html("idle"),
                "", "",
                _record_disabled(),
                _session_enabled(),   # Start
                _session_disabled(),  # End
                hide_cap,
            )

        def do_stop():
            core.interrupt()

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
        end_btn.click(
            do_end_session,
            outputs=_session_outputs,
            queue=False,
        )
        record_btn.click(
            do_record_toggle,
            outputs=_turn_outputs,
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
