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

#from langchain_community.tools import TavilySearchResults
# from langgraph.prebuilt import create_react_agent
# from langgraph.checkpoint.memory import MemorySaver

load_dotenv()
GEMINI_API_KEY = environ.get("GEMINI_API_KEY")

# TAVILY_API_KEY = environ.get("TAVILY_API_KEY")

logger = logging.getLogger(__name__)

# #FUTURE: Enable MemorySaver when LangGraph memory support is implemented
# memory = MemorySaver()

genai.configure(api_key=GEMINI_API_KEY)

# The thread is a unique key that identifies this particular conversation
thread_id = uuid.uuid4()

# Define the state schema for passing data between graph nodes
class AgentState(TypedDict):
    query: str
    tool_name: str
    tool_args: dict
    tool_result: str
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
    
    # Setup the Manager with all available tools
    model = genai.GenerativeModel(
        model_name="models/gemini-2.5-flash",
        tools=[search_project_database, search_order_database, search_global_database]
    )
    
    # Check if we just came back from a tool (Looping back)
    if state.get("tool_result"):
        logger.info("   -> Processing tool results for final answer.")
        prompt = f"""
        User Query: {state['query']}
        Database Result: {state['tool_result']}
        
        Task: Provide a natural, conversational, and nicely formatted answer based ONLY on the database result. 
        Do not mention SQL, tools, or internal steps.
        """
    else:
        # First time seeing the query
        logger.info("   -> First pass: Analyzing user query.")
        prompt = state["query"]
        
    try:
        response = model.generate_content(prompt)
        part = response.candidates[0].content.parts[0]
        
        # Did the AI ask for a tool? (The Parchi)
        if part.function_call:
            func_name = part.function_call.name
            args = {k: v for k, v in part.function_call.args.items()}
            logger.info(f"   -> 🎫 AI requested tool: {func_name}")
            return {"tool_name": func_name, "tool_args": args}
            
        # Did the AI give a direct answer?
        else:
            logger.info("   -> 💬 Final answer generated.")
            return {"final_answer": part.text, "tool_name": None}
            
    except Exception as e:
        logger.error(f"Agent Node Error: {e}")
        return {"final_answer": "Sorry, I encountered an error while thinking.", "tool_name": None}

def tool_node(state: AgentState):
    """
    The Executor. 
    It reads the Parchi (tool_name) from the state, runs the specific tool, and returns the data.
    """
    tool_name = state.get("tool_name")
    args = state.get("tool_args", {})
    
    logger.info(f"🛠️ [Node] Executing tool: {tool_name}")
    
    # Map string names to actual Python functions
    available_tools = {
        "search_project_database": search_project_database,
        "search_order_database": search_order_database,
        "search_global_database": search_global_database
    }
    
    # Execute the requested tool
    if tool_name in available_tools:
        tool_func = available_tools[tool_name]
        try:
            # We use **args to unpack the dictionary into function parameters
            result = tool_func(**args)
            logger.info("   -> Tool execution successful.")
            return {"tool_result": result}
        except Exception as e:
            logger.error(f"Tool Execution Error: {e}")
            return {"tool_result": f"Error executing {tool_name}: {e}"}
            
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
    
    # 1. BUILD THE GRAPH FACTORY
    workflow = StateGraph(AgentState)
    
    # Add our stations (nodes)
    workflow.add_node("agent", agent_node)
    workflow.add_node("action", tool_node)
    
    # Set the starting point
    workflow.set_entry_point("agent")
    
    # Add the Track Switcher
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "action",
            "end": END
        }
    )
    
    # Loop back from action to agent
    workflow.add_edge("action", "agent")
    
    # Compile the workflow
    app = workflow.compile()
    
    # 2. RUN THE WORKFLOW
    try:
        # Initialize the state (The Dabba)
        initial_state = {
            "query": query,
            "tool_name": None,
            "tool_args": {},
            "tool_result": None,
            "final_answer": None
        }
        
        # Start the engine
        final_state = app.invoke(initial_state)
        
        # Return the final answer to the frontend/user
        answer = final_state.get("final_answer")
        if answer:
            logger.info("✅ Workflow completed successfully.")
            return answer
        else:
            return "Sorry, I couldn't generate an answer."
            
    except Exception as e:
        logger.error(f"Critical error in workflow execution: {e}")
        return "I encountered a critical error while processing your request. Please try again."