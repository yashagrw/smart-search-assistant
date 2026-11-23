"""
Multi-Server Model Context Protocol (MCP) Client Router.
Connects to domain-specific MCP servers (SQLite Server and RAG Server),
performs dynamic tool discovery, and dispatches JSON-RPC tool invocations.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, List, Callable

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.logger import configure_logger
from src.mcp.sqlite_server import (
    mcp_server as sqlite_mcp_server,
    search_project_database,
    search_order_database,
    search_global_database,
)
from src.mcp.rag_server import (
    rag_mcp_server,
    search_company_policies,
)

logger = configure_logger(name="mcp_client", level=logging.INFO)

class MultiServerMCPClient:
    """
    Orchestrates tool discovery and execution across multiple domain-specific MCP servers.
    Decouples the LangGraph agent from underlying tool server implementations.
    """

    def __init__(self):
        # Register connected MCP Server instances
        self.servers = {
            "SQLite-MCP-Server": sqlite_mcp_server,
            "RAG-MCP-Server": rag_mcp_server,
        }
        
        # Map tool names to their owning MCP server and executable routines
        self._tool_registry: Dict[str, Dict[str, Any]] = {}
        self._discover_and_register_tools()

    def _discover_and_register_tools(self):
        """
        Queries all connected MCP servers to auto-discover registered tools and schemas.
        """
        callable_map = {
            "search_project_database": search_project_database,
            "search_order_database": search_order_database,
            "search_global_database": search_global_database,
            "search_company_policies": search_company_policies,
        }

        for server_name, server_instance in self.servers.items():
            mcp_tools = server_instance._tool_manager.list_tools()
            for tool in mcp_tools:
                self._tool_registry[tool.name] = {
                    "server_name": server_name,
                    "server_instance": server_instance,
                    "schema": tool,
                    "callable": callable_map.get(tool.name),
                }
                logger.info(f"[MCP Discovery] Registered tool '{tool.name}' from '{server_name}'")

    def get_gemini_tool_declarations(self) -> List[Callable]:
        """
        Returns the list of discovered tool callables containing docstring schemas
        compatible with Google Gemini's native function calling API.
        """
        return [
            entry["callable"]
            for entry in self._tool_registry.values()
            if entry["callable"] is not None
        ]

    def list_discovered_tools(self) -> List[Dict[str, str]]:
        """
        Returns metadata about all discovered tools and their respective MCP servers.
        """
        return [
            {"tool_name": name, "mcp_server": info["server_name"]}
            for name, info in self._tool_registry.items()
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches a tool invocation request to the appropriate MCP server asynchronously.
        Returns both the result string and the name of the MCP server that handled it.
        """
        if tool_name not in self._tool_registry:
            error_msg = f"Error: Tool '{tool_name}' is not registered in any connected MCP server."
            logger.error(error_msg)
            return {"result": error_msg, "mcp_server": "Unknown"}

        tool_info = self._tool_registry[tool_name]
        server_name = tool_info["server_name"]
        tool_func = tool_info["callable"]

        logger.info(f"[MCP Dispatch] Routing '{tool_name}' -> [{server_name}] with args: {arguments}")

        try:
            # Execute the MCP server tool in a non-blocking background thread
            result = await asyncio.to_thread(tool_func, **arguments)
            return {
                "result": str(result),
                "mcp_server": server_name
            }
        except Exception as e:
            logger.error(f"[MCP Fault] Execution failed on {server_name} for tool '{tool_name}': {e}", exc_info=True)
            return {
                "result": f"MCP Tool Execution Error ({server_name}): {str(e)}",
                "mcp_server": server_name
            }

# Singleton MCP Client instance for application-wide reuse
mcp_client = MultiServerMCPClient()