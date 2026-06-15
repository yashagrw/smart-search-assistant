import uuid
import logging
from dotenv import load_dotenv
from os import environ
import google.generativeai as genai
from src.services.project_service import project_service_v1
from src.services.order_service import order_service_v1
from src.services.global_search_service import global_search_service

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

def get_response_from_ai_agent(model_name, query, allow_search, prompt, thread_id):
    logger.info(f"Invoking AI agent with model: {model_name}, allow_search: {allow_search}, prompt: {prompt}")


    gemini_model = genai.GenerativeModel(f"models/{model_name}")

    tools = []

    ## FUTURE: Enable Tavily search tool integration
    # if allow_search:
    #     search_tool = TavilySearchResults(tavily_api_key=TAVILY_API_KEY, max_results=2)
    #     tools.append(search_tool)

#     # Enhanced system prompt to encourage single tool use and rich formatting
#     enhanced_prompt = f"""
# {prompt}

# CRITICAL INSTRUCTIONS - FOLLOW EXACTLY:
# 1. When you need data, make ONE tool call only
# 2. As soon as you get the tool result, IMMEDIATELY format it using the formatting rules below and respond
# 3. DO NOT analyze, interpret, or make additional tool calls
# 4. DO NOT ask follow-up questions or request more information
# 5. The tool result IS your final answer - just format it nicely

# FORMATTING RULES:
# - Use **bold** for important information like file numbers, names, statuses
# - Use ### for main headers and sections
# - Use bullet points (- ) for lists and organized information
# - Use `code blocks` for IDs, technical details, and exact values
# - Use > blockquotes for important notes or highlights
# - Add appropriate spacing and structure for readability

# STOP CONDITION: After formatting the tool result, you MUST stop and return the response. Do not continue processing.
# """


