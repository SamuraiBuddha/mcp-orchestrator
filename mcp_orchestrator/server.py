#!/usr/bin/env python3
"""MCP Orchestrator Server - Universal router for all MCPs"""

import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .orchestrator import MCPOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
orchestrator = MCPOrchestrator()
server = Server("mcp-orchestrator")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List the 4 orchestrator tools that replace 100+ individual tools"""
    return [
        types.Tool(
            name="find_tool",
            description="Discover which MCP and tool to use for any task",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of what you want to do"
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Minimum confidence threshold (0-1)",
                        "default": 0.5
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="execute",
            description="Get routing info for executing any MCP tool by describing what you want to do",
            inputSchema={
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "Natural language request"
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional parameters for the tool"
                    }
                },
                "required": ["request"]
            }
        ),
        types.Tool(
            name="list_capabilities",
            description="List all available capabilities, optionally filtered by category",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g., 'image', 'code', 'memory')"
                    }
                }
            }
        ),
        types.Tool(
            name="explain_tool",
            description="Get detailed help for a specific MCP tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "mcp_name": {
                        "type": "string",
                        "description": "Name of the MCP"
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
async def handle_call_tool(
    name: str, arguments: Optional[Dict[str, Any]] = None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution"""
    try:
        if name == "find_tool":
            query = arguments.get("query", "")
            threshold = arguments.get("threshold", 0.5)
            
            results = await orchestrator.find_tools(query, threshold)
            
            if not results:
                return [types.TextContent(
                    type="text",
                    text="No matching tools found. Try rephrasing your request."
                )]
            
            # Format results
            output = "Found matching tools:\n\n"
            for result in results[:5]:  # Top 5 matches
                output += f"**{result['mcp']}** → {result['tool']}\n"
                output += f"  Confidence: {result['confidence']:.2f}\n"
                output += f"  Description: {result['description']}\n\n"
            
            return [types.TextContent(type="text", text=output)]
            
        elif name == "execute":
            request = arguments.get("request", "")
            params = arguments.get("params", {})
            
            # Find the best tool
            results = await orchestrator.find_tools(request, threshold=0.6)
            if not results:
                return [types.TextContent(
                    type="text",
                    text="Could not find a suitable tool for your request."
                )]
            
            best_match = results[0]
            
            # Return routing information instead of trying to execute
            output = f"To execute this request, use:\n\n"
            output += f"**Tool**: {best_match['tool']}\n"
            output += f"**From MCP**: {best_match['mcp']}\n"
            output += f"**Confidence**: {best_match['confidence']:.2f}\n\n"
            
            if params:
                output += f"**With parameters**:\n```json\n{json.dumps(params, indent=2)}\n```\n\n"
            
            output += f"Use the actual `{best_match['tool']}` tool from the MCP tools list to execute this."
            
            return [types.TextContent(type="text", text=output)]
            
        elif name == "list_capabilities":
            category = arguments.get("category")
            capabilities = await orchestrator.list_all_capabilities(category)
            
            output = "Available capabilities:\n\n"
            for mcp_name, mcp_caps in capabilities.items():
                output += f"**{mcp_name}**\n"
                for cap in mcp_caps:
                    output += f"  • {cap}\n"
                output += "\n"
            
            return [types.TextContent(type="text", text=output)]
            
        elif name == "explain_tool":
            mcp_name = arguments["mcp_name"]
            tool_name = arguments["tool_name"]
            
            # Get tool info from registry
            registry_path = Path(__file__).parent.parent / "config" / "registry.json"
            with open(registry_path, 'r') as f:
                registry = json.load(f)
            
            mcp_config = registry["mcps"].get(mcp_name, {})
            tools = mcp_config.get("tools", {})
            tool_config = tools.get(tool_name, {})
            
            doc = f"**{tool_name}** (from {mcp_name})\n\n"
            doc += f"Description: {tool_config.get('description', 'No description')}\n\n"
            
            if "parameters" in tool_config:
                doc += "Parameters:\n"
                for param, info in tool_config["parameters"].items():
                    doc += f"  • {param}: {info.get('description', '')}\n"
            
            if "examples" in tool_config:
                doc += "\nExamples:\n"
                for example in tool_config["examples"]:
                    doc += f"  • {example}\n"
            
            return [types.TextContent(type="text", text=doc)]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Tool execution error: {str(e)}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    """Run the MCP Orchestrator server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-orchestrator",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
