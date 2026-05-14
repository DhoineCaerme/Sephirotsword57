"""
baseline_direct_llm.py — Baseline 1: Direct Zero-Shot LLM

Single prompt, no agents, no schema, no tools.
Simulates a developer pasting their README into a chatbox and asking
"is there anything wrong with my system?"

Cost: 1 Gemini API call per sample.
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


def _live_state_to_text(live_state: dict) -> str:
    """Converts simulated live state dict into plain English for the prompt."""
    lines = []

    ports = live_state.get("active_ports", [])
    lines.append(f"Listening ports: {', '.join(ports) if ports else 'none'}")

    pkgs = live_state.get("installed_packages", [])
    lines.append(f"Installed packages: {', '.join(pkgs) if pkgs else 'none found'}")

    svcs = live_state.get("running_services", [])
    lines.append(f"Running services/containers: {', '.join(svcs) if svcs else 'none'}")

    evars = live_state.get("active_env_vars", [])
    if evars:
        lines.append(f"Environment variables set: {', '.join(ev['name']+'='+ev.get('value','?') for ev in evars)}")
    else:
        lines.append("Environment variables: none set")

    return "\n".join(lines)


PROMPT = """You are a DevOps engineer reviewing infrastructure configuration.

README DOCUMENTATION (what the system SHOULD look like):
{doc_snippet}

LIVE SYSTEM STATE (what the system ACTUALLY looks like right now):
{live_state}

Answer ALL of the following:
1. Is there configuration drift? Answer: yes or no
2. If yes, list each discrepancy specifically.
3. Root cause: is this SYSTEM_FAULT (system needs fixing) or DOC_FAULT (docs are outdated)?
4. What is the recommended fix?

Be direct and specific."""


def run_baseline_direct_llm(doc_snippet: str, live_state: dict) -> dict:
    """
    Runs Baseline 1 on a single sample.
    Returns a dict with the same keys the evaluator expects:
      drift_detected (bool), root_cause (str), raw_output (str), error (bool)
    """
    prompt = PROMPT.format(
        doc_snippet=doc_snippet,
        live_state=_live_state_to_text(live_state),
    )

    try:
        raw = _call_gemini(prompt)
    except Exception as e:
        return {"drift_detected": False, "root_cause": "IN_SYNC",
                "raw_output": f"[API ERROR]: {e}", "error": True}

    lower = raw.lower()

    # Drift detection — look for explicit yes/no
    if re.search(r'\byes\b', lower) or "drift detected" in lower or "configuration drift" in lower:
        drift = True
    elif re.search(r'\bno\b.*drift', lower) or "no drift" in lower or "in sync" in lower:
        drift = False
    else:
        # fallback: presence of problem keywords implies drift
        drift = any(w in lower for w in ["missing", "mismatch", "discrepanc", "not found",
                                          "not running", "not installed", "not set", "wrong"])

    # Root cause
    if not drift:
        root_cause = "IN_SYNC"
    elif "doc_fault" in lower or "doc fault" in lower or "documentation fault" in lower \
            or "documentation is outdated" in lower or "update the doc" in lower:
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
        print(f"Doc: {s['doc_snippet'][:100]}...")
        result = run_baseline_direct_llm(s["doc_snippet"], s["simulated_live_state"])
        print(f"Drift: {result['drift_detected']}  Root cause: {result['root_cause']}")
        print(f"Output preview: {result['raw_output'][:200]}")
