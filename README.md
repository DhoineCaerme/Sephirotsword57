# Sephirotsword57

**Multi-Agent Reconciliation of Natural Language Documentation and Live OS State via Bash Telemetry**

Detects *documentation drift* — when a README describes a system differently from how it actually runs — and generates an actionable fix automatically.

```
README/Docs  →  [Intent Extractor]   → JSON Intent Schema
                                              ↓
Live Linux   →  [OS Prober]          → JSON Live State
                                              ↓
                                  [Causal Reconciler] → Bash fix OR Markdown patch
```

---

## Quick start (Windows)

```bash
git clone <repo>
cd Sephirotsword57

# First-time setup (one command)
setup.bat

# Create .env with your API key
echo GEMINI_API_KEY=your_key_here > .env
echo LLM_PROVIDER=gemini >> .env

# Launch the web UI
run.bat

# Or run a quick CLI demo
run.bat demo

# Or run the 4-sample quick demo (one per category)
run.bat quick
```

## Quick start (macOS / Linux)

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key_here" > .env
echo "LLM_PROVIDER=gemini" >> .env

# Validate everything is in place
python scripts/validate_setup.py

# Launch the UI
streamlit run ui/app.py
```

---

## Commands cheatsheet

| Command (Windows) | Equivalent (cross-platform) | What it does |
|---|---|---|
| `run.bat` | `streamlit run ui/app.py` | Launches the cyberpunk web UI |
| `run.bat demo` | `python main.py --demo` | One CLI run with built-in doc |
| `run.bat quick` | `python scripts/quick_demo.py` | Runs 4 samples, one per category |
| `run.bat validate` | `python scripts/validate_setup.py` | Pre-flight setup check |
| `run.bat test` | `python tests/test_metrics.py` | Runs the unit test suite |
| `run.bat eval` | `python evaluation/runner.py` | Full 100-sample evaluation |
| `run.bat eval-limit N` | `python evaluation/runner.py --limit N` | First N samples only |
| `run.bat baselines` | `python evaluation/runner.py --baselines` | Compares against 3 baselines |

---

## Project structure

```
Sephirotsword57/
├── agents/                       # Three specialised agent modules
│   ├── schemas.py                # Pydantic data contracts
│   ├── intent_extractor.py       # Stage 1: parses docs into JSON
│   ├── os_prober.py              # Stage 2: probes live system
│   └── causal_reconciler.py      # Stage 3: compares + generates fix
├── baselines/                    # Three comparison baselines
│   ├── baseline_direct_llm.py    # Zero-shot single LLM call
│   ├── baseline_regex.py         # Pure regex, no API
│   └── baseline_single_agent_rag.py
├── sandbox/                      # Read-only Bash executor
│   └── safe_bash_tool.py
├── evaluation/                   # Metrics + benchmark + dashboard data
│   ├── metrics.py                # Pure metric functions
│   ├── runner.py                 # Full + per-sample + baselines runners
│   └── results_loader.py         # Aggregates saved reports for dashboard
├── ui/                           # Streamlit web interface
│   └── app.py                    # Cyberpunk UI + results dashboard
├── tests/                        # 30 unit tests, all passing
│   ├── test_metrics.py
│   └── test_baseline_regex.py
├── scripts/
│   ├── validate_setup.py         # Pre-flight environment check
│   └── quick_demo.py             # 4-sample preset
├── Dataset/
│   └── Doc2State.json            # 100-sample benchmark dataset
├── outputs/                      # Reconciliation reports saved here
├── main.py                       # CLI entry point
├── setup.bat                     # First-time Windows setup
├── run.bat                       # Windows command dispatcher
└── requirements.txt
```

---

## The Streamlit UI

Two pages accessible from the sidebar:

**▸ PIPELINE** — input a README, run the full 3-agent pipeline, watch agents work live, see the verdict.

**▸ DASHBOARD** — aggregates every saved report from `outputs/`. Shows:
- Total reports, dataset coverage, drift accuracy, root cause accuracy, bash safety rate
- Root cause distribution chart
- Accuracy broken down by drift category
- Intent extraction Precision / Recall / F1 per field (ports, packages, services, env vars)
- Browser of all individual reports with expandable details

---

## Doc2State-100 benchmark dataset

| Category | Samples |
|---|---|
| Port Drift | 26 |
| Package Drift | 26 |
| Service/Docker Drift | 24 |
| Environment Variable Drift | 24 |
| **Total** | **100** |

Each sample contains a documentation snippet, a ground-truth infrastructure intent, a simulated live system state with injected drift, and the expected reconciliation outcome.

---

## Evaluation metrics

| Metric | What it measures |
|---|---|
| **Intent Extraction F1** | Per-field precision/recall/F1 for ports, packages, services, env vars |
| **Drift Detection Accuracy** | Binary classification: did the system correctly detect drift exists? |
| **Root Cause Attribution Accuracy** | SYSTEM_FAULT vs DOC_FAULT vs IN_SYNC classification accuracy |
| **Remediation Validity** | Are generated Bash scripts syntactically valid and safe? |

---

## Comparison baselines

| Baseline | Approach | API cost per sample |
|---|---|---|
| **B1: Direct LLM** | Single zero-shot prompt, no agents, no schema | 1 call |
| **B2: Regex** | Pure pattern matching, hardcoded package vocabulary | 0 calls |
| **B3: Single-Agent RAG** | One generalised agent with chunked context, no specialisation | 1 call |

---

## LLM providers

Set `LLM_PROVIDER` in `.env` to switch:

| Provider | Model | Notes |
|---|---|---|
| `gemini` | `gemini-2.0-flash` | Free tier, generous daily quota |
| `groq` | `llama-3.1-8b-instant` | Free tier, fast, tight per-minute limits |

---

## Authors

Group 2 — Menedżerska Akademia Nauk Stosowanych w Warszawie

- Yahya Yiğit Yıldız (78942)
- Nedret Birkay (79000)
- Doruk Kağan Ergin (78741)
- Cüneyt Emre Durak (78745)