#!/usr/bin/env python3
"""MCP Connection Manager - Handles communication with child MCP servers."""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
import os
import sys

logger = logging.getLogger("mcp-orchestrator.connection")

class MCPConnection:
    """Manages a connection to a child MCP server via stdio."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process = None
        self.reader = None
        self.writer = None
        self.request_id = 0
        self.pending_requests = {}
        
    async def connect(self):
        """Start the MCP server process and establish stdio communication."""
        cmd = [self.config["command"]] + self.config.get("args", [])
        
        # Set up environment with credentials if needed
        env = os.environ.copy()
        
        logger.info(f"Starting MCP server: {self.name} with command: {' '.join(cmd)}")
        
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        self.reader = self.process.stdout
        self.writer = self.process.stdin
        
        # Start reading responses
        asyncio.create_task(self._read_responses())
        
        # Send initialization
        await self._send_request({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "mcp-orchestrator",
                    "version": "0.1.0"
                }
            }
        })
        
    async def _read_responses(self):
        """Read responses from the MCP server."""
        while self.reader and not self.reader.at_eof():
            try:
                line = await self.reader.readline()
                if not line:
                    break
                    
                # Parse JSON-RPC response
                response = json.loads(line.decode())
                
                # Handle response
                if "id" in response and response["id"] in self.pending_requests:
                    future = self.pending_requests.pop(response["id"])
                    if "error" in response:
                        future.set_exception(Exception(response["error"]))
                    else:
                        future.set_result(response.get("result"))
                        
            except Exception as e:
                logger.error(f"Error reading from {self.name}: {e}")
                
    async def _send_request(self, request: Dict[str, Any]) -> Any:
        """Send a request to the MCP server and wait for response."""
        self.request_id += 1
        request["id"] = self.request_id
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request["id"]] = future
        
        # Send request
        request_json = json.dumps(request) + "\n"
        self.writer.write(request_json.encode())
        await self.writer.drain()
        
        # Wait for response
        return await future
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of tools from the MCP server."""
        result = await self._send_request({
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {}
        })
        return result.get("tools", [])
        
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        return await self._send_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        })
        
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            
class MCPConnectionPool:
    """Manages a pool of MCP connections."""
    
    def __init__(self):
        self.connections: Dict[str, MCPConnection] = {}
        self.connecting: Dict[str, asyncio.Lock] = {}
        
    async def get_connection(self, name: str, config: Dict[str, Any]) -> MCPConnection:
        """Get or create a connection to an MCP server."""
        if name in self.connections:
            return self.connections[name]
            
        # Ensure we only connect once even with concurrent requests
        if name not in self.connecting:
            self.connecting[name] = asyncio.Lock()
            
        async with self.connecting[name]:
            # Check again after acquiring lock
            if name in self.connections:
                return self.connections[name]
                
            # Create new connection
            connection = MCPConnection(name, config)
            await connection.connect()
            self.connections[name] = connection
            return connection
            
    async def close_all(self):
        """Close all connections."""
        for connection in self.connections.values():
            await connection.disconnect()
        self.connections.clear()

# Global connection pool
connection_pool = MCPConnectionPool()

async def execute_on_mcp(mcp_name: str, tool_name: str, arguments: Dict[str, Any], config: Dict[str, Any]) -> Any:
    """Execute a tool on a specific MCP server."""
    try:
        # Get connection from pool
        connection = await connection_pool.get_connection(mcp_name, config)
        
        # If tool_name is "auto", we need to figure out which tool to use
        if tool_name == "auto":
            # Get list of tools
            tools = await connection.list_tools()
            
            # Simple heuristic: use the first tool that seems relevant
            # In a real implementation, this would use semantic matching
            tool_name = tools[0]["name"] if tools else None
            
        if not tool_name:
            raise ValueError(f"No suitable tool found in {mcp_name}")
            
        # Call the tool
        result = await connection.call_tool(tool_name, arguments)
        return result
        
    except Exception as e:
        logger.error(f"Error executing on {mcp_name}: {e}")
        raise
