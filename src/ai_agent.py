"""
Autonomous LangGraph Agent Engine powered by Model Context Protocol (MCP).
Orchestrates multi-hop reasoning, parallel tool dispatching across multiple MCP servers,
conversational memory isolation, and real-time execution telemetry.
"""

import time
import asyncio
import logging
import operator
from typing import TypedDict, Annotated, Optional, Dict, Any, List
from dotenv import load_dotenv
from os import environ
import google.generativeai as genai

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# --- REMOVED DIRECT SERVICE IMPORTS ---
# We now use the standard MCP Client to decouple data sources from orchestrator logic
from src.mcp.client import mcp_client

load_dotenv()
GEMINI_API_KEY = environ.get("GEMINI_API_KEY")
logger = logging.getLogger(__name__)

# Initialize the Gemini SDK
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- LANGGRAPH STATE SCHEMA ---
class AgentState(TypedDict):
    """
    Defines the schema for the state passed between graph nodes.
    Supports parallel MCP tool executions, telemetry tracking, and append-only history.
    """
    system_prompt: str    
    query: str
    tool_calls: List[Dict[str, Any]]
    tool_result: Optional[str]
    all_tool_results: str 
    final_answer: Optional[str]
    # Append-only conversational memory reducer
    chat_history: Annotated[list, operator.add]
    # Execution telemetry and token metrics
    metrics: Dict[str, Any]


# --- ASYNCHRONOUS LANGGRAPH WORKFLOW NODES ---

async def agent_node(state: AgentState):
    """
    Asynchronous reasoning node.
    Evaluates conversational context and dynamically requests tools discovered via MCP.
    """
    start_time = time.perf_counter()
    logger.info("[Node: Agent] Initializing asynchronous reasoning phase with MCP tools...")
    
    # Dynamically inject MCP-discovered tools into the Gemini LLM
    model = genai.GenerativeModel(
        model_name="models/gemini-2.5-flash",
        tools=mcp_client.get_gemini_tool_declarations()
    )
    
    history_list = state.get("chat_history", [])
    chat_context = "\n".join(history_list)
    tool_history = state.get("all_tool_results", "")
    
    if tool_history:
        logger.info("   -> Synthesizing accumulated MCP tool results.")
        prompt = f"""
        System Rules: {state['system_prompt']}
        Previous Conversation Context: {chat_context}
        Original User Query: {state['query']}
        Data collected so far:
        {tool_history}
        
        Instructions:
        1. Review the collected data against the Original User Query.
        2. If a database query returned empty records ([]), DO NOT repeat the same query. Either try a fallback tool or conclude that the record does not exist.
        3. If all needed data is gathered, generate the final comprehensive answer adhering to formatting rules.
        """
    else:
        logger.info("   -> First pass: Analyzing user query.")
        prompt = f"""
        System Rules: {state['system_prompt']}
        Previous Conversation Context: {chat_context}
        Current User Query: {state['query']}
        """
        
    try:
        response = await model.generate_content_async(prompt)
        elapsed_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        usage = getattr(response, "usage_metadata", None)
        token_metrics = {
            "prompt_tokens": getattr(usage, "prompt_token_count", 0),
            "completion_tokens": getattr(usage, "candidates_token_count", 0),
            "total_tokens": getattr(usage, "total_token_count", 0)
        }
        
        existing_metrics = state.get("metrics", {}) or {}
        node_latencies = existing_metrics.get("node_latencies", [])
        node_latencies.append({"node": "agent_node", "latency_ms": elapsed_time_ms})
        
        updated_metrics = {
            **existing_metrics,
            "node_latencies": node_latencies,
            "latest_token_usage": token_metrics,
            "total_accumulated_tokens": existing_metrics.get("total_accumulated_tokens", 0) + token_metrics["total_tokens"]
        }
        
        logger.info(f"   -> [Telemetry] Agent Node finished in {elapsed_time_ms}ms. Tokens used: {token_metrics['total_tokens']}")
        
        candidate = response.candidates[0]
        extracted_tool_calls = []
        final_text_parts = []
        
        for part in candidate.content.parts:
            if part.function_call:
                func_name = part.function_call.name
                func_args = {k: v for k, v in part.function_call.args.items()}
                extracted_tool_calls.append({"name": func_name, "args": func_args})
            elif part.text:
                final_text_parts.append(part.text)
                
        if extracted_tool_calls:
            logger.info(f"   -> [Action Required] LLM requested {len(extracted_tool_calls)} MCP tool execution(s): {[tc['name'] for tc in extracted_tool_calls]}")
            return {
                "tool_calls": extracted_tool_calls,
                "metrics": updated_metrics
            }
        else:
            final_text = "".join(final_text_parts)
            logger.info("   -> Final response generated successfully.")
            return {
                "final_answer": final_text,
                "tool_calls": [],
                "chat_history": [f"AI: {final_text}"],
                "metrics": updated_metrics
            }
            
    except Exception as e:
        logger.error(f"Agent Node Encountered an Error: {e}", exc_info=True)
        return {"final_answer": "I encountered an error while processing the request.", "tool_calls": []}


