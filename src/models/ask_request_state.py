from pydantic import BaseModel

class AskRequestState(BaseModel):
    model_name: str
    query: str
    system_prompt: str
    allow_search: bool
    thread_id: str | None = None