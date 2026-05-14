"""
Intent Extractor Agent (Stage 1).

Reads unstructured operational documentation (README, runbook) and produces
a strict JSON schema describing what the documentation REQUIRES the system
to look like.
"""

import json
from crewai import Agent, Task

from agents.schemas import InfrastructureIntent


INTENT_EXTRACTOR_SYSTEM = """You extract infrastructure requirements from DevOps documentation.

Output ONLY a valid JSON object matching this schema:
{
  "required_ports": [string],
  "required_packages": [string],
  "required_services": [string],
  "required_env_vars": [{"name": string, "value": string}],
  "ambiguity_flags": [string]
}

Rules:
- Ports must be strings ("8080" not 8080).
- Use empty list [] for any field with nothing.
- Use "*" for env var values when only presence is required.
- Add to ambiguity_flags if docs are vague.
- Never invent values not in the text.
- No markdown fences, no explanations, only JSON.
"""

INTENT_EXTRACTOR_TASK = """Documentation:
\"\"\"{doc_snippet}\"\"\"

Output the JSON only."""


def create_intent_extractor(llm) -> Agent:
    """Build the Intent Extractor agent with the provided LLM."""
    return Agent(
        role="Infrastructure Intent Extractor",
        goal=(
            "Extract all infrastructure requirements (ports, packages, services, "
            "env vars) from documentation into a precise JSON schema."
        ),
        backstory=(
            "You are a senior DevOps engineer and parsing expert. "
            "You read operational documentation and accurately map out exactly "
            "what the server state needs to look like. You never guess — if "
            "something is missing or ambiguous, you flag it. You always output "
            "valid JSON and nothing else."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
        system_template=INTENT_EXTRACTOR_SYSTEM,
    )


def create_extraction_task(agent: Agent, doc_snippet: str) -> Task:
    """Build the extraction task for a given documentation snippet."""
    return Task(
        description=INTENT_EXTRACTOR_TASK.format(doc_snippet=doc_snippet),
        expected_output="A structured JSON object matching the InfrastructureIntent schema.",
        agent=agent,
        output_pydantic=InfrastructureIntent,
    )
