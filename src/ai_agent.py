"""
Autonomous LangGraph Agent Engine powered by Model Context Protocol (MCP).
Orchestrates multi-hop reasoning, parallel tool dispatching across multiple MCP servers,
conversational memory isolation, and real-time execution telemetry.
"""

import time
import asyncio
import logging
import operator
import json
from typing import TypedDict, Annotated, Optional, Dict, Any, List
from dotenv import load_dotenv
import os

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# --- UNIVERSAL LLM GATEWAY ---
import litellm
from src.mcp.client import mcp_client

load_dotenv()
# LiteLLM natively reads API keys from os.environ
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """Defines the state schema passed between graph nodes."""
    system_prompt: str    
    query: str
    tool_calls: List[Dict[str, Any]]
    tool_result: Optional[str]
    all_tool_results: str 
    final_answer: Optional[str]
    chat_history: Annotated[list, operator.add]
    metrics: Dict[str, Any]

async def agent_node(state: AgentState):
    """
    Asynchronous reasoning node utilizing LiteLLM Gateway.
    Evaluates conversational context, supports cross-model fallbacks, 
    and handles standardized OpenAI-format tool calling.
    """
    start_time = time.perf_counter()
    logger.info("[Node: Agent] Initializing LiteLLM reasoning phase with MCP tools...")
    
    # 1. Translate MCP Tool Schemas into Universal OpenAI Format
    universal_tools = []
    for tool_entry in mcp_client._tool_registry.values():
        mcp_schema = tool_entry["schema"]
        
        # 🛡️ Bulletproof extraction: Works for both MCP 1.x (inputSchema) and 2.x (input_schema)
        input_params = getattr(mcp_schema, "input_schema", getattr(mcp_schema, "inputSchema", {}))
        
        universal_tools.append({
            "type": "function",
            "function": {
                "name": mcp_schema.name,
                "description": mcp_schema.description,
                "parameters": input_params
            }
        })
    
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
        2. If a database query returned empty records ([]), DO NOT repeat the same query. Try a fallback tool or state it's missing.
        3. If all needed data is gathered, generate the final comprehensive answer.
        """
    else:
        logger.info("   -> First pass: Analyzing user query.")
        prompt = f"""
        System Rules: {state['system_prompt']}
        Previous Conversation Context: {chat_context}
        Current User Query: {state['query']}
        """
        
    try:
        # 2. Execute Universal LLM Call with High-Availability Fallback Routing
        response = await litellm.acompletion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            tools=universal_tools if universal_tools else None,
            fallbacks=["gemini/gemini-1.5-flash"],  # High Availability Safety Net
            num_retries=2
        )
        
        elapsed_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        message = response.choices[0].message
        
        # 3. Standardized Token Telemetry
        token_metrics = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
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
        
        logger.info(f"   -> [Telemetry] Gateway Node finished in {elapsed_time_ms}ms. Tokens used: {token_metrics['total_tokens']}")
        
        # 4. Standardized Tool Parsing (OpenAI Format)
        extracted_tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                func_name = tc.function.name
                func_args = json.loads(tc.function.arguments)
                extracted_tool_calls.append({"name": func_name, "args": func_args})
                
        if extracted_tool_calls:
            logger.info(f"   -> [Action Required] Gateway requested {len(extracted_tool_calls)} tool execution(s).")
            return {
                "tool_calls": extracted_tool_calls,
                "metrics": updated_metrics
            }
        else:
            final_text = message.content or ""
            logger.info("   -> Final response generated successfully.")
            return {
                "final_answer": final_text,
                "tool_calls": [],
                "chat_history": [f"AI: {final_text}"],
                "metrics": updated_metrics
            }
            
    except Exception as e:
        logger.error(f"Gateway Node Encountered an Error: {e}", exc_info=True)
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