async def tool_node(state: AgentState):
    """
    Asynchronous MCP tool execution node.
    Dispatches multiple tool calls concurrently to standalone MCP Servers via JSON-RPC.
    """
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        return {"tool_calls": []}

    logger.info(f"[Node: Tool] Initiating parallel MCP dispatch for {len(tool_calls)} tool(s)...")

    # Helper function to route individual tool request via the MCP Client
    async def execute_single_mcp_tool(call_item: Dict[str, Any]):
        tool_name = call_item.get("name")
        args = call_item.get("args", {})
        start_time = time.perf_counter()

        # Delegate execution entirely to the MCP Protocol Client Router
        mcp_response = await mcp_client.call_tool(tool_name, args)
        
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        serving_server = mcp_response.get("mcp_server", "Unknown")
        
        logger.info(f"   -> [Telemetry] MCP Tool '{tool_name}' on [{serving_server}] completed in {elapsed_ms}ms.")
        return {
            "tool": tool_name,
            "result": mcp_response.get("result", ""),
            "mcp_server": serving_server,
            "latency_ms": elapsed_ms
        }

    # Execute all requested MCP tools concurrently
    execution_results = await asyncio.gather(*[execute_single_mcp_tool(tc) for tc in tool_calls])

    existing_metrics = state.get("metrics", {}) or {}
    node_latencies = existing_metrics.get("node_latencies", [])
    accumulated_history = state.get("all_tool_results", "")

    for res in execution_results:
        node_latencies.append({
            "node": "tool_node",
            "tool": res["tool"],
            "mcp_server": res["mcp_server"],  # Added server metadata tracking!
            "latency_ms": res["latency_ms"]
        })
        accumulated_history += f"\n--- Data from MCP Tool: {res['tool']} ---\n{res['result']}\n"

    return {
        "all_tool_results": accumulated_history,
        "tool_calls": [],
        "metrics": {**existing_metrics, "node_latencies": node_latencies}
    }

def should_continue(state: AgentState):
    """
    Conditional routing edge function.
    Evaluates whether there are pending MCP tool calls to execute or if the graph should conclude.
    """
    tool_calls = state.get("tool_calls", [])
    if tool_calls and len(tool_calls) > 0:
        return "continue"
    return "end"

# ==========================================
# GLOBAL GRAPH CONFIGURATION
# ==========================================
memory = MemorySaver()
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("action", tool_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"continue": "action", "end": END})
workflow.add_edge("action", "agent")

app = workflow.compile(checkpointer=memory)

# --- MAIN ASYNC API ENTRY POINT ---
async def get_response_from_ai_agent(model_name: str, query: str, allow_search: bool, prompt: str, thread_id: str):
    """
    Asynchronous entry point for the FastAPI controller.
    Initializes multi-tool state, invokes the StateGraph using ainvoke,
    and returns a structured payload with the answer and MCP telemetry metrics.
    """
    total_start_time = time.perf_counter()
    logger.info(f"🚀 Invoking Asynchronous MCP-Powered Agent Workflow for query: {query}")
    
    try:
        initial_state = {
            "system_prompt": prompt,
            "query": query,
            "tool_calls": [],
            "tool_result": None,
            "all_tool_results": "",
            "final_answer": None,
            "chat_history": [f"User: {query}"],
            "metrics": {
                "node_latencies": [],
                "latest_token_usage": {},
                "total_accumulated_tokens": 0
            }
        }
        
        if not thread_id:
            thread_id = "default_session_id"
            
        # Runtime configuration with session checkpointing and recursion circuit breaker
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 8
        }
        
        # Non-blocking asynchronous graph execution
        final_state = await app.ainvoke(initial_state, config=config)
        
        total_time_ms = round((time.perf_counter() - total_start_time) * 1000, 2)
        answer = final_state.get("final_answer") or "Unable to generate a valid response."
        
        # Consolidate complete telemetry data
        metrics_data = final_state.get("metrics", {})
        metrics_data["total_latency_ms"] = total_time_ms
        
        logger.info(f"✅ Workflow completed in {total_time_ms}ms with {metrics_data.get('total_accumulated_tokens', 0)} total tokens.")
        
        return {
            "answer": answer,
            "metrics": metrics_data
        }
            
    except Exception as e:
        logger.error(f"Critical Workflow Failure: {e}", exc_info=True)
        error_message = (
            "The assistant reached the maximum reasoning steps without finding a complete answer. "
            "Please verify the requested identifiers." if "recursion limit" in str(e).lower()
            else "A system error occurred while processing your request. Please try again."
        )
        return {
            "answer": error_message,
            "metrics": {
                "total_latency_ms": round((time.perf_counter() - total_start_time) * 1000, 2),
                "error": str(e)
            }
        }