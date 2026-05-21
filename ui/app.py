import sys
import os
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SEPHIROT.SYS // doc-drift",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# THEME — cyberpunk / Lain aesthetic injected via CSS
# ─────────────────────────────────────────────────────────────────────────────
CYBERPUNK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=VT323&display=swap');

/* ── Global resets ───────────────────────────────────────────────────────── */
.stApp {
    background:
        radial-gradient(ellipse at top left, rgba(255,20,147,0.06), transparent 45%),
        radial-gradient(ellipse at bottom right, rgba(0,220,255,0.06), transparent 45%),
        #050510;
    color: #c8c8d8;
    font-family: 'Share Tech Mono', 'Courier New', monospace;
}

/* CRT scanlines over the whole app */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(0deg,
        rgba(0,0,0,0) 0px, rgba(0,0,0,0) 2px,
        rgba(0,220,255,0.035) 3px, rgba(0,0,0,0) 4px);
    pointer-events: none;
    z-index: 9999;
}
/* Vignette */
.stApp::after {
    content: '';
    position: fixed;
    inset: 0;
    background: radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55) 100%);
    pointer-events: none;
    z-index: 9998;
}

/* ── Headings ────────────────────────────────────────────────────────────── */
h1, h2, h3 {
    font-family: 'Share Tech Mono', monospace !important;
    color: #ff1493 !important;
    text-shadow: 0 0 8px rgba(255,20,147,0.6), 0 0 2px rgba(0,220,255,0.3);
    letter-spacing: 0.12em;
}
h1 { font-size: 2.0rem !important; }

