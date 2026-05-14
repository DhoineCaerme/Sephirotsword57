"""
Three comparison baselines for evaluation:
  - baseline_direct_llm:        single zero-shot LLM prompt
  - baseline_regex:             pure regex pattern matching, zero API
  - baseline_single_agent_rag:  one generalised agent with chunked RAG context
"""

from baselines.baseline_direct_llm import run_baseline_direct_llm
from baselines.baseline_regex import run_baseline_regex
from baselines.baseline_single_agent_rag import run_baseline_single_agent_rag

__all__ = [
    "run_baseline_direct_llm",
    "run_baseline_regex",
    "run_baseline_single_agent_rag",
]
