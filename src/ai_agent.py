import time
import asyncio
import logging
import operator
from typing import TypedDict, Annotated, Optional, Dict, Any, List
from dotenv import load_dotenv
from os import environ
import google.generativeai as genai

# Core LangGraph imports for state management and routing
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Service imports for database and search logic
from src.services.project_service import project_service_v1
from src.services.order_service import order_service_v1
from src.services.global_search_service import global_search_service
from src.services.rag_service import query_knowledge_base

# --- ENVIRONMENT CONFIGURATION ---
load_dotenv()
GEMINI_API_KEY = environ.get("GEMINI_API_KEY")
logger = logging.getLogger(__name__)

# Initialize the Gemini SDK
genai.configure(api_key=GEMINI_API_KEY)

# --- LANGGRAPH STATE SCHEMA (MULTI-TOOL & TELEMETRY SUPPORT) ---
class AgentState(TypedDict):
    """
    Defines the state schema passed between graph nodes.
    Supports parallel tool executions, telemetry tracking, and append-only history.
    """
    system_prompt: str    
    query: str
    tool_calls: List[Dict[str, Any]]
    tool_result: Optional[str]
    all_tool_results: str 
    final_answer: Optional[str]
    # Append-only conversational memory
    chat_history: Annotated[list, operator.add]
    # Execution telemetry and token metrics
    metrics: Dict[str, Any]

# --- AI AGENT TOOLS ---

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
    logger.info(f"Tool Execution -> Project Search: {sql_query}")
    try:
        clean_sql = sql_query.replace("```sql", "").replace("```", "").strip()
        result = project_service_v1(clean_sql)
        return str(result)
    except Exception as e:
        return f"Database error: {str(e)}"

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
    logger.info(f"Tool Execution -> Order Search: {sql_query}")
    try:
        clean_sql = sql_query.replace("```sql", "").replace("```", "").strip()
        result = order_service_v1(clean_sql)
        return str(result)
    except Exception as e:
        return f"Database error: {str(e)}"

def search_global_database(keyword: str) -> str:
    """
    Performs a broad keyword search across all records using FTS5 (Full Text Search).
    Use this tool for generic database searches when the intent is unclear.
    
    Args:
        keyword: The primary search term or identifier extracted from the user's prompt.
    """
    logger.info(f"Tool Execution -> Global Search: {keyword}")
    try:
        result = global_search_service(keyword)
        return str(result)
    except Exception as e:
        return f"Search error: {str(e)}"

def search_company_policies(search_query: str) -> str:
    """
    Searches the company's internal knowledge base (unstructured text/rules) using RAG and Vector Embeddings.
    Use this tool ONLY when the user asks about company rules, IT support, HR policies, hardware requests, onboarding, or refund timelines.
    
    Args:
        search_query: The exact question or search phrase the user is asking.
    """
    logger.info(f"Tool Execution -> RAG Policy Search: {search_query}")
    return query_knowledge_base(search_query)


