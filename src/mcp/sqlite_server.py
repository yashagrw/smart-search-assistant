"""
Model Context Protocol (MCP) Server for Smart Search Assistant.
Exposes SQLite relational database tools and full-text search routines
over standardized JSON-RPC protocols using MCP 2.x specification.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mcp.server.mcpserver import MCPServer
from src.services.project_service import project_service_v1
from src.services.order_service import order_service_v1
from src.services.global_search_service import global_search_service

# Initialize the Standalone MCP Server instance
mcp_server = MCPServer("SmartSearch-MCPServer")

# --- SQLITE DATABASE MCP TOOLS ---

@mcp_server.tool()
def search_project_database(sql_query: str) -> str:
    """
    Executes a SQL query on the 'projects' table to retrieve project information.
    Use this tool ONLY when the user asks about projects.
    
    Table Schema (projects):
    - id (INTEGER PRIMARY KEY)
    - name (TEXT) e.g., 'Project P185602'
    - groupNumber (TEXT) e.g., 'P64852978'
    - status (TEXT) e.g., 'open', 'cancelled'
    - client_id (INTEGER) Foreign key to client table
    - createdAt (TEXT) ISO format date string
    - updatedAt (TEXT) ISO format date string
    
    You can also JOIN with 'client' table (id, name) if client info is needed.
    
    Args:
        sql_query: A valid SQLite query string based on the provided schema. Do not include markdown formatting.
    """
    try:
        clean_sql = sql_query.replace("```sql", "").replace("```", "").strip()
        result = project_service_v1(clean_sql)
        return str(result)
    except Exception as e:
        return f"Database error: {str(e)}"

@mcp_server.tool()
def search_order_database(sql_query: str) -> str:
    """
    Executes a SQL query on the 'orders' table to retrieve order information.
    Use this tool ONLY when the user asks about orders.
    
    Table Schema (orders):
    - id (INTEGER PRIMARY KEY)
    - fileNum (TEXT) e.g., 'END1234567'
    - displayStatus (TEXT) e.g., 'open', 'cancelled', 'order_processing', 'closed'
    - status (TEXT) e.g., 'in_escrow', 'cancelled', 'closed'
    - address (TEXT) Full physical address
    - createdAt (TEXT) ISO format date string
    - updatedAt (TEXT) ISO format date string
    
    Args:
        sql_query: A valid SQLite query string based on the provided schema. Do not include markdown formatting.
    """
    try:
        clean_sql = sql_query.replace("```sql", "").replace("```", "").strip()
        result = order_service_v1(clean_sql)
        return str(result)
    except Exception as e:
        return f"Database error: {str(e)}"

@mcp_server.tool()
def search_global_database(keyword: str) -> str:
    """
    Performs a broad keyword search across all records using SQLite FTS5 (Full Text Search).
    Use this tool for generic database searches when the specific intent is unclear.
    
    Args:
        keyword: The primary search term or identifier extracted from the user's prompt.
    """
    try:
        result = global_search_service(keyword)
        return str(result)
    except Exception as e:
        return f"Search error: {str(e)}"

if __name__ == "__main__":
    # Runs the server using standard stdio transport protocol
    mcp_server.run()