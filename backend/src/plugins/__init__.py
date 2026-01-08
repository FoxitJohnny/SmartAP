"""
SmartAP Plugin System

This package provides the extensibility framework for SmartAP,
allowing developers to create custom agents for invoice processing.
"""

from .base import (
    BaseAgent,
    BaseExtractorAgent,
    BaseValidatorAgent,
    BaseRiskAgent,
    AgentContext,
    AgentResult,
    AgentStatus,
)
from .registry import (
    PluginRegistry,
    registry,
    register_agent,
    get_agent,
    list_agents,
)

__all__ = [
    # Base classes
    "BaseAgent",
    "BaseExtractorAgent",
    "BaseValidatorAgent",
    "BaseRiskAgent",
    # Data classes
    "AgentContext",
    "AgentResult",
    "AgentStatus",
    # Registry
    "PluginRegistry",
    "registry",
    "register_agent",
    "get_agent",
    "list_agents",
]
