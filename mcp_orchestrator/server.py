#!/usr/bin/env python3
"""MCP Orchestrator - The one MCP to rule them all."""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import subprocess
import sys
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server

# Import our connection manager
from .connection import execute_on_mcp, connection_pool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-orchestrator")

class MCPOrchestrator:
    """Orchestrates routing between multiple MCP servers."""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.registry = self._load_registry()
        self.credentials = self._load_credentials()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.capability_embeddings = self._compute_embeddings()
        
    def _load_registry(self) -> Dict[str, Any]:
        """Load MCP registry from config."""
        registry_path = self.config_path / "registry.json"
        if registry_path.exists():
            return json.loads(registry_path.read_text())
        return {"mcps": {}}
    
    def _load_credentials(self) -> Dict[str, Any]:
        """Load MCP credentials from config."""
        creds_path = self.config_path / "credentials.json"
        if creds_path.exists():
            return json.loads(creds_path.read_text())
        return {}
    
    def _compute_embeddings(self) -> Dict[str, np.ndarray]:
        """Pre-compute embeddings for all MCP capabilities."""
        embeddings = {}
        for mcp_name, mcp_config in self.registry.get("mcps", {}).items():
            capabilities = mcp_config.get("capabilities", [])
            if capabilities:
                # Combine all capabilities into one string for embedding
                combined = f"{mcp_config.get('description', '')} {' '.join(capabilities)}"
                embeddings[mcp_name] = self.model.encode([combined])[0]
        return embeddings
    
    def find_best_mcp(self, query: str) -> Tuple[str, float]:
        """Find the best MCP for a given query using semantic similarity."""
        query_embedding = self.model.encode([query])[0]
        best_mcp = None
        best_score = -1
        
        for mcp_name, mcp_embedding in self.capability_embeddings.items():
            score = cosine_similarity(
                query_embedding.reshape(1, -1),
                mcp_embedding.reshape(1, -1)
            )[0][0]
            
            if score > best_score:
                best_score = score
                best_mcp = mcp_name
        
        return best_mcp, best_score
    
    def list_all_capabilities(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """List all available capabilities, optionally filtered by category."""
        capabilities = {}
        
        for mcp_name, mcp_config in self.registry.get("mcps", {}).items():
            mcp_caps = mcp_config.get("capabilities", [])
            
            if category:
                # Filter capabilities that match the category
                mcp_caps = [cap for cap in mcp_caps if category.lower() in cap.lower()]
            
            if mcp_caps:
                capabilities[mcp_name] = mcp_caps
        
        return capabilities
    
    def get_tool_info(self, mcp_name: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool."""
        mcp_config = self.registry.get("mcps", {}).get(mcp_name)
        if not mcp_config:
            return None
        
        tools = mcp_config.get("tools", {})
        return tools.get(tool_name)
    
    def get_mcp_config(self, mcp_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific MCP."""
        return self.registry.get("mcps", {}).get(mcp_name)

# Global orchestrator instance
orchestrator = None

def main():
    """Main entry point for the MCP orchestrator server."""
    global orchestrator
    
    # Initialize orchestrator with config directory
    config_path = Path.home() / ".mcp-orchestrator"
    config_path.mkdir(exist_ok=True)
    
    # Create default configs if they don't exist
    registry_path = config_path / "registry.json"
    if not registry_path.exists():
        default_registry = {
            "mcps": {
                "comfyui": {
                    "description": "AI image generation with Stable Diffusion",
                    "command": "python",
                    "args": ["-m", "mcp_comfyui"],
                    "capabilities": [
                        "generate images",
                        "create logos",
                        "AI art",
                        "stable diffusion",
                        "text to image",
                        "image generation"
                    ],
                    "tools": {
                        "generate_image": {
                            "description": "Generate an image from text prompt",
                            "examples": ["robot logo", "landscape painting"]
                        }
                    }
                },
                "github": {
                    "description": "GitHub repository and code management",
                    "command": "python",
                    "args": ["-m", "mcp_github"],
                    "capabilities": [
                        "create repository",
                        "manage code",
                        "pull requests",
                        "version control",
                        "git operations",
                        "issue tracking"
                    ]
                },
                "memory": {
                    "description": "Knowledge graph and memory persistence",
                    "command": "python",
                    "args": ["-m", "mcp_memory"],
                    "capabilities": [
                        "store information",
                        "knowledge graph",
                        "remember context",
                        "search memories",
                        "persistent storage"
                    ]
                },
                "docker": {
                    "description": "Docker container management",
                    "command": "python",
                    "args": ["-m", "mcp_docker"],
                    "capabilities": [
                        "manage containers",
                        "docker operations",
                        "container logs",
                        "image management",
                        "docker compose"
                    ]
                },
                "filesystem": {
                    "description": "File system operations",
                    "command": "python",
                    "args": ["-m", "mcp_filesystem"],
                    "capabilities": [
                        "read files",
                        "write files",
                        "list directories",
                        "file operations",
                        "manage folders"
                    ]
                }
            }
        }
        registry_path.write_text(json.dumps(default_registry, indent=2))
    
    orchestrator = MCPOrchestrator(config_path)
    
    # Create MCP server
    server = Server("mcp-orchestrator")
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available orchestrator tools."""
        return [
            Tool(
                name="find_tool",
                description="Find which MCP and tool to use for a given task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language description of what you want to do"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="execute",
                description="Execute a request without knowing which MCP to use - the orchestrator will route it",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": "What you want to do"
                        },
                        "params": {
                            "type": "object",
                            "description": "Optional parameters for the request"
                        }
                    },
                    "required": ["request"]
                }
            ),
            Tool(
                name="list_capabilities",
                description="List all available capabilities across all MCPs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional category to filter by (e.g., 'image', 'code', 'file')"
                        }
                    }
                }
            ),
            Tool(
                name="explain_tool",
                description="Get detailed information about a specific tool",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "mcp_name": {
                            "type": "string",
                            "description": "Name of the MCP server"
                        },
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the tool"
                        }
                    },
                    "required": ["mcp_name", "tool_name"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool calls."""
        
        if name == "find_tool":
            query = arguments["query"]
            mcp_name, confidence = orchestrator.find_best_mcp(query)
            
            if mcp_name and confidence > 0.3:
                mcp_config = orchestrator.registry["mcps"][mcp_name]
                tools = mcp_config.get("tools", {})
                
                response = {
                    "mcp": mcp_name,
                    "confidence": round(confidence, 2),
                    "description": mcp_config.get("description", ""),
                    "available_tools": list(tools.keys()) if tools else ["(tools not documented)"]
                }
                
                return [TextContent(
                    type="text",
                    text=f"Best match: {mcp_name} MCP (confidence: {response['confidence']})\n\n" +
                         f"Description: {response['description']}\n\n" +
                         f"Available tools: {', '.join(response['available_tools'])}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text="No suitable MCP found for this query. Try listing capabilities to see what's available."
                )]
        
        elif name == "execute":
            request = arguments["request"]
            params = arguments.get("params", {})
            
            # Find the best MCP for this request
            mcp_name, confidence = orchestrator.find_best_mcp(request)
            
            if mcp_name and confidence > 0.3:
                # Get MCP configuration
                mcp_config = orchestrator.get_mcp_config(mcp_name)
                if not mcp_config:
                    return [TextContent(
                        type="text",
                        text=f"Configuration not found for {mcp_name} MCP."
                    )]
                
                try:
                    # Actually execute on the MCP using our connection manager
                    result = await execute_on_mcp(mcp_name, "auto", params, mcp_config)
                    
                    # Format the result nicely
                    if isinstance(result, list) and len(result) > 0:
                        # Handle TextContent results
                        result_text = "\n".join([item.get("text", str(item)) for item in result])
                    else:
                        result_text = json.dumps(result, indent=2)
                    
                    return [TextContent(
                        type="text",
                        text=f"Routed to {mcp_name} MCP\n\nResult:\n{result_text}"
                    )]
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"Error executing on {mcp_name} MCP: {str(e)}"
                    )]
            else:
                return [TextContent(
                    type="text",
                    text="Could not determine which MCP to use for this request."
                )]
        
        elif name == "list_capabilities":
            category = arguments.get("category")
            capabilities = orchestrator.list_all_capabilities(category)
            
            result = []
            for mcp_name, caps in capabilities.items():
                result.append(f"**{mcp_name}**:")
                for cap in caps:
                    result.append(f"  - {cap}")
                result.append("")
            
            return [TextContent(
                type="text",
                text="\n".join(result) if result else "No capabilities found."
            )]
        
        elif name == "explain_tool":
            mcp_name = arguments["mcp_name"]
            tool_name = arguments["tool_name"]
            
            tool_info = orchestrator.get_tool_info(mcp_name, tool_name)
            
            if tool_info:
                result = [
                    f"Tool: {tool_name} (from {mcp_name} MCP)",
                    f"Description: {tool_info.get('description', 'No description')}",
                    ""
                ]
                
                if "examples" in tool_info:
                    result.append("Examples:")
                    for example in tool_info["examples"]:
                        result.append(f"  - {example}")
                
                return [TextContent(type="text", text="\n".join(result))]
            else:
                return [TextContent(
                    type="text",
                    text=f"Tool '{tool_name}' not found in {mcp_name} MCP."
                )]
        
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    # Register shutdown handler
    async def shutdown():
        """Clean up connections on shutdown."""
        await connection_pool.close_all()
    
    # Run the server
    logger.info("Starting MCP Orchestrator...")
    try:
        stdio_server(server).run()
    finally:
        # Clean up connections
        asyncio.run(shutdown())

if __name__ == "__main__":
    main()