/* glitch animation on the main title */
@keyframes glitch {
    0%, 92%, 100% { transform: translate(0); text-shadow: 0 0 8px rgba(255,20,147,0.6); }
    93% { transform: translate(-2px, 1px); text-shadow: -2px 0 #00dcff, 2px 0 #ff1493; }
    95% { transform: translate(2px, -1px); text-shadow: 2px 0 #00dcff, -2px 0 #ff1493; }
    97% { transform: translate(-1px, 0); }
}
.glitch-title { animation: glitch 5s infinite; }

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: rgba(10,10,22,0.95);
    border-right: 1px solid rgba(255,20,147,0.35);
}
section[data-testid="stSidebar"] * { color: #80b8c8; }

/* ── Text inputs / textareas ─────────────────────────────────────────────── */
.stTextArea textarea, .stTextInput input {
    background: rgba(15,15,28,0.9) !important;
    color: #00dcff !important;
    border: 1px solid rgba(0,220,255,0.4) !important;
    font-family: 'Share Tech Mono', monospace !important;
    box-shadow: inset 0 0 12px rgba(0,220,255,0.06);
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #ff1493 !important;
    box-shadow: inset 0 0 12px rgba(255,20,147,0.12), 0 0 8px rgba(255,20,147,0.3);
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton button {
    background: linear-gradient(135deg, rgba(255,20,147,0.15), rgba(255,0,102,0.05)) !important;
    color: #ff66aa !important;
    border: 1.5px solid #ff1493 !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 0.2em !important;
    text-shadow: 0 0 6px rgba(255,20,147,0.6);
    box-shadow: 0 0 14px rgba(255,20,147,0.25), inset 0 0 10px rgba(255,20,147,0.1);
    transition: all 0.2s;
}
.stButton button:hover {
    box-shadow: 0 0 24px rgba(255,20,147,0.55), inset 0 0 14px rgba(255,20,147,0.2);
    color: #ffaad4 !important;
}

/* ── Selectbox ───────────────────────────────────────────────────────────── */
.stSelectbox div[data-baseweb="select"] > div {
    background: rgba(15,15,28,0.9) !important;
    border: 1px solid rgba(0,220,255,0.4) !important;
    color: #00dcff !important;
}

/* ── Expanders → panels ──────────────────────────────────────────────────── */
.streamlit-expanderHeader, details summary {
    background: rgba(15,15,28,0.85) !important;
    border: 1px solid rgba(255,20,147,0.3) !important;
    color: #ff1493 !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 0.1em;
}
.streamlit-expanderContent, details > div {
    background: rgba(12,12,24,0.7) !important;
    border: 1px solid rgba(255,20,147,0.15) !important;
    border-top: none !important;
}

/* ── Code blocks ─────────────────────────────────────────────────────────── */
.stCode, pre, code {
    background: rgba(8,8,16,0.95) !important;
    border: 1px solid rgba(0,220,255,0.3) !important;
    color: #00dcff !important;
}

/* ── JSON viewer ─────────────────────────────────────────────────────────── */
.stJson {
    background: rgba(8,8,16,0.95) !important;
    border: 1px solid rgba(0,220,255,0.25) !important;
}

/* ── Custom panel component ──────────────────────────────────────────────── */
.cyber-panel {
    background: rgba(15,15,28,0.85);
    border: 1px solid rgba(255,20,147,0.35);
    padding: 12px 14px;
    margin-bottom: 10px;
    position: relative;
    box-shadow: inset 0 0 14px rgba(255,20,147,0.06);
}
.cyber-panel.cyan {
    border-color: rgba(0,220,255,0.35);
    box-shadow: inset 0 0 14px rgba(0,220,255,0.06);
}
.cyber-panel-title {
    position: absolute;
    top: -8px;
    left: 8px;
    background: #050510;
    padding: 0 7px;
    font-size: 10px;
    color: #ff1493;
    letter-spacing: 0.18em;
    text-shadow: 0 0 4px rgba(255,20,147,0.5);
}
.cyber-panel.cyan .cyber-panel-title { color: #00dcff; text-shadow: 0 0 4px rgba(0,220,255,0.5); }

/* ── Meters ──────────────────────────────────────────────────────────────── */
.meter { margin-bottom: 10px; }
.meter-row { display: flex; justify-content: space-between; font-size: 10px; margin-bottom: 3px; }
.meter-label { color: #00dcff; letter-spacing: 0.18em; text-shadow: 0 0 4px rgba(0,220,255,0.5); }
.meter-val { color: #c8c8d8; }
.meter-bar {
    background: #0a0a18;
    height: 8px;
    border: 1px solid #1a1a2a;
    overflow: hidden;
    position: relative;
}
.meter-fill {
    height: 100%;
    background: linear-gradient(90deg, #00dcff, #00aacc);
    box-shadow: 0 0 7px rgba(0,220,255,0.6);
}
.meter-fill.warn { background: linear-gradient(90deg, #ffaa00, #ff7700); box-shadow: 0 0 7px rgba(255,170,0,0.6); }
.meter-fill.err  { background: linear-gradient(90deg, #ff1493, #ff0066); box-shadow: 0 0 9px rgba(255,20,147,0.8); }

/* ── Verdict box ─────────────────────────────────────────────────────────── */
.verdict {
    border: 1.5px solid #ff1493;
    padding: 14px;
    text-align: center;
    color: #ff66aa;
    letter-spacing: 0.32em;
    font-size: 15px;
    font-weight: bold;
    text-shadow: 0 0 8px rgba(255,20,147,0.8);
    box-shadow: 0 0 20px rgba(255,20,147,0.4), inset 0 0 14px rgba(255,20,147,0.15);
    background: linear-gradient(135deg, rgba(255,20,147,0.12), rgba(255,0,102,0.05));
    animation: vpulse 2s infinite;
}
.verdict.sync {
    border-color: #00dcff;
    color: #66e5ff;
    text-shadow: 0 0 8px rgba(0,220,255,0.8);
    box-shadow: 0 0 20px rgba(0,220,255,0.4), inset 0 0 14px rgba(0,220,255,0.15);
    background: linear-gradient(135deg, rgba(0,220,255,0.12), rgba(0,150,200,0.05));
    animation: none;
}
@keyframes vpulse {
    50% { box-shadow: 0 0 32px rgba(255,20,147,0.7), inset 0 0 20px rgba(255,20,147,0.25); }
}

/* ── Top status bar ──────────────────────────────────────────────────────── */
.topbar {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    letter-spacing: 0.15em;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,20,147,0.35);
    margin-bottom: 14px;
}
.topbar .tb-left { color: #00dcff; text-shadow: 0 0 4px rgba(0,220,255,0.5); }
.topbar .tb-center {
    color: #ff1493;
    text-shadow: 0 0 6px rgba(255,20,147,0.7);
    font-weight: bold;
}
.topbar .tb-right { color: #80b8c8; }

/* ── Kanji divider ───────────────────────────────────────────────────────── */
.kanji {
    font-size: 13px;
    color: #ff1493;
    letter-spacing: 0.3em;
    text-align: center;
    padding: 6px 0;
    border-top: 1px solid rgba(255,20,147,0.3);
    border-bottom: 1px solid rgba(255,20,147,0.3);
    margin: 10px 0;
    text-shadow: 0 0 6px rgba(255,20,147,0.6);
}

/* ── Stage feed rows ─────────────────────────────────────────────────────── */
.stage-row { padding: 2px 0; font-size: 12px; color: #a0a0b8; }
.stage-row .ts { color: #5a8a9a; }
.stage-row .ok { color: #00dcff; text-shadow: 0 0 3px rgba(0,220,255,0.5); }
.stage-row .drift { color: #ff1493; text-shadow: 0 0 4px rgba(255,20,147,0.7); font-weight: bold; }

/* ── ASCII art ───────────────────────────────────────────────────────────── */
.ascii {
    color: #00dcff;
    font-size: 10px;
    line-height: 1.15;
    white-space: pre;
    opacity: 0.7;
    text-shadow: 0 0 3px rgba(0,220,255,0.4);
}

/* spinner colour */
.stSpinner > div { border-top-color: #ff1493 !important; }

/* alerts */
div[data-testid="stAlert"] {
    background: rgba(15,15,28,0.9) !important;
    border: 1px solid rgba(0,220,255,0.4) !important;
    color: #00dcff !important;
}
</style>
"""
st.markdown(CYBERPUNK_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

def panel(title: str, body_html: str, cyan: bool = False):
    """Render a cyberpunk bordered panel with a bracket title."""
    cls = "cyber-panel cyan" if cyan else "cyber-panel"
    st.markdown(
        f'<div class="{cls}"><span class="cyber-panel-title">[ {title} ]</span>'
        f'<div style="padding-top:4px;">{body_html}</div></div>',
        unsafe_allow_html=True,
    )


def meter(label: str, value_text: str, pct: float, level: str = "ok"):
    """
    Render a single side meter.
    level: "ok" (cyan), "warn" (amber), "err" (pink)
    pct: 0-100 fill width
    """
    pct = max(0, min(100, pct))
    fill_cls = {"ok": "meter-fill", "warn": "meter-fill warn", "err": "meter-fill err"}[level]
    st.markdown(
        f'<div class="meter">'
        f'<div class="meter-row"><span class="meter-label">{label}</span>'
        f'<span class="meter-val">{value_text}</span></div>'
        f'<div class="meter-bar"><div class="{fill_cls}" style="width:{pct}%;"></div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def topbar(target_host: str, status: str):
    """Render the top status bar."""
    ts = time.strftime("%H:%M:%S")
    st.markdown(
        f'<div class="topbar">'
        f'<span class="tb-left">◉ NODE_57 // {status}</span>'
        f'<span class="tb-center">接続中 :: SEPHIROT.SYS</span>'
        f'<span class="tb-right">{ts} UTC // {target_host}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-size:18px;color:#ff1493;letter-spacing:0.2em;'
        'text-shadow:0 0 8px rgba(255,20,147,0.6);">◢◤ CONFIG ◢◤</div>',
        unsafe_allow_html=True,
    )

    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    st.markdown(
        f'<div class="cyber-panel cyan" style="margin-top:12px;">'
        f'<span class="cyber-panel-title">[ LLM.NODE ]</span>'
        f'<div style="padding-top:4px;color:#00dcff;">provider :: {provider}</div></div>',
        unsafe_allow_html=True,
    )

    # Dataset sample selector
    # ── Page selector ────────────────────────────────────────────────────
    st.markdown('<div class="kanji">▼ NAV</div>', unsafe_allow_html=True)
    page = st.radio(
        "page",
        ["▸ PIPELINE", "▸ DASHBOARD"],
        label_visibility="collapsed",
        key="page_selector",
    )

    st.markdown('<div class="kanji">記録 DATASET</div>', unsafe_allow_html=True)
    dataset_path = PROJECT_ROOT / "Dataset" / "Doc2State.json"
    sample_options = {}
    if dataset_path.exists():
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
            sample_options = {f"{s['id']} :: {s['category']}": s for s in dataset}
        except Exception as e:
            st.error(f"dataset load fail: {e}")

    def _on_sample_change():
        """Callback: when dropdown changes, push sample text into the widget keys."""
        key = st.session_state.get("sample_selector", "(none)")
        if key and key != "(none)" and key in sample_options:
            s = sample_options[key]
            st.session_state["doc_input"] = s["doc_snippet"]
            st.session_state["mock_input"] = json.dumps(
                s["simulated_live_state"], indent=2
            )
        elif key == "(none)":
            st.session_state["doc_input"] = ""
            st.session_state["mock_input"] = ""

    selected_sample_key = st.selectbox(
        "LOAD SAMPLE",
        ["(none)"] + list(sample_options.keys()),
        key="sample_selector",
        on_change=_on_sample_change,
    )

    # ASCII decoration
    st.markdown(
        '<div class="ascii">┌─────────────┐\n'
        '│ ▓▓▓░░▓░▓▓░░░ │\n'
        '│ ░░▓▓░▓▓░░▓▓▓ │\n'
        '│ ▓░▓░▓░░▓▓░▓░ │\n'
        '└─────────────┘\n'
        '   SIG.LOCK ◉</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="kanji">情報 ABOUT</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:11px;color:#80b8c8;line-height:1.6;">'
        'Detects <span style="color:#ff1493;">documentation drift</span> — '
        'when a README describes a system differently from how it runs.<br><br>'
        '<span style="color:#00dcff;">PIPELINE:</span><br>'
        '▸ intent_extractor<br>'
        '▸ os_prober<br>'
        '▸ causal_reconciler</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
# Widget keys "doc_input" and "mock_input" are the single source of truth.
# They are seeded once here, then updated by the selectbox callback above.
if "doc_input" not in st.session_state:
    st.session_state["doc_input"] = ""
if "mock_input" not in st.session_state:
    st.session_state["mock_input"] = ""


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 class="glitch-title">◢◤ SEPHIROTSWORD57 ◢◤</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div style="color:#80b8c8;font-size:12px;letter-spacing:0.15em;margin-top:-8px;">'
    '// multi-agent reconciliation of natural language docs vs live OS state //</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

# Top status bar
topbar("localhost:22", "SYNC.OK")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: PIPELINE  (default)
# ─────────────────────────────────────────────────────────────────────────────
if page == "▸ PIPELINE":
    col_meters, col_main, col_readout = st.columns([1, 3, 1])

    # ── LEFT: live meters (populated after run) ─────────────────────────────────
    with col_meters:
        st.markdown(
            '<div style="color:#00dcff;font-size:11px;letter-spacing:0.2em;'
            'margin-bottom:8px;">▼ SYS.METERS</div>',
            unsafe_allow_html=True,
        )
        meters_placeholder = st.empty()

        # Default idle meters
        with meters_placeholder.container():
            meter("PARSE", "idle", 0, "ok")
            meter("PROBE", "idle", 0, "ok")
            meter("RECON", "idle", 0, "ok")
            meter("DRIFT", "---", 0, "ok")

        st.markdown(
            '<div class="ascii" style="margin-top:10px;">'
            'X: 042.789\nY: -19.330\nZ: 0000.01</div>',
            unsafe_allow_html=True,
        )

    # ── RIGHT: static readout panels ────────────────────────────────────────────
    with col_readout:
        st.markdown(
            '<div style="color:#ff1493;font-size:11px;letter-spacing:0.2em;'
            'margin-bottom:8px;">▼ READOUTS</div>',
            unsafe_allow_html=True,
        )
        panel(
            "TARGET",
            'host : localhost<br>port : 22<br>os : ubuntu_22<br>arch : x86_64',
        )
        st.markdown('<div class="kanji">記録 LOG</div>', unsafe_allow_html=True)
        readout_traffic = st.empty()
        with readout_traffic.container():
            panel("TX / RX", "▲ 0.00 kb<br>▼ 0.00 kb<br>pkts : 0", cyan=True)

    # ── CENTER: input + run + output ────────────────────────────────────────────
    with col_main:
        # INPUT.DOC panel
        st.markdown(
            '<div class="cyber-panel"><span class="cyber-panel-title">[ INPUT.DOC ]</span></div>',
            unsafe_allow_html=True,
        )
        doc_snippet = st.text_area(
            "documentation",
            height=140,
            key="doc_input",
            label_visibility="collapsed",
            placeholder="paste README / runbook here...",
        )

        # MOCK.STATE panel
        st.markdown(
            '<div class="cyber-panel cyan"><span class="cyber-panel-title">[ MOCK.LIVE_STATE ]</span></div>',
            unsafe_allow_html=True,
        )
        mock_state_json = st.text_area(
            "mock state",
            height=120,
            key="mock_input",
            label_visibility="collapsed",
            placeholder='{"active_ports":["9090"],"installed_packages":[]}',
        )

        run_button = st.button("▶ EXECUTE PIPELINE", type="primary", use_container_width=True)

        # ── AGENT.STREAM + results ──────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        stream_area = st.empty()
        results_area = st.container()


    # ─────────────────────────────────────────────────────────────────────────────
    # PIPELINE EXECUTION
    # ─────────────────────────────────────────────────────────────────────────────
    if run_button:
        # Validate inputs
        if not doc_snippet.strip():
            st.error("INPUT.DOC :: empty — cannot execute")
            st.stop()

        mock_state = None
        if mock_state_json.strip():
            try:
                mock_state = json.loads(mock_state_json)
            except json.JSONDecodeError as e:
                st.error(f"MOCK.LIVE_STATE :: invalid JSON — {e}")
                st.stop()

        # Import the pipeline
        try:
            from main import run_full_pipeline, build_llm, LLMConfigError
        except Exception as e:
            st.error(f"PIPELINE.IMPORT :: fail — {e}")
            st.stop()

        # Build LLM
        try:
            llm = build_llm()
        except Exception as e:
            st.error(f"LLM.NODE :: fail — {e}")
            st.stop()

        # ── Run pipeline, timing each stage by patching nothing —
        #    instead we run the whole pipeline and time it, then
        #    derive per-stage proportions. For true per-stage timing
        #    we run the three crews individually here. ──────────────
        try:
            from agents import (
                create_intent_extractor, create_extraction_task,
                create_os_prober, create_probing_task,
                create_causal_reconciler, create_reconciliation_task,
            )
            from crewai import Crew, Process

            stream_lines = []

            def push(line_html: str):
                """Append a line to the agent stream feed and re-render."""
                stream_lines.append(line_html)
                feed = "".join(
                    f'<div class="stage-row">{l}</div>' for l in stream_lines
                )
                stream_area.markdown(
                    f'<div class="cyber-panel cyan">'
                    f'<span class="cyber-panel-title">[ AGENT.STREAM ]</span>'
                    f'<div style="padding-top:4px;">{feed}</div></div>',
                    unsafe_allow_html=True,
                )

            def ts():
                return time.strftime("%H:%M:%S")

            # ── STAGE 1: Intent Extractor ──────────────────────────────────────
            push(f'<span class="ts">{ts()}</span> <span class="ok">▸</span> intent_extractor : INIT')
            t0 = time.time()
            extractor = create_intent_extractor(llm)
            task = create_extraction_task(extractor, doc_snippet)
            crew = Crew(agents=[extractor], tasks=[task], process=Process.sequential, verbose=False)
            intent = crew.kickoff().pydantic
            t_parse = time.time() - t0
            push(f'<span class="ts">{ts()}</span> <span class="ok">▸</span> intent_extractor : <span class="ok">OK</span> ({t_parse:.1f}s)')

            # ── STAGE 2: OS Prober ─────────────────────────────────────────────
            push(f'<span class="ts">{ts()}</span> <span class="ok">▸</span> os_prober : INIT')
            t0 = time.time()
            prober = create_os_prober(llm, mock_state=mock_state)
            task = create_probing_task(prober, intent)
            crew = Crew(agents=[prober], tasks=[task], process=Process.sequential, verbose=False)
            live_state = crew.kickoff().pydantic
            t_probe = time.time() - t0
            push(f'<span class="ts">{ts()}</span> <span class="ok">▸</span> os_prober : <span class="ok">OK</span> ({t_probe:.1f}s)')

            # ── STAGE 3: Causal Reconciler ─────────────────────────────────────
            push(f'<span class="ts">{ts()}</span> <span class="ok">▸</span> causal_reconciler : INIT')
            t0 = time.time()
            reconciler = create_causal_reconciler(llm)
            task = create_reconciliation_task(reconciler, intent, live_state, doc_snippet)
            crew = Crew(agents=[reconciler], tasks=[task], process=Process.sequential, verbose=False)
            report = crew.kickoff().pydantic
            t_recon = time.time() - t0

            if report.drift_detected:
                push(f'<span class="ts">{ts()}</span> <span class="drift">▸ DRIFT</span> '
                     f'causal_reconciler : {report.root_cause} ({t_recon:.1f}s)')
            else:
                push(f'<span class="ts">{ts()}</span> <span class="ok">▸</span> '
                     f'causal_reconciler : IN_SYNC ({t_recon:.1f}s)')

            # ── Save report ────────────────────────────────────────────────────
            ts_file = time.strftime("%Y%m%d_%H%M%S")
            save_path = PROJECT_ROOT / "outputs" / f"report_{ts_file}.json"
            save_path.parent.mkdir(exist_ok=True)
            full_report = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "documentation": doc_snippet,
                "extracted_intent": intent.model_dump(),
                "live_system_state": live_state.model_dump(),
                "reconciliation_report": report.model_dump(),
            }
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(full_report, f, indent=2, ensure_ascii=False)

            # ─────────────────────────────────────────────────────────────────
            # WIRE THE METERS TO REAL DATA
            # ─────────────────────────────────────────────────────────────────
            # Stage timers — scale relative to a 30s ceiling for the bar width
            CEIL = 30.0
            parse_pct = min(100, t_parse / CEIL * 100)
            probe_pct = min(100, t_probe / CEIL * 100)
            recon_pct = min(100, t_recon / CEIL * 100)

            # DRIFT meter — discrepancies / total intent items
            intent_d = intent.model_dump()
            total_items = (
                len(intent_d.get("required_ports", []))
                + len(intent_d.get("required_packages", []))
                + len(intent_d.get("required_services", []))
                + len(intent_d.get("required_env_vars", []))
            )
            n_discrep = len(report.discrepancies or [])
            drift_pct = (n_discrep / total_items * 100) if total_items > 0 else 0
            drift_level = "err" if report.drift_detected else "ok"

            # Pick level colours for stage timers (warn if slow)
            def lvl(t):
                return "err" if t > 20 else ("warn" if t > 10 else "ok")

            with meters_placeholder.container():
                meter("PARSE", f"{t_parse:.1f}s", parse_pct, lvl(t_parse))
                meter("PROBE", f"{t_probe:.1f}s", probe_pct, lvl(t_probe))
                meter("RECON", f"{t_recon:.1f}s", recon_pct, lvl(t_recon))
                meter("DRIFT", f"{n_discrep}/{total_items}", drift_pct, drift_level)

            # Update TX/RX readout with token-ish proxy (chars processed)
            chars_in = len(doc_snippet) + len(mock_state_json)
            chars_out = len(json.dumps(full_report))
            with readout_traffic.container():
                panel(
                    "TX / RX",
                    f'▲ {chars_in/1024:.2f} kb<br>'
                    f'▼ {chars_out/1024:.2f} kb<br>'
                    f'pkts : {n_discrep + total_items}',
                    cyan=True,
                )

            # ─────────────────────────────────────────────────────────────────
            # RESULTS
            # ─────────────────────────────────────────────────────────────────
            with results_area:
                # Verdict box
                if report.drift_detected:
                    st.markdown(
                        f'<div class="verdict">⚠ DRIFT // {report.root_cause}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="verdict sync">✓ SYSTEM IN SYNC</div>',
                        unsafe_allow_html=True,
                    )

                if report.justification:
                    st.markdown(
                        f'<div style="color:#80b8c8;font-size:11px;margin-top:8px;'
                        f'letter-spacing:0.05em;">// {report.justification}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown('<div class="kanji">解析 ANALYSIS</div>', unsafe_allow_html=True)

                with st.expander("◢ STAGE 1 :: EXTRACTED INTENT", expanded=True):
                    st.json(intent.model_dump())

                with st.expander("◢ STAGE 2 :: LIVE SYSTEM STATE", expanded=True):
                    st.json(live_state.model_dump())

                with st.expander("◢ STAGE 3 :: RECONCILIATION REPORT", expanded=True):
                    if report.discrepancies:
                        st.markdown(
                            '<div style="color:#ff1493;letter-spacing:0.1em;">'
                            '▸ DISCREPANCIES:</div>',
                            unsafe_allow_html=True,
                        )
                        for d in report.discrepancies:
                            st.markdown(
                                f'<div class="stage-row">'
                                f'<span class="drift">▸</span> '
                                f'<span style="color:#00dcff;">{d.field}</span> :: '
                                f'expected <span style="color:#ff66aa;">{d.expected}</span> '
                                f'got <span style="color:#ff66aa;">{d.actual}</span></div>',
                                unsafe_allow_html=True,
                            )

                    if report.remediation_bash:
                        st.markdown(
                            '<div style="color:#00dcff;letter-spacing:0.1em;margin-top:8px;">'
                            '▸ BASH.REMEDIATION:</div>',
                            unsafe_allow_html=True,
                        )
                        st.code(report.remediation_bash, language="bash")

                    if report.remediation_markdown:
                        st.markdown(
                            '<div style="color:#00dcff;letter-spacing:0.1em;margin-top:8px;">'
                            '▸ MARKDOWN.PATCH:</div>',
                            unsafe_allow_html=True,
                        )
                        st.code(report.remediation_markdown, language="markdown")

                # Download
                st.download_button(
                    "▼ DOWNLOAD REPORT // JSON",
                    data=json.dumps(full_report, indent=2, ensure_ascii=False),
                    file_name=f"sephirot_report_{ts_file}.json",
                    mime="application/json",
                    use_container_width=True,
                )

                st.markdown(
                    f'<div style="color:#5a8a9a;font-size:10px;margin-top:8px;'
                    f'letter-spacing:0.1em;">// report saved :: outputs/report_{ts_file}.json</div>',
                    unsafe_allow_html=True,
                )

        except Exception as e:
            st.error(f"PIPELINE.EXEC :: fail — {e.__class__.__name__}: {e}")
            with st.expander("◢ TRACEBACK"):
                st.exception(e)




# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DASHBOARD  (results visualisation)
# ─────────────────────────────────────────────────────────────────────────────
elif page == "▸ DASHBOARD":
    from evaluation.results_loader import (
        load_all_reports, load_dataset, compute_aggregate_stats,
    )

    reports = load_all_reports(str(PROJECT_ROOT / "outputs"))
    dataset_index = load_dataset(str(PROJECT_ROOT / "Dataset" / "Doc2State.json"))
    stats = compute_aggregate_stats(reports, dataset_index)

    if stats["total_reports"] == 0:
        st.markdown(
            '''<div class="cyber-panel">
            <span class="cyber-panel-title">[ DASHBOARD.EMPTY ]</span>
            <div style="padding-top:8px;color:#80b8c8;">
            no reports yet. run the pipeline at least once to populate this view.
            </div></div>''',
            unsafe_allow_html=True,
        )
    else:
        # ── HEADLINE STATS ROW ───────────────────────────────────────────
        st.markdown(
            '''<div style="color:#ff1493;font-size:13px;letter-spacing:0.2em;
            margin-bottom:12px;">▼ AGGREGATE.STATS</div>''',
            unsafe_allow_html=True,
        )
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(
                f'''<div class="cyber-panel cyan" style="text-align:center;">
                <span class="cyber-panel-title">[ TOTAL ]</span>
                <div style="padding-top:4px;font-size:22px;color:#00dcff;
                text-shadow:0 0 8px rgba(0,220,255,0.6);">{stats["total_reports"]}</div>
                <div style="font-size:9px;color:#80b8c8;">reports loaded</div>
                </div>''',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'''<div class="cyber-panel" style="text-align:center;">
                <span class="cyber-panel-title">[ DATASET ]</span>
                <div style="padding-top:4px;font-size:22px;color:#ff1493;
                text-shadow:0 0 8px rgba(255,20,147,0.6);">{stats["dataset_reports"]}</div>
                <div style="font-size:9px;color:#80b8c8;">samples scored</div>
                </div>''',
                unsafe_allow_html=True,
            )
        with c3:
            acc_pct = stats["drift_accuracy"] * 100
            color = "#00dcff" if acc_pct >= 70 else ("#ffaa00" if acc_pct >= 50 else "#ff1493")
            st.markdown(
                f'''<div class="cyber-panel cyan" style="text-align:center;">
                <span class="cyber-panel-title">[ DRIFT.ACC ]</span>
                <div style="padding-top:4px;font-size:22px;color:{color};
                text-shadow:0 0 8px {color}80;">{acc_pct:.1f}%</div>
                <div style="font-size:9px;color:#80b8c8;">detection accuracy</div>
                </div>''',
                unsafe_allow_html=True,
            )
        with c4:
            rc_pct = stats["root_cause_accuracy"] * 100
            color = "#00dcff" if rc_pct >= 70 else ("#ffaa00" if rc_pct >= 50 else "#ff1493")
            st.markdown(
                f'''<div class="cyber-panel" style="text-align:center;">
                <span class="cyber-panel-title">[ ROOT.CAUSE ]</span>
                <div style="padding-top:4px;font-size:22px;color:{color};
                text-shadow:0 0 8px {color}80;">{rc_pct:.1f}%</div>
                <div style="font-size:9px;color:#80b8c8;">attribution accuracy</div>
                </div>''',
                unsafe_allow_html=True,
            )
        with c5:
            safety_pct = stats["safety_rate"] * 100
            color = "#00dcff" if safety_pct >= 95 else "#ffaa00"
            st.markdown(
                f'''<div class="cyber-panel cyan" style="text-align:center;">
                <span class="cyber-panel-title">[ SAFETY ]</span>
                <div style="padding-top:4px;font-size:22px;color:{color};
                text-shadow:0 0 8px {color}80;">{safety_pct:.1f}%</div>
                <div style="font-size:9px;color:#80b8c8;">safe bash scripts</div>
                </div>''',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="kanji">分布 DISTRIBUTION</div>', unsafe_allow_html=True)

        # ── DRIFT DISTRIBUTION (bar) ─────────────────────────────────────
        d_col, c_col = st.columns([1, 1])
        with d_col:
            st.markdown(
                '''<div class="cyber-panel">
                <span class="cyber-panel-title">[ ROOT.CAUSE DISTRIBUTION ]</span>
                </div>''',
                unsafe_allow_html=True,
            )
            dd = stats["drift_distribution"]
            max_count = max(dd.values()) if dd else 1
            for rc, count in sorted(dd.items(), key=lambda x: -x[1]):
                pct = (count / max_count * 100) if max_count > 0 else 0
                bar_color = {
                    "SYSTEM_FAULT": "#ff1493",
                    "DOC_FAULT":    "#ffaa00",
                    "IN_SYNC":      "#00dcff",
                    "AMBIGUOUS":    "#9966ff",
                }.get(rc, "#666688")
                st.markdown(
                    f'''<div style="margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;font-size:10px;">
                    <span style="color:{bar_color};letter-spacing:0.12em;">{rc}</span>
                    <span style="color:#c8c8d8;">{count}</span></div>
                    <div style="background:#0a0a18;height:10px;border:1px solid #1a1a2a;">
                    <div style="background:{bar_color};height:100%;width:{pct}%;
                    box-shadow:0 0 6px {bar_color}99;"></div></div></div>''',
                    unsafe_allow_html=True,
                )

        with c_col:
            st.markdown(
                '''<div class="cyber-panel cyan">
                <span class="cyber-panel-title">[ ACCURACY BY CATEGORY ]</span>
                </div>''',
                unsafe_allow_html=True,
            )
            if stats["by_category"]:
                for cat, c in sorted(stats["by_category"].items()):
                    total = c["total"]
                    acc = (c["correct_drift"] / total * 100) if total > 0 else 0
                    bar_color = "#00dcff" if acc >= 70 else ("#ffaa00" if acc >= 50 else "#ff1493")
                    st.markdown(
                        f'''<div style="margin-bottom:8px;">
                        <div style="display:flex;justify-content:space-between;font-size:10px;">
                        <span style="color:#00dcff;letter-spacing:0.1em;">{cat}</span>
                        <span style="color:#c8c8d8;">{c["correct_drift"]}/{total}</span></div>
                        <div style="background:#0a0a18;height:10px;border:1px solid #1a1a2a;">
                        <div style="background:{bar_color};height:100%;width:{acc}%;
                        box-shadow:0 0 6px {bar_color}99;"></div></div></div>''',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div style="color:#80b8c8;font-size:11px;padding:8px;">'
                    'no dataset samples evaluated yet.</div>',
                    unsafe_allow_html=True,
                )

        st.markdown('<div class="kanji">解析 EXTRACTION</div>', unsafe_allow_html=True)

        # ── EXTRACTION P/R/F1 TABLE ──────────────────────────────────────
        st.markdown(
            '''<div class="cyber-panel cyan">
            <span class="cyber-panel-title">[ INTENT EXTRACTION :: P / R / F1 ]</span>
            </div>''',
            unsafe_allow_html=True,
        )
        rows_html = (
            '<div style="display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;'
            'gap:8px;padding:8px;color:#80b8c8;font-size:10px;'
            'border-bottom:1px solid rgba(0,220,255,0.3);">'
            '<div>FIELD</div><div style="text-align:right;">PRECISION</div>'
            '<div style="text-align:right;">RECALL</div>'
            '<div style="text-align:right;">F1</div></div>'
        )
        for field, s in stats["extraction_stats"].items():
            f1_color = "#00dcff" if s["f1"] >= 0.7 else ("#ffaa00" if s["f1"] >= 0.4 else "#ff1493")
            rows_html += (
                f'<div style="display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;'
                f'gap:8px;padding:6px 8px;font-size:11px;'
                f'border-bottom:1px solid rgba(255,20,147,0.15);">'
                f'<div style="color:#ff66aa;">{field}</div>'
                f'<div style="text-align:right;color:#c8c8d8;font-variant-numeric:tabular-nums;">{s["precision"]:.3f}</div>'
                f'<div style="text-align:right;color:#c8c8d8;font-variant-numeric:tabular-nums;">{s["recall"]:.3f}</div>'
                f'<div style="text-align:right;color:{f1_color};font-variant-numeric:tabular-nums;'
                f'text-shadow:0 0 4px {f1_color}66;">{s["f1"]:.3f}</div></div>'
            )
        st.markdown(rows_html, unsafe_allow_html=True)

        st.markdown('<div class="kanji">記録 LOG</div>', unsafe_allow_html=True)

        # ── REPORT BROWSER ───────────────────────────────────────────────
        st.markdown(
            '''<div class="cyber-panel">
            <span class="cyber-panel-title">[ REPORT.BROWSER ]</span>
            </div>''',
            unsafe_allow_html=True,
        )
        # List of all reports, newest first
        for r in reports[-25:][::-1]:  # show last 25 in reverse
            rr = r.get("reconciliation_report", {})
            sid = r.get("_sample_id") or "live"
            drift = rr.get("drift_detected", False)
            rc = rr.get("root_cause") or "?"
            color = "#ff1493" if drift else "#00dcff"
            tag = "DRIFT" if drift else "SYNC"
            doc_preview = (r.get("documentation") or "")[:80]
            with st.expander(f"▸ {r.get('_filename','?')} :: {tag} :: {rc}"):
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.markdown(
                        f'''<div style="font-size:10px;color:#80b8c8;line-height:1.6;">
                        <span style="color:#ff1493;">sample_id :</span> {sid}<br>
                        <span style="color:#ff1493;">timestamp :</span> {r.get("timestamp","?")}<br>
                        <span style="color:#ff1493;">drift :</span>
                        <span style="color:{color};">{drift}</span><br>
                        <span style="color:#ff1493;">root_cause :</span>
                        <span style="color:{color};">{rc}</span>
                        </div>''',
                        unsafe_allow_html=True,
                    )
                with col_b:
                    st.markdown(
                        f'<div style="font-size:11px;color:#c8c8d8;'
                        f'background:rgba(8,8,16,0.6);padding:6px;border:1px solid #2a2a4a;">'
                        f'<em>{doc_preview}{"..." if len(doc_preview) >= 80 else ""}</em></div>',
                        unsafe_allow_html=True,
                    )

                if rr.get("discrepancies"):
                    st.markdown(
                        '<div style="color:#ff1493;font-size:10px;margin-top:6px;'
                        'letter-spacing:0.1em;">▸ DISCREPANCIES:</div>',
                        unsafe_allow_html=True,
                    )
                    for d in rr["discrepancies"]:
                        st.markdown(
                            f'<div style="font-size:11px;color:#a0a0b8;padding-left:8px;">'
                            f'<span style="color:#00dcff;">{d.get("field","?")}</span> :: '
                            f'expected <span style="color:#ff66aa;">{d.get("expected","?")}</span> '
                            f'got <span style="color:#ff66aa;">{d.get("actual","?")}</span></div>',
                            unsafe_allow_html=True,
                        )

                if rr.get("remediation_bash"):
                    st.code(rr["remediation_bash"], language="bash")


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div style="border-top:1px solid rgba(255,20,147,0.3);padding-top:8px;'
    'color:#5a8a9a;font-size:10px;letter-spacing:0.15em;text-align:center;">'
    '◢◤ SEPHIROTSWORD57 :: GROUP_2 :: 78942 / 79000 / 78741 / 78745 ◢◤<br>'
    '記録 // 接続中 // システム正常</div>',
    unsafe_allow_html=True,
)