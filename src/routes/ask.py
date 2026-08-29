import logging
from fastapi import APIRouter
from src.models.ask_request_state import AskRequestState
from src.ai_agent import get_response_from_ai_agent
from src.utils.logger import configure_logger

router = APIRouter()
logger = configure_logger(name="ask_agent", level=logging.INFO)

ALLOWED_MODEL_NAMES = [
    "gemini-2.5-flash",
    "gemini-1.5-flash"
]

@router.post("/ask")
async def ask_agent(request: AskRequestState):
    """
    Asynchronous endpoint that receives user search requests,
    validates the model parameters, awaits the agent workflow,
    and returns both the final answer and execution telemetry.
    """
    logger.info(f"Received request: {request}")
    if request.model_name not in ALLOWED_MODEL_NAMES:
        logger.warning(f"Invalid model name: {request.model_name}")
        return {"error": f"{request.model_name} is an invalid Model Name"}

    llm_id = request.model_name
    query = request.query
    prompt = request.system_prompt
    allow_search = request.allow_search
    thread_id = request.thread_id

    logger.info(f"Calling AI agent with model: {llm_id}, allow_search: {allow_search}, thread_id: {thread_id}")
    
    # Non-blocking async await
    response = await get_response_from_ai_agent(llm_id, query, allow_search, prompt, thread_id)
    
    logger.info(f"AI agent execution complete for thread: {thread_id}")
    return response