# --- LANGGRAPH WORKFLOW NODES ---
async def agent_node(state: AgentState):
    """
    Asynchronous reasoning node.
    Evaluates conversational context, extracts multiple/parallel tool invocations 
    from LLM response parts, and tracks latency and token consumption metrics.
    """
    start_time = time.perf_counter()
    logger.info("[Node: Agent] Initializing asynchronous reasoning phase...")
    
    model = genai.GenerativeModel(
        model_name="models/gemini-2.5-flash",
        tools=[search_project_database, search_order_database, search_global_database, search_company_policies]
    )
    
    history_list = state.get("chat_history", [])
    chat_context = "\n".join(history_list)
    tool_history = state.get("all_tool_results", "")
    
    if tool_history:
        logger.info("   -> Synthesizing accumulated tool results.")
        prompt = f"""
        System Rules: {state['system_prompt']}
        
        Previous Conversation Context:
        {chat_context}
        
        Original User Query: {state['query']}
        
        Data collected so far:
        {tool_history}
        
        Instructions:
1. R    1. Review the collected data against the Original User Query.
        2. If a database query returned empty records ([]), DO NOT repeat the same query. Either try a fallback tool (like search_global_database) or conclude that the record does not exist.
        3. If all needed data is gathered (or verified missing), generate the final comprehensive answer adhering to formatting rules.
        """
    else:
        logger.info("   -> First pass: Analyzing user query.")
        prompt = f"""
        System Rules: {state['system_prompt']}
        
        Previous Conversation Context:
        {chat_context}
        
        Current User Query: {state['query']}
        """
        
    try:
        # Non-blocking asynchronous LLM generation
        response = await model.generate_content_async(prompt)
        
        # Calculate reasoning latency
        elapsed_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Safely extract token consumption metadata
        usage = getattr(response, "usage_metadata", None)
        token_metrics = {
            "prompt_tokens": getattr(usage, "prompt_token_count", 0),
            "completion_tokens": getattr(usage, "candidates_token_count", 0),
            "total_tokens": getattr(usage, "total_token_count", 0)
        }
        
        # Update telemetry state
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
        
        # Iterate over all content parts to collect text or parallel function calls
        for part in candidate.content.parts:
            if part.function_call:
                func_name = part.function_call.name
                func_args = {k: v for k, v in part.function_call.args.items()}
                extracted_tool_calls.append({"name": func_name, "args": func_args})
            elif part.text:
                final_text_parts.append(part.text)
                
        # If parallel or single tool execution is requested by the model
        if extracted_tool_calls:
            logger.info(f"   -> [Action Required] LLM requested {len(extracted_tool_calls)} tool execution(s): {[tc['name'] for tc in extracted_tool_calls]}")
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
        return {
            "final_answer": "I encountered an error while processing the request.", 
            "tool_calls": []
        }

async def tool_node(state: AgentState):
    """
    Asynchronous parallel tool execution node.
    Dispatches multiple tool calls concurrently via asyncio.gather and asyncio.to_thread,
    logs individual tool latencies, and aggregates the results into state.
    """
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        logger.info("[Node: Tool] No tool calls to execute.")
        return {"tool_calls": []}

    logger.info(f"[Node: Tool] Initiating parallel execution for {len(tool_calls)} tool(s)...")

    available_tools = {
        "search_project_database": search_project_database,
        "search_order_database": search_order_database,
        "search_global_database": search_global_database,
        "search_company_policies": search_company_policies
    }

    # Helper function to execute an individual tool with precise telemetry timing
    async def execute_single_tool(call_item: Dict[str, Any]):
        tool_name = call_item.get("name")
        args = call_item.get("args", {})
        start_time = time.perf_counter()

        if tool_name not in available_tools:
            return {
                "tool": tool_name,
                "result": f"Error: Unrecognized tool '{tool_name}' requested.",
                "latency_ms": 0.0
            }

        try:
            # Offload synchronous database/vector search to a thread pool for non-blocking concurrency
            tool_func = available_tools[tool_name]
            result = await asyncio.to_thread(tool_func, **args)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(f"   -> [Telemetry] Tool '{tool_name}' completed in {elapsed_ms}ms.")
            return {
                "tool": tool_name,
                "result": str(result),
                "latency_ms": elapsed_ms
            }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            return {
                "tool": tool_name,
                "result": f"Tool execution failed: {str(e)}",
                "latency_ms": elapsed_ms
            }

    # Execute all requested tools concurrently
    execution_results = await asyncio.gather(*[execute_single_tool(tc) for tc in tool_calls])

    # Accumulate results and update metrics
    existing_metrics = state.get("metrics", {}) or {}
    node_latencies = existing_metrics.get("node_latencies", [])
    accumulated_history = state.get("all_tool_results", "")

    for res in execution_results:
        node_latencies.append({
            "node": "tool_node",
            "tool": res["tool"],
            "latency_ms": res["latency_ms"]
        })
        accumulated_history += f"\n--- Data from {res['tool']} ---\n{res['result']}\n"

    updated_metrics = {
        **existing_metrics,
        "node_latencies": node_latencies
    }

    return {
        "all_tool_results": accumulated_history,
        "tool_calls": [],  # Clear the queue once all tools are executed
        "metrics": updated_metrics
    }

def should_continue(state: AgentState):
    """
    Conditional routing edge function.
    Evaluates whether there are pending tool calls to execute or if the graph should conclude.
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
    and returns a structured payload with the answer and telemetry metrics.
    """
    total_start_time = time.perf_counter()
    logger.info(f"🚀 Invoking Asynchronous Agent Workflow for query: {query}")
    
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