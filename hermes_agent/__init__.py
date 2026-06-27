"""
hermes_agent/ — 整合層
"""
from .plugin import (
    _pre_llm_call, _post_llm_call,
    get_current_time, get_bryan_absence,
)
from .tools import (
    validate_soul, SoulValidationResult, format_report,
    YuaSoulLoader, BuiltPrompt,
    YuaMemoryAdapter, AdapterResult,
)
from .agent import (
    YuaAgent, AgentConfig, AgentTurn,
    MockLLMProvider, LLMProvider,
    extract_fact_heuristic, FactExtractionResult,
)
from .llm_providers import MinimaxM3Provider, CachedLLMProvider

__all__ = [
    # plugin
    "_pre_llm_call", "_post_llm_call",
    "get_current_time", "get_bryan_absence",
    # tools
    "validate_soul", "SoulValidationResult", "format_report",
    "YuaSoulLoader", "BuiltPrompt",
    "YuaMemoryAdapter", "AdapterResult",
    # agent
    "YuaAgent", "AgentConfig", "AgentTurn",
    "MockLLMProvider", "LLMProvider",
    "extract_fact_heuristic", "FactExtractionResult",
    # llm providers
    "MinimaxM3Provider", "CachedLLMProvider",
]
