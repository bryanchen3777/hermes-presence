"""
hermes_agent/ — hermes-presence 整合層
"""
from .plugin import (
    _pre_llm_call, _post_llm_call,
    get_current_time, get_bryan_absence,
)
from .tools import (
    validate_soul, SoulValidationResult, format_report,
    YuaSoulLoader, BuiltPrompt,
    YuaMemoryAdapter, AdapterResult,
    ParsedPalaceFile, parse_palace_md, parse_palace_dir,
    parse_sage_sqlite, palace_to_fact, sage_to_fact,
    discover_hermes_roots,
)
from .agent import (
    YuaAgent, AgentConfig, LLMProvider,
    MockLLMProvider, AgentTurn,
    extract_fact_heuristic, FactExtractionResult,
)
from .llm_providers import (
    MinimaxM3Provider,
    LocalLLMProvider,
)

__all__ = [
    # plugin
    "_pre_llm_call", "_post_llm_call",
    "get_current_time", "get_bryan_absence",
    # tools
    "validate_soul", "SoulValidationResult", "format_report",
    "YuaSoulLoader", "BuiltPrompt",
    "YuaMemoryAdapter", "AdapterResult",
    "ParsedPalaceFile", "parse_palace_md", "parse_palace_dir",
    "parse_sage_sqlite", "palace_to_fact", "sage_to_fact",
    "discover_hermes_roots",
    # agent
    "YuaAgent", "AgentConfig", "AgentTurn",
    "MockLLMProvider", "LLMProvider",
    "extract_fact_heuristic", "FactExtractionResult",
    # llm providers
    "MinimaxM3Provider", "LocalLLMProvider",
]
