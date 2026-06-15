from fastapi import APIRouter
from src.models.ask_request_state import AskRequestState
from src.ai_agent import get_response_from_ai_agent
from src.utils.logger import configure_logger
import logging

router = APIRouter()
logger = configure_logger(name="ask_agent", level=logging.INFO)

ALLOWED_MODEL_NAMES = [
    "gemini-2.5-flash",
]

@router.post("/ask")
def ask_agent(request: AskRequestState):
    logger.info(f"Received request: {request}")
    if request.model_name not in ALLOWED_MODEL_NAMES:
        logger.warning(f"Invalid model name: {request.model_name}")
        return {"error": f"{request.model_name} is a invalid Model Name"}

    llm_id = request.model_name
    query = request.query
    prompt = request.system_prompt
    allow_search = request.allow_search
    thread_id = request.thread_id

    logger.info(f"Calling AI agent with model: {llm_id}, allow_search: {allow_search}, thread_id: {thread_id}")
    response = get_response_from_ai_agent(llm_id, query, allow_search, prompt, thread_id)
    logger.info(f"AI agent response: {response}")
    return response