import uuid
import logging
from dotenv import load_dotenv
from os import environ
import google.generativeai as genai
from src.services.project_service import project_service_v1
from src.services.order_service import order_service_v1
from src.services.global_search_service import global_search_service

# Core LangGraph imports for state management and workflow routing
from typing import TypedDict
from langgraph.graph import StateGraph, END
import json

# --- ENVIRONMENT SETUP ---
load_dotenv()
GEMINI_API_KEY = environ.get("GEMINI_API_KEY")
logger = logging.getLogger(__name__)

# Configure Gemini with the API Key
genai.configure(api_key=GEMINI_API_KEY)

# --- LANGGRAPH STATE (THE DABBA) ---
class AgentState(TypedDict):
    system_prompt: str    
    query: str
    tool_name: str
    tool_args: dict
    tool_result: str
    all_tool_results: str 
    final_answer: str

# --- NATIVE GEMINI TOOLS ---

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
    logger.info(f"Tool Call -> Project Search: {sql_query}")
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
    logger.info(f"Tool Call -> Order Search: {sql_query}")
    try:
        clean_sql = sql_query.replace("```sql", "").replace("```", "").strip()
        result = order_service_v1(clean_sql)
        return str(result)
    except Exception as e:
        return f"Database error: {str(e)}"

def search_global_database(keyword: str) -> str:
    """
    Performs a broad keyword search across all records using FTS5 (Full Text Search).
    Use this tool for generic searches, IDs, partial addresses, group numbers, or when the intent is unclear.
    
    Args:
        keyword: The primary search term or identifier extracted from the user's prompt.
    """
    logger.info(f"Tool Call -> Global Search: {keyword}")
    try:
        result = global_search_service(keyword)
        return str(result)
    except Exception as e:
        return f"Search error: {str(e)}"


# --- LANGGRAPH NODES (THE STATIONS) ---

def agent_node(state: AgentState):
    """
    The Brain of the operation. 
    It reads the state, decides if a tool is needed, or provides the final answer.
    """
    logger.info("🧠 [Node] AI Agent is thinking...")
    
    model = genai.GenerativeModel(
        model_name="models/gemini-2.5-flash",
        tools=[search_project_database, search_order_database, search_global_database]
    )
    
    history = state.get("all_tool_results", "")
    
    if history:
        logger.info("   -> Processing accumulated tool results.")
        prompt = f"""
        System Rules:
        {state['system_prompt']}
        
        Original User Query: {state['query']}
        
        Data collected so far:
        {history}
        
        Instructions:
        1. Review the Data collected so far against the Original User Query.
        2. If you still need MORE data (e.g., another table to search), make another tool call.
        3. If you have ALL the required data, generate the final comprehensive answer using the formatting rules.
        """
    else:
        logger.info("   -> First pass: Analyzing user query.")
        prompt = f"{state['system_prompt']}\n\nUser Query: {state['query']}"
        
    try:
        response = model.generate_content(prompt)
        part = response.candidates[0].content.parts[0]
        
        if part.function_call:
            func_name = part.function_call.name
            args = {k: v for k, v in part.function_call.args.items()}
            logger.info(f"   -> 🎫 AI requested tool: {func_name}")
            return {"tool_name": func_name, "tool_args": args}
            
        else:
            logger.info("   -> 💬 Final answer generated.")
            return {"final_answer": part.text, "tool_name": None}
            
    except Exception as e:
        logger.error(f"Agent Node Error: {e}")
        return {"final_answer": "Sorry, I encountered an error while thinking.", "tool_name": None}

def tool_node(state: AgentState):
    """
    The Executor. 
    It reads the Parchi, runs the specific tool, and accumulates the data.
    """
    tool_name = state.get("tool_name")
    args = state.get("tool_args", {})
    
    logger.info(f"🛠️ [Node] Executing tool: {tool_name}")
    
    available_tools = {
        "search_project_database": search_project_database,
        "search_order_database": search_order_database,
        "search_global_database": search_global_database
    }
    
    if tool_name in available_tools:
        tool_func = available_tools[tool_name]
        try:
            result = tool_func(**args)
            logger.info("   -> Tool execution successful.")
            
            current_history = state.get("all_tool_results", "")
            new_history = current_history + f"\n--- Data from {tool_name} ---\n{result}\n"
            
            return {"tool_result": result, "all_tool_results": new_history}
            
        except Exception as e:
            logger.error(f"Tool Execution Error: {e}")
            return {"tool_result": str(e)}
            
    return {"tool_result": "Error: Unknown tool requested."}

# --- THE ROUTER (TRACK SWITCHER) ---
def should_continue(state: AgentState):
    """Decides whether to go to the tool node or finish the execution."""
    if state.get("tool_name"):
        return "continue"
    return "end"

# --- THE MAIN ENGINE ---
def get_response_from_ai_agent(model_name, query, allow_search, prompt, thread_id):
    """
    Entry point for the FastAPI route.
    Builds and invokes the LangGraph workflow.
    """
    logger.info(f"🚀 Starting LangGraph Agent for query: {query}")
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("action", tool_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "action",
            "end": END
        }
    )
    
    workflow.add_edge("action", "agent")
    app = workflow.compile()
    
    try:
        initial_state = {
            "system_prompt": prompt,
            "query": query,
            "tool_name": None,
            "tool_args": {},
            "tool_result": None,
            "all_tool_results": "",
            "final_answer": None
        }
        
        final_state = app.invoke(initial_state)
        
        answer = final_state.get("final_answer")
        if answer:
            logger.info("✅ Workflow completed successfully.")
            return answer
        else:
            return "Sorry, I couldn't generate an answer."
            
    except Exception as e:
        logger.error(f"Critical error in workflow execution: {e}")
        return "I encountered a critical error while processing your request. Please try again."