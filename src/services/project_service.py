import sqlite3
import logging
from src.utils.logger import configure_logger

DB_PATH = 'local_data.db'

logger = configure_logger(name="get_projects_tool", level=logging.INFO)

def project_service_v1(sql_query):
    logger.info(f"\033[34mExecuting project_service_v1 with query: {sql_query}\033[0m")
    if not sql_query.strip().lower().startswith('select'):
        error_msg = "Sorry, can't process this request."
        logger.error(error_msg)
        return {'error': error_msg}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        result = cursor.fetchall()
        logger.info(f"Query result: {result}")
    except Exception as e:
        result = {'error': str(e)}
        logger.error(f"Error executing query: {e}")
    finally:
        conn.close()
    return result
