"""
Sephirotsword57 — main entry point.

Orchestrates the three-agent pipeline:
  Stage 1: Intent Extractor   → InfrastructureIntent
  Stage 2: OS Prober          → LiveSystemState
  Stage 3: Causal Reconciler  → ReconciliationReport

Usage:
  python main.py --readme path/to/README.md
  python main.py --doc "your documentation text"
  python main.py --demo
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Tuple, Optional
from dotenv import load_dotenv
from crewai import Crew, Process, LLM

from agents.schemas import InfrastructureIntent, LiveSystemState, ReconciliationReport
from agents import (
    create_intent_extractor, create_extraction_task,
    create_os_prober, create_probing_task,
    create_causal_reconciler, create_reconciliation_task,
)

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("sephirotsword57")


# ── LLM provider selection ───────────────────────────────────────────────────

class LLMConfigError(Exception):
    """Raised when LLM provider configuration is invalid or missing."""


def build_llm() -> LLM:
    """
    Build the LLM instance based on the LLM_PROVIDER env variable.
    Supports gemini and groq. Validates API key presence before returning.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower().strip()

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMConfigError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set in .env"
            )
        log.info(f"[LLM] Using Gemini (gemini-2.0-flash)")
        return LLM(
            model="gemini/gemini-2.0-flash",
            api_key=api_key,
            temperature=0.1,
            max_tokens=1500,
        )

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise LLMConfigError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set in .env"
            )
        log.info(f"[LLM] Using Groq (llama-3.1-8b-instant)")
        return LLM(
            model="groq/llama-3.1-8b-instant",
            api_key=api_key,
            temperature=0.1,
            max_tokens=1500,
        )

    raise LLMConfigError(
        f"Unknown LLM_PROVIDER: {provider!r}. Use 'gemini' or 'groq'."
    )


# ── Rate limit handling ──────────────────────────────────────────────────────

INTER_STAGE_DELAY = int(os.getenv("INTER_STAGE_DELAY", "0"))


def maybe_pause(stage_name: str) -> None:
    """Pause between pipeline stages if rate limiting is needed."""
    if INTER_STAGE_DELAY > 0:
        log.info(f"  [Rate limit pause: waiting {INTER_STAGE_DELAY}s after {stage_name}...]")
        time.sleep(INTER_STAGE_DELAY)


# ── Report persistence ───────────────────────────────────────────────────────

