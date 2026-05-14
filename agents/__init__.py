"""
Sephirotsword57 — Agent package.

Each agent lives in its own module for clean separation of concerns:
  - intent_extractor.py:   Stage 1 - parses documentation into a JSON intent schema
  - os_prober.py:          Stage 2 - probes the live OS for actual state
  - causal_reconciler.py:  Stage 3 - compares intent vs live state and generates fix

NOTE: Agent factories are imported lazily so that schemas.py can be imported
without requiring crewai to be installed (useful for unit tests).
"""

# Schemas are always safe to import (pydantic only)
from agents.schemas import (
    EnvVar,
    InfrastructureIntent,
    LiveSystemState,
    Discrepancy,
    ReconciliationReport,
)


def __getattr__(name):
    """Lazy-load agent factory functions only when first accessed."""
    if name == "create_intent_extractor" or name == "create_extraction_task":
        from agents.intent_extractor import (
            create_intent_extractor, create_extraction_task
        )
        return locals()[name]
    if name == "create_os_prober" or name == "create_probing_task":
        from agents.os_prober import (
            create_os_prober, create_probing_task
        )
        return locals()[name]
    if name == "create_causal_reconciler" or name == "create_reconciliation_task":
        from agents.causal_reconciler import (
            create_causal_reconciler, create_reconciliation_task
        )
        return locals()[name]
    raise AttributeError(f"module 'agents' has no attribute {name!r}")


__all__ = [
    # Schemas (always available)
    "EnvVar",
    "InfrastructureIntent",
    "LiveSystemState",
    "Discrepancy",
    "ReconciliationReport",
    # Agent factories (loaded lazily)
    "create_intent_extractor",
    "create_extraction_task",
    "create_os_prober",
    "create_probing_task",
    "create_causal_reconciler",
    "create_reconciliation_task",
]
