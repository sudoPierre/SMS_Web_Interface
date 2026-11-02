"""LLM agent for natural-language SMS ("Allume le salon").

Tools are async Python functions registered with @agent_tool; every module in
agent/tools/ is imported by load_tools(), so adding a tool only means adding a file.
"""
from .loop import is_enabled, run_agent
from .registry import AgentTool, agent_tool, get_tools, load_tools

__all__ = ["AgentTool", "agent_tool", "get_tools", "is_enabled", "load_tools", "run_agent"]
