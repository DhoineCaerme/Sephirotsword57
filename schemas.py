from pydantic import BaseModel, Field
from typing import Optional, List


class EnvVar(BaseModel):
    name: str = Field(description="The environment variable name, e.g. DATABASE_URL")
    value: Optional[str] = Field(
        default="*",
        description="The expected value. Use '*' if only presence is required."
    )


# ── Intent schema (what the documentation SAYS should be true) ──────────────
class InfrastructureIntent(BaseModel):
    required_ports: Optional[List[str]] = Field(
        default=[],
        description="List of required port numbers as strings, e.g. ['8080', '443']."
    )
    required_packages: Optional[List[str]] = Field(
        default=[],
        description="List of required system packages, e.g. ['nginx', 'redis']."
    )
    required_services: Optional[List[str]] = Field(
        default=[],
        description="List of required systemd services or Docker containers, e.g. ['redis-server', 'postgresql']."
    )
    required_env_vars: Optional[List[EnvVar]] = Field(
        default=[],
        description="List of required environment variables with optional expected values."
    )
    ambiguity_flags: Optional[List[str]] = Field(
        default=[],
        description="Warnings about vague or ambiguous documentation, e.g. 'port not explicitly stated'."
    )


# ── Live state schema (what the OS Prober ACTUALLY finds) ───────────────────
class LiveSystemState(BaseModel):
    active_ports: Optional[List[str]] = Field(
        default=[],
        description="List of port numbers currently listening on the system."
    )
    installed_packages: Optional[List[str]] = Field(
        default=[],
        description="List of required packages that are actually installed."
    )
    running_services: Optional[List[str]] = Field(
        default=[],
        description="List of required services/containers that are actually running."
    )
    active_env_vars: Optional[List[EnvVar]] = Field(
        default=[],
        description="List of required environment variables that are actually present."
    )


# ── Reconciliation output schema ─────────────────────────────────────────────
class Discrepancy(BaseModel):
    field: str = Field(description="Which field drifted: ports | packages | services | env_vars")
    expected: str = Field(description="What the documentation says should exist.")
    actual: str = Field(description="What the OS Prober actually found.")


class ReconciliationReport(BaseModel):
    drift_detected: bool = Field(description="True if any discrepancy was found.")
    root_cause: Optional[str] = Field(
        default=None,
        description="SYSTEM_FAULT | DOC_FAULT | AMBIGUOUS | IN_SYNC"
    )
    discrepancies: Optional[List[Discrepancy]] = Field(
        default=[],
        description="List of all detected discrepancies."
    )
    remediation_bash: Optional[str] = Field(
        default=None,
        description="Safe Bash script to fix system faults. None if no system fault."
    )
    remediation_markdown: Optional[str] = Field(
        default=None,
        description="Markdown patch suggestion for the README. None if no doc fault."
    )
    justification: Optional[str] = Field(
        default=None,
        description="One-sentence explanation of the root cause classification."
    )
