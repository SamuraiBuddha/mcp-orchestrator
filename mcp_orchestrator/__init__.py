"""MCP Orchestrator - The ONE MCP to rule them all"""

from .orchestrator import MCPOrchestrator
from .server import main

__version__ = "0.1.0"
__all__ = ["MCPOrchestrator", "main"]