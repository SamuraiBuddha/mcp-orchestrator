"""Core orchestrator logic with embedding-based routing"""

import json
import numpy as np
import requests
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ToolMatch:
    """Represents a matched tool with metadata"""
    mcp: str
    tool: str
    confidence: float
    description: str
    capabilities: List[str]

class MCPOrchestrator:
    """Intelligent router for MCP tools using Granite embeddings"""
    
    def __init__(self, 
                 registry_path: str = "config/registry.json",
                 lm_studio_url: str = "http://127.0.0.1:1234"):
        self.lm_studio_url = lm_studio_url
        self.embedding_model = "text-embedding-granite-embedding-278m-multilingual"
        self.embedding_cache = {}
        
        # Load registry
        registry_file = Path(registry_path)
        if not registry_file.exists():
            # Use default registry
            registry_file = Path(__file__).parent.parent / "config" / "registry.json"
        
        with open(registry_file, 'r') as f:
            self.registry = json.load(f)
        
        # Pre-compute embeddings
        logger.info("Pre-computing MCP embeddings...")
        self.mcp_embeddings = self._compute_mcp_embeddings()
        self.tool_embeddings = self._compute_tool_embeddings()
        logger.info(f"Computed embeddings for {len(self.mcp_embeddings)} MCPs")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding from Granite via LM Studio with caching"""
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        try:
            response = requests.post(
                f"{self.lm_studio_url}/v1/embeddings",
                json={
                    "model": self.embedding_model,
                    "input": text
                },
                timeout=5.0
            )
            response.raise_for_status()
            
            embedding = np.array(response.json()["data"][0]["embedding"])
            self.embedding_cache[text] = embedding
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}")
            # Fallback to random embedding if service unavailable
            return np.random.randn(768)
    
    def _compute_mcp_embeddings(self) -> Dict[str, np.ndarray]:
        """Pre-compute embeddings for all MCP capabilities"""
        embeddings = {}
        
        for mcp_name, mcp_config in self.registry.get("mcps", {}).items():
            # Combine all descriptive text
            text_parts = [
                mcp_config.get("description", ""),
                " ".join(mcp_config.get("capabilities", [])),
                " ".join(mcp_config.get("keywords", []))
            ]
            combined_text = " ".join(filter(None, text_parts))
            
            if combined_text:
                embeddings[mcp_name] = self.get_embedding(combined_text)
        
        return embeddings
    
    def _compute_tool_embeddings(self) -> Dict[str, np.ndarray]:
        """Pre-compute embeddings for individual tools"""
        embeddings = {}
        
        for mcp_name, mcp_config in self.registry.get("mcps", {}).items():
            tools = mcp_config.get("tools", {})
            
            for tool_name, tool_config in tools.items():
                # Create unique key
                tool_key = f"{mcp_name}::{tool_name}"
                
                # Combine tool description and examples
                text_parts = [
                    tool_config.get("description", ""),
                    " ".join(tool_config.get("examples", [])),
                    " ".join(tool_config.get("keywords", []))
                ]
                combined_text = " ".join(filter(None, text_parts))
                
                if combined_text:
                    embeddings[tool_key] = self.get_embedding(combined_text)
        
        return embeddings
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    async def find_tools(self, query: str, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Find matching tools for a query"""
        query_embedding = self.get_embedding(query)
        matches = []
        
        # Check MCP-level matches
        for mcp_name, mcp_embedding in self.mcp_embeddings.items():
            score = self.cosine_similarity(query_embedding, mcp_embedding)
            
            if score >= threshold:
                mcp_config = self.registry["mcps"][mcp_name]
                matches.append({
                    "mcp": mcp_name,
                    "tool": "*",  # All tools
                    "confidence": score,
                    "description": mcp_config.get("description", ""),
                    "capabilities": mcp_config.get("capabilities", [])
                })
        
        # Check individual tool matches
        for tool_key, tool_embedding in self.tool_embeddings.items():
            score = self.cosine_similarity(query_embedding, tool_embedding)
            
            if score >= threshold:
                mcp_name, tool_name = tool_key.split("::", 1)
                tool_config = self.registry["mcps"][mcp_name]["tools"][tool_name]
                
                matches.append({
                    "mcp": mcp_name,
                    "tool": tool_name,
                    "confidence": score,
                    "description": tool_config.get("description", ""),
                    "capabilities": []
                })
        
        # Sort by confidence
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Remove duplicates, keeping highest confidence
        seen = set()
        unique_matches = []
        for match in matches:
            key = f"{match['mcp']}::{match['tool']}"
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        return unique_matches
    
    async def list_all_capabilities(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """List all available capabilities, optionally filtered"""
        capabilities = {}
        
        for mcp_name, mcp_config in self.registry.get("mcps", {}).items():
            # Filter by category if specified
            if category:
                keywords = mcp_config.get("keywords", [])
                if category.lower() not in [k.lower() for k in keywords]:
                    continue
            
            capabilities[mcp_name] = mcp_config.get("capabilities", [])
        
        return capabilities