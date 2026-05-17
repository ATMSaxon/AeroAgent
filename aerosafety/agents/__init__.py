"""
aerosafety.agents — Agent system implementations for AeroSafetyEval.

Systems available:
  System 1: DirectLLMAgent      — no retrieval, no tools (baseline)
  System 2: RAGAgent            — pluggable retriever, BM25 default
  System 3: ToolAugmentedAgent  — tool calling with validated outputs
  System 4: MultiAgentSystem    — sequential role-specialised pipeline
  System 5: AeroSFTAgent        — NOT IMPLEMENTED (Phase 2, GPU training)
  System 6: AeroDPOAgent        — NOT IMPLEMENTED (Phase 2, GPU training)
  System 7: VerifierGatedAgent  — wraps System 3 + 6 independent verifiers

All agents produce a full AgentTrace (aerosafety.io.AgentTrace).
No agent silently degrades — errors surface per CLAUDE.md §8.1.
"""

from aerosafety.agents.base import AgentBase
from aerosafety.agents.llm_client import LLMClient
from aerosafety.agents.mock_llm import MockLLM
from aerosafety.agents.system1_direct import DirectLLMAgent
from aerosafety.agents.system2_rag import BM25Retriever, RAGAgent, Retriever
from aerosafety.agents.system3_tool_aug import ToolAugmentedAgent
from aerosafety.agents.system4_multi_agent import MultiAgentSystem
from aerosafety.agents.system5_aero_sft import AeroSFTAgent
from aerosafety.agents.system6_aero_dpo import AeroDPOAgent
from aerosafety.agents.system7_verifier_gated import VerifierGatedAgent

__all__ = [
    "AgentBase",
    "LLMClient",
    "MockLLM",
    "DirectLLMAgent",
    "RAGAgent",
    "BM25Retriever",
    "Retriever",
    "ToolAugmentedAgent",
    "MultiAgentSystem",
    "AeroSFTAgent",
    "AeroDPOAgent",
    "VerifierGatedAgent",
]
