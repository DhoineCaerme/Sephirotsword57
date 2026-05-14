"""
baseline_single_agent_rag.py — Baseline 3: Single-Agent with RAG Context

One generalised LLM agent performs extraction AND comparison AND root cause
classification all in a single prompt. Uses basic chunking + keyword retrieval
to simulate RAG without needing a vector store.

Cost: 1 Gemini API call per sample.

This demonstrates why agent specialisation matters — a single agent doing
everything at once is less reliable than 3 specialised agents.
"""

import os
import re
import json
from dotenv import load_dotenv

load_dotenv()


def _call_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text.strip()


# ── Simple chunking + keyword retrieval (simulates RAG) ──────────────────────

INFRA_KEYWORDS = [
    "port", "package", "install", "service", "container", "docker",
    "environment", "variable", "env", "run", "start", "listen",
    "require", "ensure", "must", "should", "need", "configure",
]


def chunk_text(text: str, chunk_size: int = 150, overlap: int = 30) -> list:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += chunk_size - overlap
    return chunks or [text]


def retrieve_chunks(chunks: list, top_k: int = 3) -> list:
    """Score chunks by infrastructure keyword density, return top_k."""
    scored = []
    for chunk in chunks:
        lower = chunk.lower()
        score = sum(1 for kw in INFRA_KEYWORDS if kw in lower)
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def _live_state_to_text(live_state: dict) -> str:
    lines = []
    ports = live_state.get("active_ports", [])
    lines.append(f"Active ports: {', '.join(ports) if ports else 'none'}")
    pkgs = live_state.get("installed_packages", [])
    lines.append(f"Installed packages: {', '.join(pkgs) if pkgs else 'none'}")
    svcs = live_state.get("running_services", [])
    lines.append(f"Running services: {', '.join(svcs) if svcs else 'none'}")
    evars = live_state.get("active_env_vars", [])
    if evars:
        lines.append(f"Env vars set: {', '.join(ev['name']+'='+ev.get('value','?') for ev in evars)}")
    else:
        lines.append("Env vars: none")
    return "\n".join(lines)


PROMPT = """You are a DevOps infrastructure auditing agent.

RETRIEVED DOCUMENTATION CONTEXT:
---
{context}
---

LIVE SYSTEM STATE:
{live_state}

In a single response perform ALL of these tasks:
1. Extract all infrastructure requirements from the documentation
   (ports, packages, services/containers, environment variables).
2. Compare each requirement to the live system state.
3. State clearly: is there configuration drift? (yes/no)
4. If drift exists, classify root cause:
   - SYSTEM_FAULT: the system needs to be fixed
   - DOC_FAULT: the documentation is outdated
5. Suggest a specific fix.

Use clear headings for each section."""


def run_baseline_single_agent_rag(doc_snippet: str, live_state: dict) -> dict:
    """
    Runs Baseline 3 on a single sample.
    Returns dict with: drift_detected, root_cause, raw_output, error
    """
    chunks = chunk_text(doc_snippet)
    context = "\n---\n".join(retrieve_chunks(chunks, top_k=min(3, len(chunks))))
    live_text = _live_state_to_text(live_state)

    prompt = PROMPT.format(context=context, live_state=live_text)

    try:
        raw = _call_gemini(prompt)
    except Exception as e:
        return {"drift_detected": False, "root_cause": "IN_SYNC",
                "raw_output": f"[API ERROR]: {e}", "error": True}

    lower = raw.lower()

    # Drift detection
    if re.search(r'\byes\b', lower) or "drift detected" in lower or "configuration drift" in lower:
        drift = True
    elif "no drift" in lower or "no configuration drift" in lower or "in sync" in lower:
        drift = False
    else:
        drift = any(w in lower for w in ["missing", "mismatch", "discrepanc", "not found",
                                          "not running", "not installed", "not set"])

    # Root cause
    if not drift:
        root_cause = "IN_SYNC"
    elif "doc_fault" in lower or "doc fault" in lower or "documentation fault" in lower \
            or "documentation is outdated" in lower:
        root_cause = "DOC_FAULT"
    else:
        root_cause = "SYSTEM_FAULT"

    return {"drift_detected": drift, "root_cause": root_cause,
            "raw_output": raw, "error": False}


if __name__ == "__main__":
    with open("Dataset/Doc2State.json") as f:
        data = json.load(f)

    seen = set()
    for s in data:
        if s["category"] in seen:
            continue
        seen.add(s["category"])
        print(f"\n=== {s['category']} (ID {s['id']}) ===")
        result = run_baseline_single_agent_rag(s["doc_snippet"], s["simulated_live_state"])
        print(f"Drift: {result['drift_detected']}  Root cause: {result['root_cause']}")
        print(f"Output preview: {result['raw_output'][:200]}")
