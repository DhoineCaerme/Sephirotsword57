"""
OS Prober Agent (Stage 2).

Takes the JSON Infrastructure Intent and probes the live Linux system using
targeted, read-only Bash commands. Returns a LiveSystemState describing what
actually exists on the system right now.
"""

import json
from crewai import Agent, Task

from agents.schemas import InfrastructureIntent, LiveSystemState
from sandbox.safe_bash_tool import SafeBashTool


OS_PROBER_TASK = """Verify which of these requirements are present on the system:
{intent_json}

Use SafeBashTool with these commands:
- Ports:    ss -tuln | grep :<PORT>
- Packages: dpkg -l <NAME>
- Services: systemctl is-active <NAME>  OR  docker ps --filter name=<NAME>
- Env vars: printenv <NAME>

Run ONE command per requirement. Read the RESULT line of each tool output.
- "IS active/running/installed" → add to live state
- "is NOT active/running/installed" or "[]" → do NOT add

Output only the LiveSystemState JSON: active_ports, installed_packages,
running_services, active_env_vars."""


def create_os_prober(llm, mock_state: dict = None) -> Agent:
    """
    Build the OS Prober agent.
    Pass mock_state to run in evaluation mode using simulated telemetry.
    """
    tool = SafeBashTool(mock_dataset_state=mock_state)
    return Agent(
        role="Linux OS Telemetry Prober",
        goal=(
            "Use targeted, read-only Bash commands to verify whether each "
            "infrastructure requirement from the intent actually exists on the "
            "live system."
        ),
        backstory=(
            "You are a master Linux sysadmin. You know exactly which commands "
            "to run (ss -tuln, dpkg -l, systemctl is-active, docker ps, printenv) "
            "to check system state precisely. You run only non-destructive, "
            "targeted commands — never broad dumps. You report only what you "
            "confirmed, never what you assumed."
        ),
        verbose=True,
        allow_delegation=False,
        tools=[tool],
        llm=llm,
    )


def create_probing_task(agent: Agent, intent: InfrastructureIntent) -> Task:
    """Build the probing task using the extracted intent."""
    intent_json = json.dumps(intent.model_dump(), indent=2)
    return Task(
        description=OS_PROBER_TASK.format(intent_json=intent_json),
        expected_output="A structured JSON object matching the LiveSystemState schema.",
        agent=agent,
        output_pydantic=LiveSystemState,
    )
