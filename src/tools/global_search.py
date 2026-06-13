from langchain.tools import StructuredTool
from pydantic.v1 import BaseModel, Field
from src.services.global_search_service import global_search_service

class GlobalSearchInput(BaseModel):
    search_terms: str = Field(..., description="One or more search terms (space-separated) to search across all projects and orders.")

def global_search_tool_wrapper(search_terms: str):
    return global_search_service(search_terms)

global_search_v1 = StructuredTool(
    name="global_search_v1",
    func=global_search_tool_wrapper,
    args_schema=GlobalSearchInput,
    description=(
        "Performs a global full-text search for one or more terms across all projects and orders. "
        "Returns results grouped by type (projects/orders). "
        "Supports multiple space-separated search terms. "
        "Searches project name, group number, order file number, address fields, all the fields that are indexed in the FTS5 tables."
    )
)
