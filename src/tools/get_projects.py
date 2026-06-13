from langchain.tools import StructuredTool
from pydantic.v1 import BaseModel, Field
from src.services.project_service_v1 import project_service_v1

class GetProjectsV1Input(BaseModel):
    sql_query: str = Field(..., description="SQL query to execute on the projects table.")

def get_projects_v1_wrapper(sql_query: str):
    return project_service_v1(sql_query)

get_projects_v1 = StructuredTool(
    name="get_projects_v1",
    func=get_projects_v1_wrapper,
    args_schema=GetProjectsV1Input,
    description=(
        "Executes a SQL query on the 'projects' table using project_service_v1 and returns the result. "
        "Pass a valid SQL SELECT or DML query as 'sql_query'.\n\n"
        "PROJECTS TABLE COLUMNS:\n"
        "- id: INTEGER, Primary key, unique identifier for each project.\n"
        "- name: TEXT, Name of the project.\n"
        "- groupNumber: TEXT, Unique group number for the project (format: P96845619).\n"
        "- status: TEXT, Project status. One of: 'open', 'cancelled'.\n"
        "- client_id: INTEGER, Foreign key referencing the client table.\n"
        "- createdAt: TEXT, ISO datetime string when the project was created.\n"
        "- updatedAt: TEXT, ISO datetime string when the project was last updated.\n\n"
        "CLIENT TABLE COLUMNS (referenced by client_id):\n"
        "- id: INTEGER, Primary key, unique identifier for each client.\n"
        "- name: TEXT, Name of the client.\n\n"
        "USAGE EXAMPLES:\n"
        "- To get all open projects: SELECT * FROM projects WHERE status = 'open';\n"
        "- To get a project by groupNumber: SELECT * FROM projects WHERE groupNumber = 'P96845619';\n"
        "- To count cancelled projects: SELECT COUNT(*) FROM projects WHERE status = 'cancelled';\n"
        "- To join with client info: SELECT p.*, c.name as client_name FROM projects p JOIN client c ON p.client_id = c.id;\n"
    )
)
