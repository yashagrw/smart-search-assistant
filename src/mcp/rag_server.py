"""
Model Context Protocol (MCP) Server for Enterprise RAG & Policy Search.
Exposes Two-Stage Re-ranked ChromaDB retrieval over standardized JSON-RPC
protocols using the MCP 2.x specification.
"""

import os
import sys

# Ensure project root directory is in sys.path for standalone execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mcp.server.mcpserver import MCPServer
from src.services.rag_service import query_knowledge_base

# Initialize dedicated RAG MCP Server instance
rag_mcp_server = MCPServer("SmartSearch-RAG-MCPServer")

@rag_mcp_server.tool()
def search_company_policies(search_query: str) -> str:
    """
    Searches the company's internal unstructured knowledge base using Two-Stage Vector RAG
    (Stage 1: ChromaDB 3072-dim Bi-Encoder retrieval -> Stage 2: Cross-scoring Re-ranker).
    
    Use this tool when the user asks about any corporate policies across these departments:
    1. HR Policies: Paid Time Off (PTO), sick/parental/bereavement leaves, WFH stipends ($500), health insurance tiers, EAP mental health, PIP, or POSH rules.
    2. IT Security: Zero Trust VPN, MFA, password complexity (14 chars), incident reporting SLAs (P1/P2/P3), hardware replacement (MacBook/Dell), BYOD, or AI data privacy.
    3. Finance & Procurement: Airfare/hotel lodging caps (Tier 1/2/3 cities), daily meal per diem ($85), corporate credit cards, PO approval matrices ($5k to $100k+), or vendor onboarding.
    4. Customer Support & SLAs: Support ticket response times, order cancellation lockout windows, refund timelines (Card/Wire/ACH), escrow disputes, or VIP client rules.
    
    Args:
        search_query: The specific policy question or keywords extracted from the user's prompt.
    """
    try:
        return query_knowledge_base(search_query)
    except Exception as e:
        return f"RAG retrieval error: {str(e)}"

if __name__ == "__main__":
    # Start the RAG MCP server over standard stdio transport
    rag_mcp_server.run()