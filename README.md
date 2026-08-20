# Smart Search Assistant using Gemini, LangGraph, and SQLite

## Overview
Smart Search Assistant is an advanced AI-powered autonomous agent that enables natural language interaction with enterprise structured data (Projects/Orders) and unstructured knowledge bases (Company Policies). The application combines a React frontend with a FastAPI backend and leverages **LangGraph**, **ChromaDB**, and **Gemini 2.5 Flash** to intelligently orchestrate multi-step tool execution, retain conversational memory, and generate highly accurate responses.

## Features
### 🧠 Autonomous Agent (Powered by LangGraph)
*   **Multi-Tool Orchestration:** The agent reasons through complex queries and executes multiple tools in a single conversational loop.
*   **Conversational Memory:** Utilizes LangGraph's `MemorySaver` to retain chat context across sessions (Thread Isolation).
*   **Agentic Fallback:** Autonomously adapts and falls back to broader FTS5 global searches if SQL queries yield no results.

### 📚 RAG Pipeline (Retrieval-Augmented Generation)
*   **Vector Database Integration:** Powered by ChromaDB for persistent unstructured data storage.
*   **Enterprise Chunking:** Utilizes `RecursiveCharacterTextSplitter` with chunk overlap and contextual metadata injection.
*   **Semantic Search:** Converts user intent into 3072-dimensional vectors using Google Gemini Embeddings to fetch precise organizational policies.

### 📊 Database Search Capabilities (Text-to-SQL)
*   **Project & Order Search:** Dynamically generates and executes SQLite queries based on the database schema provided in tool docstrings.
*   **Global Search:** SQLite FTS5-powered full-text search across all records with deduplication.

## Architecture

    ┌──────────────────┐
    │  React Frontend  │
    │   (Port 4000)    │
    └────────┬─────────┘
             │ HTTP Request (with Thread ID)
             ▼
    ┌────────────────────────────────────────────────────────┐
    │                   FastAPI Backend                      │
    │                                                        │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │        LangGraph Autonomous Agent Engine         │  │
    │  │                                                  │  │
    │  │  ┌──────────────┐          ┌──────────────────┐  │  │
    │  │  │ LLM Node     │ Tool Call│ Action Node      │  │  │
    │  │  │ (Gemini 2.5) ├─────────►│ (4 Custom Tools) │  │  │
    │  │  │              │          │                  │  │  │
    │  │  │ [Brain]      │◄─────────┤ [SQL + RAG]      │  │  │
    │  │  └──────┬───────┘  Result  └────────┬─────────┘  │  │
    │  │         │                           │            │  │
    │  │         │ Final Answer              ▼            │  │
    │  └─────────┼───────────┬─────── ┌────────────────┐  │  │
    │            │           │        │ SQLite (FTS5)  │  │  │
    │            ▼           │        └────────────────┘  │  │
    │   Response to User     │        ┌────────────────┐  │  │
    │                        └───────►│ ChromaDB (RAG) │  │  │
    │                                 └────────────────┘  │  │
    └────────────────────────────────────────────────────────┘

## Technology Stack
*   **Backend:** Python, FastAPI, Uvicorn, Pydantic
*   **AI/LLM:** Google Gemini 2.5 Flash, Gemini Embeddings
*   **Agent Framework:** LangGraph
*   **Databases:** SQLite (Structured), ChromaDB (Vector)
*   **Frontend:** React, JavaScript (ES6+), React Markdown

## Project Structure

```text
ai-chatbot/
├── client/
│   └── src/                 # React Application
├── knowledge_base/          # Unstructured data for RAG
│   └── company_policies.txt 
├── src/
│   ├── ai_agent.py          # Main LangGraph Engine & Agent Tools
│   ├── main.py              # FastAPI Application
│   ├── db_setup.py          # SQLite Initialization
│   ├── models/              # Pydantic Schemas
│   ├── routes/              # API Endpoints
│   ├── services/            # Database Execution Logic
│   │   ├── project_service.py
│   │   ├── order_service.py
│   │   ├── global_search_service.py
│   │   └── rag_service.py   # ChromaDB & Vector Search Logic
│   ├── tools/               # Helper Tool Implementations
│   │   ├── get_orders.py
│   │   ├── get_projects.py
│   │   └── global_search.py
│   └── utils/               # Logging & Utilities
├── init_vector_db.py        # Script to chunk and vectorize text
├── local_data.db            # SQLite Database
├── requirements.txt
├── .env
└── README.md

## Getting Started

### Backend Setup

    git clone <repository-url>
    cd ai-chatbot
    python -m venv venv
    
    # Windows: venv\Scripts\activate
    # Linux/macOS: source venv/bin/activate
    
    pip install -r requirements.txt

Create a `.env` file:
    GEMINI_API_KEY=your_gemini_api_key

Initialize the Databases (SQLite & ChromaDB Vector Store):
    python src/db_setup.py
    python init_vector_db.py

Run the backend:
    python -m uvicorn src.main:app --reload --port 8000

### Frontend Setup

    cd client
    npm install
    npm start

## Example Queries
*   **Multi-Intent SQL:** "Find project P64852978 and list all cancelled orders."
*   **RAG Document Search:** "My laptop screen is flickering. How do I get it replaced?"
*   **Conversational Memory:** "What is the group number for that project?"

## Future Enhancements
*   **Multi-Agent Architecture:** Introducing specialized worker agents (e.g., a dedicated SQL Agent and a RAG Agent) overseen by a Supervisor.
*   Async execution for extreme concurrent scalability.

## License
This project is intended for educational and demonstration purposes.