def save_reconciliation_report(
    output_path: str,
    doc_snippet: str,
    intent: InfrastructureIntent,
    live_state: LiveSystemState,
    report: ReconciliationReport,
) -> None:
    """Save full reconciliation result as structured JSON."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    output = {
        "timestamp": datetime.now().isoformat(),
        "documentation": doc_snippet,
        "extracted_intent": intent.model_dump(),
        "live_system_state": live_state.model_dump(),
        "reconciliation_report": report.model_dump(),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    log.info(f"  → Report saved to: {output_path}")


# ── Pipeline orchestrators ───────────────────────────────────────────────────

def run_full_pipeline(
    doc_snippet: str,
    mock_live_state: Optional[dict] = None,
    save_report_path: Optional[str] = None,
    llm: Optional[LLM] = None,
) -> Tuple[InfrastructureIntent, LiveSystemState, ReconciliationReport]:
    """
    Run the full three-agent pipeline sequentially with robust error handling.

    Args:
        doc_snippet:       Documentation text to analyse.
        mock_live_state:   If set, OS Prober uses this simulated state.
        save_report_path:  If set, save the final report as JSON to this path.
        llm:               LLM instance. If None, builds from environment.

    Returns:
        (intent, live_state, report) as pydantic objects.

    Raises:
        LLMConfigError:    If LLM provider config is missing or invalid.
        RuntimeError:      If any pipeline stage fails after retries.
    """
    if llm is None:
        llm = build_llm()

    # ── Stage 1: Intent Extraction ────────────────────────────────────────
    log.info("[Stage 1/3] Running Intent Extractor...")
    try:
        extractor = create_intent_extractor(llm)
        task = create_extraction_task(extractor, doc_snippet)
        crew = Crew(
            agents=[extractor],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        intent: InfrastructureIntent = crew.kickoff().pydantic
        log.info(f"  → Intent: {intent.model_dump()}")
    except Exception as e:
        raise RuntimeError(f"Stage 1 (Intent Extractor) failed: {e}") from e

    maybe_pause("Stage 1")

    # ── Stage 2: OS Probing ──────────────────────────────────────────────
    log.info("[Stage 2/3] Running OS Prober...")
    try:
        prober = create_os_prober(llm, mock_state=mock_live_state)
        task = create_probing_task(prober, intent)
        crew = Crew(
            agents=[prober],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        live_state: LiveSystemState = crew.kickoff().pydantic
        log.info(f"  → Live state: {live_state.model_dump()}")
    except Exception as e:
        raise RuntimeError(f"Stage 2 (OS Prober) failed: {e}") from e

    maybe_pause("Stage 2")

    # ── Stage 3: Causal Reconciliation ───────────────────────────────────
    log.info("[Stage 3/3] Running Causal Reconciler...")
    try:
        reconciler = create_causal_reconciler(llm)
        task = create_reconciliation_task(reconciler, intent, live_state, doc_snippet)
        crew = Crew(
            agents=[reconciler],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        report: ReconciliationReport = crew.kickoff().pydantic
    except Exception as e:
        raise RuntimeError(f"Stage 3 (Causal Reconciler) failed: {e}") from e

    if save_report_path:
        save_reconciliation_report(save_report_path, doc_snippet, intent, live_state, report)

    return intent, live_state, report


# ── CLI entry point ──────────────────────────────────────────────────────────

DEMO_DOC = (
    "The frontend service communicates with the backend via port 8080. "
    "Ensure nginx is installed as the reverse proxy. "
    "The Redis cache container must be running as 'redis-server'. "
    "Set the DATABASE_URL environment variable before starting the app."
)


def main():
    parser = argparse.ArgumentParser(
        description="Sephirotsword57 — Documentation Drift Detector"
    )
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--readme", type=str, help="Path to a README.md file.")
    src_group.add_argument("--doc", type=str, help="Documentation text directly.")
    src_group.add_argument("--demo", action="store_true", help="Use built-in demo doc.")

    parser.add_argument("--mock-state", type=str, default=None,
                        help="Path to JSON file with simulated live state.")
    parser.add_argument("--save-report", type=str, default=None,
                        help="Path to save the JSON reconciliation report.")
    args = parser.parse_args()

    # Resolve documentation source
    if args.demo:
        doc_snippet = DEMO_DOC
        log.info("[DEMO MODE] Using built-in documentation snippet.")
    elif args.readme:
        try:
            with open(args.readme, "r", encoding="utf-8") as f:
                doc_snippet = f.read()
            log.info(f"[README] Loaded from: {args.readme}")
        except FileNotFoundError:
            log.error(f"README file not found: {args.readme}")
            sys.exit(1)
        except Exception as e:
            log.error(f"Could not read README: {e}")
            sys.exit(1)
    else:
        doc_snippet = args.doc

    # Resolve mock state (optional)
    mock_state = None
    if args.mock_state:
        try:
            with open(args.mock_state, "r", encoding="utf-8") as f:
                mock_state = json.load(f)
            log.info(f"[MOCK] Using simulated live state from: {args.mock_state}")
        except FileNotFoundError:
            log.error(f"Mock state file not found: {args.mock_state}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            log.error(f"Mock state JSON is invalid: {e}")
            sys.exit(1)

    # Auto-generate a save path if not specified
    save_path = args.save_report
    if save_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"outputs/report_{ts}.json"

    print(f"\n{'='*60}")
    print(f"DOCUMENTATION:\n{doc_snippet[:300]}{'...' if len(doc_snippet) > 300 else ''}")
    print(f"{'='*60}\n")

    # Run pipeline
    try:
        intent, live_state, report = run_full_pipeline(
            doc_snippet,
            mock_live_state=mock_state,
            save_report_path=save_path,
        )

        print(f"\n{'='*60}")
        print("RECONCILIATION REPORT")
        print(f"{'='*60}")
        print(f"Drift Detected : {report.drift_detected}")
        print(f"Root Cause     : {report.root_cause}")
        print(f"Justification  : {report.justification}")

        if report.discrepancies:
            print("\nDiscrepancies:")
            for d in report.discrepancies:
                print(f"  [{d.field}] Expected: {d.expected} | Actual: {d.actual}")

        if report.remediation_bash:
            print(f"\nBash Remediation:\n{report.remediation_bash}")
        if report.remediation_markdown:
            print(f"\nMarkdown Patch:\n{report.remediation_markdown}")

    except LLMConfigError as e:
        log.error(f"LLM configuration error: {e}")
        log.error("Check your .env file. Required: LLM_PROVIDER + matching API key.")
        sys.exit(2)
    except RuntimeError as e:
        log.error(f"Pipeline error: {e}")
        sys.exit(3)
    except KeyboardInterrupt:
        log.warning("Interrupted by user.")
        sys.exit(130)
    except Exception as e:
        log.error(f"Unexpected error: {e.__class__.__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
