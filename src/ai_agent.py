import time
import logging
import operator
from typing import TypedDict, Annotated, Optional, Dict, Any
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

# --- LANGGRAPH STATE SCHEMA ---
class AgentState(TypedDict):
    """Defines the schema for the state passed between graph nodes."""
    system_prompt: str    
    query: str
    tool_name: str
    tool_args: dict
    tool_result: str
    all_tool_results: str 
    final_answer: str
    # Append-only conversation history
    chat_history: Annotated[list, operator.add]
    # Telemetry data (latency, token counts)
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
    Leverages Gemini's async API to evaluate conversation context,
    accumulate tool responses, and track token usage and latency.
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
        1. Review the data collected so far against the Original User Query.
        2. If additional data is required to fully answer the query, invoke the appropriate tool.
        3. If all necessary data is present, generate the final comprehensive answer adhering strictly to the formatting rules.
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
        # Non-blocking async API call to Gemini
        response = await model.generate_content_async(prompt)
        part = response.candidates[0].content.parts[0]
        
        # Calculate execution latency in milliseconds
        elapsed_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Extract token usage metadata safely
        usage = getattr(response, "usage_metadata", None)
        token_metrics = {
            "prompt_tokens": getattr(usage, "prompt_token_count", 0),
            "completion_tokens": getattr(usage, "candidates_token_count", 0),
            "total_tokens": getattr(usage, "total_token_count", 0)
        }
        
        # Update telemetry metrics inside state
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
        
        # Check if Gemini requested a tool execution
        if part.function_call:
            func_name = part.function_call.name
            args = {k: v for k, v in part.function_call.args.items()}
            logger.info(f"   -> [Action Required] LLM requested tool execution: {func_name}")
            return {
                "tool_name": func_name, 
                "tool_args": args,
                "metrics": updated_metrics
            }
        else:
            logger.info("   -> Final response generated successfully.")
            return {
                "final_answer": part.text, 
                "tool_name": None,
                "chat_history": [f"AI: {part.text}"],
                "metrics": updated_metrics
            }
            
    except Exception as e:
        logger.error(f"Agent Node Encountered an Error: {e}", exc_info=True)
        return {
            "final_answer": "I encountered an error while processing the request.", 
            "tool_name": None
        }

async def tool_node(state: AgentState):
    """
    Asynchronous tool execution node.
    Executes the requested tool, logs the tool execution latency,
    and updates the accumulated results and state metrics.
    """
    start_time = time.perf_counter()
    tool_name = state.get("tool_name")
    args = state.get("tool_args", {})
    
    logger.info(f"[Node: Tool] Executing routine: {tool_name}")
    
    available_tools = {
        "search_project_database": search_project_database,
        "search_order_database": search_order_database,
        "search_global_database": search_global_database,
        "search_company_policies": search_company_policies
    }
    
    existing_metrics = state.get("metrics", {}) or {}
    node_latencies = existing_metrics.get("node_latencies", [])
    
    if tool_name in available_tools:
        tool_func = available_tools[tool_name]
        try:
            # Execute the targeted tool function
            result = tool_func(**args)
            
            elapsed_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(f"   -> [Telemetry] Tool '{tool_name}' finished in {elapsed_time_ms}ms.")
            
            # Record tool-specific latency in metrics
            node_latencies.append({
                "node": "tool_node",
                "tool": tool_name,
                "latency_ms": elapsed_time_ms
            })
            
            current_history = state.get("all_tool_results", "")
            new_history = current_history + f"\n--- Data from {tool_name} ---\n{result}\n"
            
            updated_metrics = {
                **existing_metrics,
                "node_latencies": node_latencies
            }
            
            return {
                "tool_result": result, 
                "all_tool_results": new_history,
                "metrics": updated_metrics
            }
            
        except Exception as e:
            logger.error(f"Routine Execution Error: {e}", exc_info=True)
            return {"tool_result": str(e), "metrics": existing_metrics}
            
    return {"tool_result": "Error: Unrecognized tool requested.", "metrics": existing_metrics}

def should_continue(state: AgentState):
    """Conditional routing logic to determine the next graph edge."""
    if state.get("tool_name"):
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

# --- MAIN API ENTRY POINT ---
# --- MAIN ASYNC API ENTRY POINT ---
async def get_response_from_ai_agent(model_name: str, query: str, allow_search: bool, prompt: str, thread_id: str):
    """
    Asynchronous entry point for the FastAPI controller.
    Initializes state, invokes the StateGraph using ainvoke,
    and returns a structured payload with the answer and telemetry metrics.
    """
    total_start_time = time.perf_counter()
    logger.info(f"🚀 Invoking Asynchronous Agent Workflow for query: {query}")
    
    try:
        initial_state = {
            "system_prompt": prompt,
            "query": query,
            "tool_name": None,
            "tool_args": {},
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
            
        config = {"configurable": {"thread_id": thread_id}}
        
        # Non-blocking asynchronous graph execution
        final_state = await app.ainvoke(initial_state, config=config)
        
        total_time_ms = round((time.perf_counter() - total_start_time) * 1000, 2)
        answer = final_state.get("final_answer") or "Unable to generate a valid response."
        
        # Consolidate telemetry metrics
        metrics_data = final_state.get("metrics", {})
        metrics_data["total_latency_ms"] = total_time_ms
        
        logger.info(f"✅ Workflow completed in {total_time_ms}ms with {metrics_data.get('total_accumulated_tokens', 0)} total tokens.")
        
        # Return structured dictionary containing both text response and performance telemetry
        return {
            "answer": answer,
            "metrics": metrics_data
        }
            
    except Exception as e:
        logger.error(f"Critical Workflow Failure: {e}", exc_info=True)
        return {
            "answer": "A critical system error occurred while processing your request. Please try again.",
            "metrics": {
                "total_latency_ms": round((time.perf_counter() - total_start_time) * 1000, 2),
                "error": str(e)
            }
        }