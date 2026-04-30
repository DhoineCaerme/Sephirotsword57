import os
import json
import argparse
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai import LLM

from schemas import InfrastructureIntent, LiveSystemState, ReconciliationReport
from tools import SafeBashTool
from prompts import (
    INTENT_EXTRACTOR_SYSTEM,
    INTENT_EXTRACTOR_TASK,
    OS_PROBER_TASK,
    CAUSAL_RECONCILER_TASK,
)

load_dotenv()

LLM_MODEL = LLM(model="gemini/gemini-2.5-flash-lite", api_key=os.getenv("GEMINI_API_KEY"), temperature=0.1,
    max_tokens=5000)

# ── Agent factories ──────────────────────────────────────────────────────────

def create_intent_extractor() -> Agent:
    """Creates the Intent Extractor agent."""
    return Agent(
        role="Infrastructure Intent Extractor",
        goal=(
            "Extract all infrastructure requirements (ports, packages, services, env vars) "
            "from natural language documentation into a precise JSON schema."
        ),
        backstory=(
            "You are a senior DevOps engineer and parsing expert. "
            "You read operational documentation and accurately map out exactly what the "
            "server state needs to look like. You never guess — if something is missing "
            "or ambiguous, you flag it. You always output valid JSON and nothing else."
        ),
        verbose=True,
        allow_delegation=False,
        llm=LLM_MODEL,
        system_template=INTENT_EXTRACTOR_SYSTEM,
    )


def create_os_prober(mock_state: dict = None) -> Agent:
    """
    Creates the OS Prober agent.
    Pass mock_state to run in evaluation/mock mode using dataset telemetry.
    """
    tool = SafeBashTool(mock_dataset_state=mock_state)
    return Agent(
        role="Linux OS Telemetry Prober",
        goal=(
            "Use targeted, read-only Bash commands to verify whether each infrastructure "
            "requirement from the intent actually exists on the live system."
        ),
        backstory=(
            "You are a master Linux sysadmin. You know exactly which commands to run "
            "(ss -tuln, dpkg -l, systemctl is-active, docker ps, printenv) to check "
            "system state precisely. You run only non-destructive, targeted commands — "
            "never broad dumps. You report only what you confirmed, never what you assumed."
        ),
        verbose=True,
        allow_delegation=False,
        tools=[tool],
        llm=LLM_MODEL,
    )


def create_causal_reconciler() -> Agent:
    """Creates the Causal Reconciler agent."""
    return Agent(
        role="Causal Reconciler",
        goal=(
            "Compare the infrastructure intent against live system state, identify all "
            "discrepancies, classify the root cause as SYSTEM_FAULT or DOC_FAULT, "
            "and generate a safe remediation script or README patch."
        ),
        backstory=(
            "You are a senior SRE who specialises in configuration drift analysis. "
            "When you find a mismatch between what documentation says and what the system "
            "shows, you reason carefully about whether the system is wrong or the docs are "
            "outdated. You always produce a concrete, actionable fix."
        ),
        verbose=True,
        allow_delegation=False,
        llm=LLM_MODEL,
    )


# ── Task factories ────────────────────────────────────────────────────────────

def create_extraction_task(agent: Agent, doc_snippet: str) -> Task:
    return Task(
        description=INTENT_EXTRACTOR_TASK.format(doc_snippet=doc_snippet),
        expected_output="A structured JSON object matching the InfrastructureIntent schema.",
        agent=agent,
        output_pydantic=InfrastructureIntent,
    )


def create_probing_task(agent: Agent, intent: InfrastructureIntent) -> Task:
    intent_json = json.dumps(intent.model_dump(), indent=2)
    return Task(
        description=OS_PROBER_TASK.format(intent_json=intent_json),
        expected_output="A structured JSON object matching the LiveSystemState schema.",
        agent=agent,
        output_pydantic=LiveSystemState,
    )


def create_reconciliation_task(
    agent: Agent,
    intent: InfrastructureIntent,
    live_state: LiveSystemState,
    doc_snippet: str,
) -> Task:
    return Task(
        description=CAUSAL_RECONCILER_TASK.format(
            intent_json=json.dumps(intent.model_dump(), indent=2),
            live_state_json=json.dumps(live_state.model_dump(), indent=2),
            doc_snippet=doc_snippet,
        ),
        expected_output="A structured JSON object matching the ReconciliationReport schema.",
        agent=agent,
        output_pydantic=ReconciliationReport,
    )


