# Sephirotsword57

Multi-Agent Reconciliation of Natural Language Documentation and Live OS State via Bash Telemetry.

Detects **documentation drift** — when a README says the system should look one way but the live server is actually different — and generates a fix automatically.

## Architecture

The pipeline uses three specialized agents:

```
README/Docs  →  [Intent Extractor]   → JSON Intent Schema
Live Linux   →  [OS Prober]          → JSON Live State
                       ↓
                 [Causal Reconciler] → Discrepancy + Bash Fix or Markdown Patch
```

## Project Structure

```
Sephirotsword57/
├── agents/                 # The 3 specialised agent modules
│   ├── schemas.py          # Pydantic data contracts
│   ├── intent_extractor.py # Stage 1: parses docs into JSON
│   ├── os_prober.py        # Stage 2: probes live system
│   └── causal_reconciler.py # Stage 3: compares + generates fix
├── baselines/              # 3 comparison baselines for evaluation
│   ├── baseline_direct_llm.py
│   ├── baseline_regex.py
│   └── baseline_single_agent_rag.py
├── sandbox/                # Security-enforced read-only Bash executor
│   └── safe_bash_tool.py
├── evaluation/             # Metrics + benchmark runner
│   ├── metrics.py
│   └── runner.py
├── ui/                     # Streamlit web interface
│   └── app.py
├── tests/                  # Unit tests (no API calls needed)
├── Dataset/
│   └── Doc2State.json      # Our 100-sample benchmark dataset
├── outputs/                # Reconciliation reports saved here
├── main.py                 # CLI entry point
└── requirements.txt
```

## Setup

```bash
# 1. Create virtual environment
py -3.11 -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file with your API keys
echo "GEMINI_API_KEY=your_key_here" > .env
echo "GROQ_API_KEY=your_key_here" >> .env
echo "LLM_PROVIDER=gemini" >> .env
```

## Usage

### CLI
```bash
# Run with built-in demo
python main.py --demo

# Run with a single dataset sample
python evaluation/runner.py --sample-id 003

# Run full 100-sample evaluation
python evaluation/runner.py

# Run baseline comparison
python evaluation/runner.py --baselines --limit 10

# Validate setup without making API calls
python evaluation/runner.py --dry-run
```

### Web UI
```bash
streamlit run ui/app.py
```
Then open http://localhost:8501

### Tests
```bash
pytest tests/ -v
```

## Doc2State-100 Dataset

Our benchmark dataset contains 100 hand-crafted reconciliation cases across 4 drift categories:

| Category | Samples |
|---|---|
| Port Drift | 26 |
| Package Drift | 26 |
| Service/Docker Drift | 24 |
| Environment Variable Drift | 24 |

Each sample contains a documentation snippet, a ground-truth infrastructure intent, a simulated live system state with injected drift, and the expected reconciliation outcome.

## LLM Providers

Supported via `LLM_PROVIDER` environment variable:
- `gemini` — Google Gemini 2.0 Flash (free tier available)
- `groq` — Groq Llama 3.1 8B Instant (free tier available)

Switch between them with one line in `.env`.

## Authors

Group 2 — Menedżerska Akademia Nauk Stosowanych w Warszawie

- Yahya Yiğit Yıldız (78942)
- Nedret Birkay (79000)
- Doruk Kağan Ergin (78741)
- Cüneyt Emre Durak (78745)
