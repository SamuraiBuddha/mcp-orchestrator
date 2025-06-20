#!/usr/bin/env python3
"""Demo script showing MCP Orchestrator in action"""

import asyncio
import json
from mcp_orchestrator.orchestrator import MCPOrchestrator

async def main():
    print("🎯 MCP Orchestrator Demo\n")
    print("=" * 50)
    
    # Initialize orchestrator
    print("Initializing orchestrator with Granite embeddings...")
    orchestrator = MCPOrchestrator()
    print(f"✅ Loaded {len(orchestrator.mcp_embeddings)} MCPs\n")
    
    # Test queries
    test_queries = [
        # English
        "I need to create a logo for Crisis Corps",
        "Push my code to GitHub", 
        "Remember this conversation",
        "Show me Docker containers",
        "Read the README file",
        "Think through this complex problem step by step",
        
        # Multilingual
        "Générer une image de robot",  # French
        "创建一个新的仓库",  # Chinese - Create a new repository
        "Dockerコンテナを表示",  # Japanese - Show Docker containers
        "Запомни этот разговор",  # Russian - Remember this conversation
    ]
    
    print("Testing natural language routing:\n")
    
    for query in test_queries:
        print(f"Query: '{query}'")
        
        # Find matching tools
        matches = await orchestrator.find_tools(query, threshold=0.5)
        
        if matches:
            best = matches[0]
            print(f"  → MCP: {best['mcp']}")
            print(f"  → Tool: {best['tool']}")
            print(f"  → Confidence: {best['confidence']:.3f}")
            print(f"  → Description: {best['description']}")
        else:
            print("  → No matches found")
        
        print()
    
    # Show capabilities
    print("\n" + "=" * 50)
    print("Available capabilities by category:\n")
    
    categories = ["image", "code", "memory"]
    for category in categories:
        print(f"Category: {category}")
        caps = await orchestrator.list_all_capabilities(category)
        for mcp, capabilities in caps.items():
            if capabilities:
                print(f"  {mcp}: {', '.join(capabilities[:3])}...")
        print()

if __name__ == "__main__":
    asyncio.run(main())