# ── Pipeline orchestrators ────────────────────────────────────────────────────

def run_extraction(doc_snippet: str) -> InfrastructureIntent:
    """
    Stage 1: Run only the Intent Extractor on a documentation snippet.
    Returns an InfrastructureIntent pydantic object.
    """
    agent = create_intent_extractor()
    task = create_extraction_task(agent, doc_snippet)
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return result.pydantic


def run_full_pipeline(
    doc_snippet: str,
    mock_live_state: dict = None,
) -> tuple[InfrastructureIntent, LiveSystemState, ReconciliationReport]:

    # Stage 1: Extract intent from documentation
    print("\n[Stage 1/3] Running Intent Extractor...")
    extractor = create_intent_extractor()
    extraction_task = create_extraction_task(extractor, doc_snippet)
    extraction_crew = Crew(
        agents=[extractor],
        tasks=[extraction_task],
        process=Process.sequential,
        verbose=True,
    )
    intent: InfrastructureIntent = extraction_crew.kickoff().pydantic
    print(f"  → Intent extracted: {intent.model_dump()}")

    # Stage 2: Probe the OS (real or mock)
    print("\n[Stage 2/3] Running OS Prober...")
    prober = create_os_prober(mock_state=mock_live_state)
    probing_task = create_probing_task(prober, intent)
    probing_crew = Crew(
        agents=[prober],
        tasks=[probing_task],
        process=Process.sequential,
        verbose=True,
    )
    live_state: LiveSystemState = probing_crew.kickoff().pydantic
    print(f"  → Live state found: {live_state.model_dump()}")

    # Stage 3: Reconcile
    print("\n[Stage 3/3] Running Causal Reconciler...")
    reconciler = create_causal_reconciler()
    reconciliation_task = create_reconciliation_task(
        reconciler, intent, live_state, doc_snippet
    )
    reconciliation_crew = Crew(
        agents=[reconciler],
        tasks=[reconciliation_task],
        process=Process.sequential,
        verbose=True,
    )
    report: ReconciliationReport = reconciliation_crew.kickoff().pydantic

    return intent, live_state, report


# ── CLI entry point ───────────────────────────────────────────────────────────

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
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--readme", type=str, help="Path to a README.md file to analyse.")
    group.add_argument("--doc", type=str, help="Documentation text as a string.")
    group.add_argument("--demo", action="store_true", help="Run with a built-in demo snippet.")
    parser.add_argument(
        "--mock-state",
        type=str,
        default=None,
        help="Path to a JSON file containing simulated live state (for testing without a VM).",
    )
    args = parser.parse_args()

    # Resolve doc snippet
    if args.demo:
        doc_snippet = DEMO_DOC
        print(f"[DEMO MODE] Using built-in documentation snippet.")
    elif args.readme:
        with open(args.readme, "r") as f:
            doc_snippet = f.read()
        print(f"[README] Loaded from: {args.readme}")
    else:
        doc_snippet = args.doc

    # Resolve mock state (optional)
    mock_state = None
    if args.mock_state:
        with open(args.mock_state, "r") as f:
            mock_state = json.load(f)
        print(f"[MOCK] Using simulated live state from: {args.mock_state}")

    print(f"\n{'='*60}")
    print(f"DOCUMENTATION SNIPPET:\n{doc_snippet[:300]}{'...' if len(doc_snippet)>300 else ''}")
    print(f"{'='*60}\n")

    # Run pipeline
    try:
        intent, live_state, report = run_full_pipeline(doc_snippet, mock_live_state=mock_state)

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

        print(f"\nFull report JSON:\n{json.dumps(report.model_dump(), indent=2)}")

    except Exception as e:
        print(f"\n[ERROR]: {e}")
        print(
            "Tip: Make sure ANTHROPIC_API_KEY is set in your .env file "
            "and you have internet access."
        )


if __name__ == "__main__":
    main()
