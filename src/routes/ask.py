import logging
from fastapi import APIRouter
from src.models.ask_request_state import AskRequestState
from src.ai_agent import get_response_from_ai_agent
from src.utils.logger import configure_logger
from src.utils.guardrails import check_input_guardrails, sanitize_output

router = APIRouter()
logger = configure_logger(name="ask_agent", level=logging.INFO)

ALLOWED_MODEL_NAMES = [
    "gemini-2.5-flash",
    "gemini-1.5-flash"
]

@router.post("/ask")
async def ask_agent(request: AskRequestState):
    """
    Asynchronous endpoint that validates security guardrails, 
    processes the AI query, and sanitizes outputs.
    """
    logger.info(f"Received request for thread: {request.thread_id}")
    
    # 🛡️ 1. INPUT GUARDRAIL: Check for Prompt Injection / Jailbreaks
    is_safe, security_msg = check_input_guardrails(request.query)
    if not is_safe:
        return {
            "answer": f"🚨 {security_msg}",
            "metrics": {"total_latency_ms": 0, "error": "Blocked by Security Firewall"}
        }

    if request.model_name not in ALLOWED_MODEL_NAMES:
        logger.warning(f"Invalid model name: {request.model_name}")
        return {"error": f"{request.model_name} is an invalid Model Name"}

    llm_id = request.model_name
    query = request.query
    prompt = request.system_prompt
    allow_search = request.allow_search
    thread_id = request.thread_id
    
    # Execute AI Agent
    response = await get_response_from_ai_agent(llm_id, query, allow_search, prompt, thread_id)
    
    # 🛡️ 2. OUTPUT GUARDRAIL: Sanitize PII before returning to client
    if isinstance(response, dict) and "answer" in response:
        response["answer"] = sanitize_output(response["answer"])
    
    logger.info(f"AI agent execution complete for thread: {thread_id}")
    return response