from langchain.tools import StructuredTool
from pydantic.v1 import BaseModel, Field
from src.services.order_service_v1 import order_service_v1

class GetOrdersV1Input(BaseModel):
    sql_query: str = Field(..., description="SQL query to execute on the orders table.")

def get_orders_v1_wrapper(sql_query: str):
    return order_service_v1(sql_query)

get_orders_v1 = StructuredTool(
    name="get_orders_v1",
    func=get_orders_v1_wrapper,
    args_schema=GetOrdersV1Input,
    description=(
        "Executes a SQL query on the 'orders' table using order_service_v1 and returns the result. "
        "Pass a valid SQL SELECT or DML query as 'sql_query'.\n\n"
        "ORDERS TABLE COLUMNS:\n"
        "- id: INTEGER, Primary key, unique identifier for each order.\n"
        "- createdAt: TEXT, ISO datetime string when the order was created.\n"
        "- updatedAt: TEXT, ISO datetime string when the order was last updated.\n"
        "- fileNum: TEXT, Unique file number for the order (format: END6527461).\n"
        "- displayStatus: TEXT, Status for display purposes. One of: 'open', 'cancelled', 'order_processing', 'closed'.\n"
        "- status: TEXT, Internal status. One of: 'in_escrow', 'cancelled', 'closed'.\n"
        "- address: TEXT, The address associated with the order.\n\n"
        "USAGE EXAMPLES:\n"
        "- To get all open orders: SELECT * FROM orders WHERE displayStatus = 'open';\n"
        "- To get a specific order by fileNum: SELECT * FROM orders WHERE fileNum = 'END6527461';\n"
        "- To count closed orders: SELECT COUNT(*) FROM orders WHERE status = 'closed';\n"
        "- To search by address: SELECT * FROM orders WHERE address LIKE '%Main St%';\n"
    )
)
