"""
Plugin Registry for SmartAP Agent System

Manages registration, discovery, and execution of custom agents.
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type
import logging

from .base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for all agents (built-in and custom).
    
    Handles:
    - Agent registration
    - Agent discovery (auto-scan plugins directory)
    - Agent retrieval by name
    - Dependency resolution
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent instance.
        
        Args:
            agent: Agent instance to register
        
        Raises:
            ValueError: If agent with same name already registered
        """
        if agent.name in self._agents:
            logger.warning(f"Agent '{agent.name}' already registered, overwriting")
        
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name} (v{agent.version})")
    
    def register_agent_class(self, name: str, agent_class: Type[BaseAgent]) -> None:
        """
        Register an agent class (lazy instantiation).
        
        Args:
            name: Unique name for the agent
            agent_class: Agent class to register
        
        Raises:
            ValueError: If not a subclass of BaseAgent
        """
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"{agent_class} must inherit from BaseAgent")
        
        self._agent_classes[name] = agent_class
        logger.info(f"Registered agent class: {name}")
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get agent by name.
        
        If agent class is registered but not instantiated, instantiate it.
        
        Args:
            name: Agent name
        
        Returns:
            Agent instance or None if not found
        """
        # Return existing instance
        if name in self._agents:
            return self._agents[name]
        
        # Instantiate from class if available
        if name in self._agent_classes:
            agent_class = self._agent_classes[name]
            agent = agent_class()
            self._agents[name] = agent
            return agent
        
        logger.warning(f"Agent '{name}' not found in registry")
        return None
    
    def list_agents(self) -> List[str]:
        """
        List all registered agent names.
        
        Returns:
            List of agent names
        """
        all_agents = set(self._agents.keys()) | set(self._agent_classes.keys())
        return sorted(all_agents)
    
    def get_agent_info(self, name: str) -> Optional[Dict]:
        """
        Get agent metadata.
        
        Args:
            name: Agent name
        
        Returns:
            Dictionary with agent metadata or None
        """
        agent = self.get_agent(name)
        if not agent:
            return None
        
        return {
            "name": agent.name,
            "version": agent.version,
            "description": agent.description,
            "dependencies": agent.dependencies,
            "class": agent.__class__.__name__
        }
    
    def discover_plugins(self, plugins_dir: Path) -> int:
        """
        Auto-discover and register agents from plugins directory.
        
        Scans for Python files in plugins_dir and registers any classes
        that inherit from BaseAgent.
        
        Args:
            plugins_dir: Path to plugins directory
        
        Returns:
            Number of agents discovered and registered
        """
        if not plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {plugins_dir}")
            return 0
        
        discovered = 0
        
        # Scan all .py files
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue  # Skip __init__.py and private files
            
            try:
                # Import module
                module_name = f"plugins.{plugin_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find agent classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseAgent) and obj != BaseAgent:
                        # Instantiate and register
                        try:
                            agent = obj()
                            self.register_agent(agent)
                            discovered += 1
                        except Exception as e:
                            logger.error(f"Failed to instantiate {name}: {e}")
            
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_file}: {e}")
        
        logger.info(f"Discovered {discovered} agents from {plugins_dir}")
        return discovered
    
    def resolve_dependencies(self, agent_name: str) -> List[str]:
        """
        Resolve agent dependencies in execution order.
        
        Uses topological sort to determine execution order.
        
        Args:
            agent_name: Name of agent to resolve dependencies for
        
        Returns:
            List of agent names in execution order (dependencies first)
        
        Raises:
            ValueError: If circular dependency detected
        """
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        visited = set()
        execution_order = []
        
        def visit(name: str, path: List[str]):
            if name in path:
                raise ValueError(f"Circular dependency detected: {' -> '.join(path + [name])}")
            
            if name in visited:
                return
            
            current_agent = self.get_agent(name)
            if not current_agent:
                raise ValueError(f"Dependency '{name}' not found")
            
            # Visit dependencies first
            for dep in current_agent.dependencies:
                visit(dep, path + [name])
            
            visited.add(name)
            execution_order.append(name)
        
        visit(agent_name, [])
        return execution_order


# Global registry instance
registry = PluginRegistry()


def register_agent(agent: BaseAgent) -> None:
    """Convenience function to register agent with global registry"""
    registry.register_agent(agent)


def get_agent(name: str) -> Optional[BaseAgent]:
    """Convenience function to get agent from global registry"""
    return registry.get_agent(name)


def list_agents() -> List[str]:
    """Convenience function to list all registered agents"""
    return registry.list_agents()
