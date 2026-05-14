"""
Pydantic schemas defining the data contracts between the three agents.

Flow:
  Documentation text → InfrastructureIntent (from Intent Extractor)
                     ↘
                       → ReconciliationReport (from Causal Reconciler)
                     ↗
  Live system        → LiveSystemState (from OS Prober)
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class EnvVar(BaseModel):
    """Single environment variable specification."""
    name: str = Field(description="Environment variable name, e.g. DATABASE_URL")
    value: Optional[str] = Field(
        default="*",
        description="Expected value. Use '*' if only presence is required."
    )


class InfrastructureIntent(BaseModel):
    """What the documentation SAYS the system should look like."""
    required_ports: Optional[List[str]] = Field(
        default=[],
        description="Required listening port numbers as strings."
    )
    required_packages: Optional[List[str]] = Field(
        default=[],
        description="Required system packages."
    )
    required_services: Optional[List[str]] = Field(
        default=[],
        description="Required systemd services or Docker containers."
    )
    required_env_vars: Optional[List[EnvVar]] = Field(
        default=[],
        description="Required environment variables and expected values."
    )
    ambiguity_flags: Optional[List[str]] = Field(
        default=[],
        description="Warnings about vague or ambiguous documentation."
    )


class LiveSystemState(BaseModel):
    """What the OS Prober ACTUALLY finds on the live system."""
    active_ports: Optional[List[str]] = Field(
        default=[],
        description="Ports currently listening on the system."
    )
    installed_packages: Optional[List[str]] = Field(
        default=[],
        description="Required packages actually installed."
    )
    running_services: Optional[List[str]] = Field(
        default=[],
        description="Required services/containers actually running."
    )
    active_env_vars: Optional[List[EnvVar]] = Field(
        default=[],
        description="Required environment variables actually present."
    )


class Discrepancy(BaseModel):
    """A single mismatch between intent and live state."""
    field: str = Field(description="Field name: ports | packages | services | env_vars")
    expected: str = Field(description="Value from intent.")
    actual: str = Field(description="What the OS Prober found.")


class ReconciliationReport(BaseModel):
    """Final output: diagnosis, root cause, and remediation."""
    drift_detected: bool = Field(description="True if any discrepancy was found.")
    root_cause: Optional[str] = Field(
        default=None,
        description="SYSTEM_FAULT | DOC_FAULT | AMBIGUOUS | IN_SYNC"
    )
    discrepancies: Optional[List[Discrepancy]] = Field(
        default=[],
        description="All detected discrepancies."
    )
    remediation_bash: Optional[str] = Field(
        default=None,
        description="Safe Bash script to fix system faults."
    )
    remediation_markdown: Optional[str] = Field(
        default=None,
        description="Markdown patch suggestion for the README."
    )
    justification: Optional[str] = Field(
        default=None,
        description="One-sentence explanation of the root cause classification."
    )
