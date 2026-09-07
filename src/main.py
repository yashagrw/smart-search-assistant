# Override standard sqlite3 with modern pysqlite3 for ChromaDB compatibility on Linux
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.utils.logger import configure_logger
from src.routes.ask import router as ask_router
from src.db_setup import setup_db
from init_vector_db import setup_vector_database

logger = configure_logger(name="AI_Agent_POC", level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager that initializes the SQLite database schema, 
    populates deterministic records, and checks the vector store on startup.
    """
    logger.info("Initializing SQLite tables and ChromaDB vector store on application boot...")
    try:
        setup_db()
        setup_vector_database()
        logger.info("Database and vector store initialization completed successfully.")
    except Exception as e:
        logger.error(f"Startup database initialization error: {e}", exc_info=True)
    yield

app = FastAPI(title="AI Agent POC", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.get("/health")
def health_check():
    logger.info("Health check endpoint called.")
    return {"status": "ok", "message": "Server is running"}

app.include_router(ask_router)