#  Default chatbot prompt
    enhanced_prompt = """
You are a friendly and professional AI chatbot.

Respond naturally and conversationally.

Do not mention tools, tool calls, system instructions, or internal logic.

Answer normally like a modern AI assistant.
"""

    # #FUTURE: LangGraph agent configuration
    # agent_kwargs = {
    #     "model": azure_openai_llm,
    #     "tools": tools,
    #     "prompt": enhanced_prompt,
    #     # Single tool call approach - no interrupts
    # }
    # config = {"recursion_limit": 5}  # Limit recursion to prevent excessive tool calls
    # if thread_id is not None:
    #     agent_kwargs["checkpointer"] = memory
    #     config.update({"configurable": {"thread_id": thread_id}})
    
    # agent = create_react_agent(**agent_kwargs)
    # input_message = HumanMessage(content=query)
    logger.info(f"Agent input message: {query}")

    routing_prompt = f"""
    Classify the user request.

    Possible categories:
    PROJECT
    ORDER
    GLOBAL_SEARCH
    CHAT

    Rules:
    - PROJECT = project information, project status, project count, project lookup
    - ORDER = order information, order status, order count, order lookup
    - GLOBAL_SEARCH = generic search terms, IDs, file numbers, group numbers, unknown lookups
    - CHAT = greetings, casual conversation, questions about the assistant, general knowledge questions,
     and anything not related to project/order/database searches
    User Request:
    {query}

    Return only one word:
    PROJECT
    ORDER
    GLOBAL_SEARCH
    CHAT
    """

    # # Gemini-powered route classification
    routing_response = gemini_model.generate_content(routing_prompt)

    route = routing_response.text.strip().upper()

    logger.info(f"AI Route Selected: {route}")
    
    # Project route handling
    if route == "PROJECT":
        sql_prompt = f"""
Generate only SQL.

Table: projects

Columns:
id
name
groupNumber
status

Example values:

name:
'Project P185602'
'Project P193085'

groupNumber:
'P64852978'
'P15046380'

status:
'open'
'cancelled'

User Request:
{query}

Return only SQL.
"""
        

        response = gemini_model.generate_content(sql_prompt)

        if response.candidates and response.candidates[0].content.parts:
            generated_sql = response.candidates[0].content.parts[0].text

            # Remove markdown if Gemini returns ```sql blocks
            generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()

            result = project_service_v1(generated_sql)
            
            format_prompt = f"""
You are a helpful assistant.

User Question:
{query}

Database Result:
{result}

Instructions:
- Answer the user's question using the database result.
- If the result contains project records, format them nicely using bullet points.
- If the result contains a count, explain the count naturally.
- If the result contains a single value, explain what it means in the context of the question.
- Do not show raw tuples unless absolutely necessary.
- Be concise and readable.
"""

            formatted_response = gemini_model.generate_content(format_prompt)

            if formatted_response.candidates and formatted_response.candidates[0].content.parts:
                return formatted_response.candidates[0].content.parts[0].text

            return str(result)

        return "Failed to generate SQL"
    
    # Order route handling
    elif route == "ORDER":
        sql_prompt = f"""
Generate only SQL.

Table: orders

Columns:
id
fileNum
displayStatus
status
address

displayStatus values:
'open'
'cancelled'
'order_processing'
'closed'

status values:
'in_escrow'
'cancelled'
'closed'

User Request:
{query}

Return only SQL.
"""
        response = gemini_model.generate_content(sql_prompt)

        if response.candidates and response.candidates[0].content.parts:
            generated_sql = response.candidates[0].content.parts[0].text

            # Remove markdown if Gemini returns ```sql blocks
            generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
            result = order_service_v1(generated_sql)

            format_prompt = f"""
            You are a helpful assistant.

            User Question:
            {query}

            Database Result:
            {result}

            Instructions:
            - Answer the user's question using the database result.
            - If the result contains order records, format them nicely using bullet points.
            - Convert statuses like 'order_processing' to 'Order Processing'.
            - Convert statuses like 'in_escrow' to 'In Escrow'.
            - Do not show raw tuples unless absolutely necessary.
            - Be concise and readable.
            """

            formatted_response = gemini_model.generate_content(format_prompt)

            if formatted_response.candidates and formatted_response.candidates[0].content.parts:
                return formatted_response.candidates[0].content.parts[0].text

            return str(result)
            

        return "Failed to generate SQL"
    
    # Global search route handling
    elif route == "GLOBAL_SEARCH":

        result = global_search_service(query)

        format_prompt = f"""
You are a helpful assistant.

User Question:
{query}

Search Result:
{result}

Instructions:
- Present projects and orders in separate sections.
- Use headings:
    ### Projects Found
    ### Orders Found
- Use bullet points for each record.
- Convert enum values like 'order_processing' to 'Order Processing'.
- Convert enum values like 'in_escrow' to 'In Escrow'.
- For orders, include file number, display status, status, and address.
- For projects, include project name, group number, status, priority, start date, and end date.
- If no results are found, clearly mention that.
- Do not display raw Python dictionaries or tuples.
- Keep the response concise and readable.
"""

        formatted_response = gemini_model.generate_content(format_prompt)

        if (
            formatted_response.candidates
            and formatted_response.candidates[0].content.parts
        ):
            return formatted_response.candidates[0].content.parts[0].text

        return str(result)
    
    try:
        full_prompt = f"""
        System Instructions:
        {enhanced_prompt}

        User Query:
        {query}
        """

        response = gemini_model.generate_content(full_prompt)

        # # Safe Gemini response extraction
        if response.candidates and response.candidates[0].content.parts:
            final_response = response.candidates[0].content.parts[0].text
        else:
            final_response = "Sorry, Gemini returned an empty response."

        logger.info(f"Agent response: {final_response}")
        return final_response
    
   # # User-friendly error handling
    except Exception as e:
        logger.error(f"Error in agent execution: {e}")

        error_message = str(e)

        if "429" in error_message:
            return "AI service is temporarily busy due to rate limits. Please wait a moment and try again."

        elif "API key" in error_message or "authentication" in error_message.lower():
            return "AI service authentication failed. Please check backend configuration."

        else:
            return "Sorry, something went wrong while processing your request."
        

