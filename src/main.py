from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.utils.logger import configure_logger
from src.routes.ask import router as ask_router

import logging
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = configure_logger(name="AI_Agent_POC", level=logging.INFO)

PORT = 8000

app = FastAPI(title="AI Agent POC")

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

if __name__ == "__main__":
    logger.info(f"Starting server on port {PORT}")
    uvicorn.run(app, port=PORT)