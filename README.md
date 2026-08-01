# Smart Search Assistant using Gemini, LangGraph, and SQLite

## Overview

Smart Search Assistant is an advanced AI-powered autonomous agent that enables natural language interaction with project and order data. The application combines a React frontend with a FastAPI backend and leverages **LangGraph** and **Gemini 2.5 Flash** to intelligently orchestrate multi-step tool execution, retain conversational memory, and generate meaningful responses.

Users can retrieve complex information using conversational queries instead of manually writing database queries. The system supports project search, order retrieval, and global full-text search across datasets stored in SQLite.

---

## Features

### 🧠 Autonomous Agent (Powered by LangGraph)
*   **Multi-Tool Orchestration:** The agent can reason through complex queries and execute multiple tools in a single loop (e.g., fetching project details and calculating order statuses simultaneously).
*   **Conversational Memory:** Utilizes LangGraph's `MemorySaver` to retain chat context across sessions, preventing the AI from losing track of previous messages.
*   **Self-Correction (Agentic Fallback):** If a specific SQL query yields no results, the agent can autonomously adapt and fall back to broader FTS5 global searches.

### 📊 Database Search Capabilities
*   **Project Search:** Retrieve project information (status, dates, clients) using natural language.
*   **Order Search:** Search by file number, status, or address.
*   **Global Search:** SQLite FTS5-powered full-text search across all records with deduplication.
*   **Text-to-SQL Automation:** The AI dynamically generates and executes SQLite queries based on the database schema provided in tool docstrings.

### 💻 System & Interface
*   **Frontend:** Modern React-based chat interface with rich Markdown rendering.
*   **Backend:** Fast and modular REST API built on FastAPI.

---

## Architecture

The system has been upgraded from a single-intent router to a stateful, cyclical LangGraph workflow.

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
    │  │  │ (Gemini 2.5) ├─────────►│ (Python Tools)   │  │  │
    │  │  │              │          │                  │  │  │
    │  │  │ [Brain]      │◄─────────┤ [Executes SQL]   │  │  │
    │  │  └──────┬───────┘  Result  └────────┬─────────┘  │  │
    │  │         │                           │            │  │
    │  │         │ Final Answer              ▼            │  │
    │  └─────────┼─────────────────── ┌────────────────┐  │  │
    │            │                    │ SQLite + FTS5  │  │  │
    │            ▼                    └────────────────┘  │  │
    │   Response to User                                  │  │
    └────────────────────────────────────────────────────────┘

---

## Technology Stack

### Backend
*   Python (FastAPI, Uvicorn, Pydantic)
*   SQLite (with FTS5)
*   **LangGraph** (State Management & Agent Workflow)
*   Google Gemini 2.5 Flash (Native SDK)

### Frontend
*   React, JavaScript (ES6+), CSS, React Markdown

---

## Project Structure

    ai-chatbot/
    ├── client/
    │   └── src/                 # React Application
    ├── src/
    │   ├── ai_agent.py          # Main LangGraph Engine & Tools
    │   ├── main.py              # FastAPI Application
    │   ├── db_setup.py          # SQLite Initialization
    │   ├── models/              # Pydantic Schemas
    │   ├── routes/              # API Endpoints
    │   ├── services/            # Database Execution Logic
    │   └── utils/               # Logging & Utilities
    ├── local_data.db
    ├── requirements.txt
    ├── .env
    └── README.md


---

## Getting Started

### Prerequisites
*   Python 3.9+
*   Node.js 16+
*   npm or Yarn
*   Gemini API Key

### Backend Setup

    git clone <repository-url>
    cd ai-chatbot

    python -m venv venv

    # Windows
    venv\Scripts\activate
    # Linux / macOS
    source venv/bin/activate

    pip install -r requirements.txt

Create a `.env` file:

    GEMINI_API_KEY=your_gemini_api_key

Initialize the local database:

    python src/db_setup.py

Run the backend:

    python -m uvicorn src.main:app --reload --port 8000


### Frontend Setup

    cd client
    npm install
    npm start


---

## Example Queries

*   **Single Intent:** "Show open projects"
*   **Multi-Intent:** "Find project P64852978 and list all cancelled orders."
*   **Conversational Memory:** 
    *   User: "Show me details for Project Alpha."
    *   User: "What is its group number?" *(Agent remembers 'Alpha')*
*   **Global Search Fallback:** "Search for Springfield"

---

## Future Enhancements
*   **RAG (Retrieval-Augmented Generation):** Indexing unstructured data (PDFs/Documents) using Vector Databases.
*   **Multi-Agent Architecture:** Introducing specialized worker agents (e.g., a dedicated SQL Agent and a Formatting Agent) overseen by a Supervisor.
*   Tavily search integration for real-time web information retrieval.

---

## License
This project is intended for educational, learning, and demonstration purposes.