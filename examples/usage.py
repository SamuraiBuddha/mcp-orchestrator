#!/usr/bin/env python3
"""Example usage of MCP Orchestrator."""

import asyncio
import json

# These examples show how Claude would use the orchestrator

async def example_find_tool():
    """Example: Finding the right tool for a task."""
    print("=== Finding Tools ===")
    
    queries = [
        "I need to generate a logo",
        "Check my GitHub notifications",
        "Remember this for later",
        "Run some JavaScript code",
        "Manage Docker containers"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        # In real usage, this would call the orchestrator
        # result = await orchestrator.find_tool(query)
        print("  → Would return the best MCP and tool for this task")

async def example_execute():
    """Example: Executing without knowing which MCP to use."""
    print("\n=== Direct Execution ===")
    
    requests = [
        {
            "request": "Generate a cyberpunk robot logo",
            "params": {"size": "1024x1024", "style": "dark and futuristic"}
        },
        {
            "request": "Create a new repository called mcp-orchestrator",
            "params": {"private": False, "description": "Universal MCP router"}
        },
        {
            "request": "Save this conversation to memory",
            "params": {"topic": "MCP Orchestrator Design"}
        }
    ]
    
    for req in requests:
        print(f"\nRequest: {req['request']}")
        print(f"Params: {req['params']}")
        # result = await orchestrator.execute(req['request'], req['params'])
        print("  → Orchestrator would route to the appropriate MCP")

async def example_discovery():
    """Example: Discovering available capabilities."""
    print("\n=== Capability Discovery ===")
    
    categories = [None, "image", "code", "file", "memory"]
    
    for category in categories:
        if category:
            print(f"\nCategory: {category}")
        else:
            print("\nAll capabilities:")
        # caps = await orchestrator.list_capabilities(category)
        print("  → Would list all relevant MCPs and their capabilities")

async def example_tool_help():
    """Example: Getting help for specific tools."""
    print("\n=== Tool Documentation ===")
    
    tools = [
        ("comfyui", "generate_image"),
        ("github", "create_repository"),
        ("memory", "search_nodes")
    ]
    
    for mcp_name, tool_name in tools:
        print(f"\nTool: {mcp_name}.{tool_name}")
        # help = await orchestrator.explain_tool(mcp_name, tool_name)
        print("  → Would show parameters, examples, and usage")

def main():
    """Run all examples."""
    print("MCP Orchestrator Usage Examples")
    print("=" * 40)
    
    asyncio.run(example_find_tool())
    asyncio.run(example_execute())
    asyncio.run(example_discovery())
    asyncio.run(example_tool_help())
    
    print("\n" + "=" * 40)
    print("Benefits:")
    print("- Claude only needs to know 4 tools instead of 100+")
    print("- Natural language routing to any MCP")
    print("- Central configuration and credentials")
    print("- Automatic tool discovery and help")

if __name__ == "__main__":
    main()
