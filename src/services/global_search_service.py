import sqlite3
from src.utils.logger import configure_logger

DB_PATH = 'local_data.db'
logger = configure_logger(name="global_search_service", level="INFO")

def global_search_service(search_terms):
    """
    Perform full-text search for one or more terms across projects and orders.
    Returns results grouped by type (projects/orders).
    Uses FTS5 with prefix wildcards, and also performs LIKE for substring matching. Results are merged and deduplicated.
    """
    if isinstance(search_terms, str):
        terms = search_terms.strip().split()
    else:
        terms = search_terms
    fts_query_str = ' OR '.join([f'{term}*' for term in terms])
    like_query_strs = [f'%{term}%' for term in terms]
    results = {"projects": [], "orders": []}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # FTS5 search for projects
        projects_query = f"SELECT p.* FROM projects_fts fts JOIN projects p ON fts.rowid = p.id WHERE projects_fts MATCH ?"
        c.execute(projects_query, [fts_query_str])
        projects = c.fetchall()
        logger.info(f"Projects FTS results: {projects}")
        # LIKE search for projects
        like_projects_query = (
            "SELECT * FROM projects WHERE " +
            " OR ".join(["name LIKE ? OR groupNumber LIKE ?" for _ in terms])
        )
        like_params = []
        for s in like_query_strs:
            like_params.extend([s, s])
        c.execute(like_projects_query, like_params)
        projects_like = c.fetchall()
        logger.info(f"Projects LIKE results: {projects_like}")
        # Merge and deduplicate
        all_projects = list({tuple(row) for row in projects + projects_like})
        results["projects"] = all_projects
        # FTS5 search for orders
        orders_query = f"SELECT o.* FROM orders_fts fts JOIN orders o ON fts.rowid = o.id WHERE orders_fts MATCH ?"
        c.execute(orders_query, [fts_query_str])
        orders = c.fetchall()
        logger.info(f"Orders FTS results: {orders}")
        # LIKE search for orders
        like_orders_query = (
            "SELECT * FROM orders WHERE " +
            " OR ".join(["fileNum LIKE ? OR address LIKE ?" for _ in terms])
        )
        like_params = []
        for s in like_query_strs:
            like_params.extend([s, s])
        c.execute(like_orders_query, like_params)
        orders_like = c.fetchall()
        logger.info(f"Orders LIKE results: {orders_like}")
        # Merge and deduplicate
        all_orders = list({tuple(row) for row in orders + orders_like})
        results["orders"] = all_orders
    except Exception as e:
        logger.error(f"Error in global search: {e}")
        results = {"error": str(e)}
    finally:
        conn.close()
    return results
