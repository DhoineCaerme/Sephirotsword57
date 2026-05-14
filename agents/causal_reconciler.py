"""
Causal Reconciler Agent (Stage 3).

Compares the Infrastructure Intent against the Live System State, identifies
discrepancies, classifies root cause (SYSTEM_FAULT vs DOC_FAULT), and
generates a safe remediation Bash script or Markdown patch.
"""

import json
from crewai import Agent, Task

from agents.schemas import (
    InfrastructureIntent,
    LiveSystemState,
    ReconciliationReport,
)


CAUSAL_RECONCILER_TASK = """Compare INTENT vs LIVE STATE:

INTENT: {intent_json}
LIVE: {live_state_json}
DOC: \"\"\"{doc_snippet}\"\"\"

Field mapping:
- required_ports ↔ active_ports
- required_packages ↔ installed_packages
- required_services ↔ running_services
- required_env_vars ↔ active_env_vars (by name)

For EACH item in intent, check if its EXACT name is in the matching live field.
NOT present → DISCREPANCY. Other items running do not count.
Example: required ["redis-server"], live ["postgres","nginx"] → redis-server missing → DISCREPANCY.

Root cause:
- SYSTEM_FAULT: required item missing/wrong on system
- DOC_FAULT: many ambiguity_flags or live has reasonable alternative
- IN_SYNC: ZERO discrepancies only
- AMBIGUOUS: unclear

Remediation:
- SYSTEM_FAULT → Bash script to fix
- DOC_FAULT → Markdown patch for README
- IN_SYNC → both null

Output only the ReconciliationReport JSON.
"""


def create_causal_reconciler(llm) -> Agent:
    """Build the Causal Reconciler agent."""
    return Agent(
        role="Causal Reconciler",
        goal=(
            "Compare the infrastructure intent against live system state, "
            "identify all discrepancies, classify the root cause as SYSTEM_FAULT "
            "or DOC_FAULT, and generate a safe remediation script or README patch."
        ),
        backstory=(
            "You are a senior SRE who specialises in configuration drift analysis. "
            "When you find a mismatch between what documentation says and what "
            "the system shows, you reason carefully about whether the system is "
            "wrong or the docs are outdated. You always produce a concrete, "
            "actionable fix."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )


def create_reconciliation_task(
    agent: Agent,
    intent: InfrastructureIntent,
    live_state: LiveSystemState,
    doc_snippet: str,
) -> Task:
    """Build the reconciliation task using both data sources."""
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
