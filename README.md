# Smart Search Assistant using Gemini, LangGraph, and SQLite

## Overview
Smart Search Assistant is an enterprise-grade autonomous AI search agent that enables natural language interaction with enterprise structured data (Projects/Orders) and unstructured knowledge bases (Company Policies). The application combines a React frontend with an asynchronous FastAPI backend and leverages **LangGraph**, **ChromaDB**, and **Gemini 2.5 Flash** to intelligently orchestrate multi-step tool execution, retain conversational memory, profile execution telemetry, and evaluate responses scientifically.

## Features
### 🧠 Autonomous Agent (Powered by LangGraph)
*   **Multi-Tool Orchestration:** The agent reasons through complex multi-intent queries and invokes multiple tools dynamically.
*   **Parallel Execution:** Dispatches multiple database and vector search queries concurrently using `asyncio.gather` and background thread pooling (`asyncio.to_thread`).
*   **Conversational Memory:** Utilizes LangGraph's `MemorySaver` with tab-isolated session tokens to maintain multi-turn chat history.
*   **Agentic Fallback:** Autonomously falls back to broader SQLite FTS5 global search if structured SQL queries yield no records.
*   **Circuit Breakers:** Configured runtime `recursion_limit` (8 hops) to prevent runaway reasoning loops and quota exhaustion.

### ⚡ Async Runtime & Real-Time Telemetry
*   **Non-Blocking Event Loop:** Fully asynchronous workflow powered by `generate_content_async` and `app.ainvoke`.
*   **Live UI Telemetry:** Real-time state tracing tracking per-node latency (ms), input/output token consumption, and rendering performance chips on the frontend UI.
*   **Latency Optimization:** Reduced multi-hop resolution latency by over **60%** (from ~20.6s baseline to ~7.3s).

### 📚 RAG Pipeline (Retrieval-Augmented Generation)
*   **Vector Database Integration:** Powered by ChromaDB for persistent unstructured data storage.
*   **Enterprise Chunking:** Utilizes `RecursiveCharacterTextSplitter` (chunk size 500, overlap 100) with contextual metadata injection.
*   **Semantic Search:** Converts user queries into 3072-dimensional vectors using Google Gemini Embeddings (`models/gemini-embedding-001`).

### 📊 Database Search Capabilities (Text-to-SQL)
*   **Project & Order Search:** Dynamically generates and executes SQLite queries based on database schemas provided in tool docstrings.
*   **Global Search:** SQLite FTS5-powered full-text search across all records with deduplication.

### 🔬 Automated EvalOps Suite (LLM-as-a-Judge)
*   **Benchmark Evaluation:** Integrated evaluation harness (`src/evals/evaluate_rag.py`) scoring RAG performance against a golden benchmark dataset.
*   **Hallucination & Retrieval Auditing:** Evaluates Faithfulness, Answer Relevance, and Context Precision metrics with rate-limiting backoff resilience.

## Architecture

    ┌──────────────────┐
    │  React Frontend  │
    │   (Port 4000)    │
    └────────┬─────────┘
             │ HTTP POST /ask (Session Token)
             ▼
    ┌────────────────────────────────────────────────────────┐
    │                   FastAPI Backend                      │
    │               (Async / Non-Blocking)                   │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │        LangGraph Autonomous Agent Engine         │  │
    │  │                                                  │  │
    │  │  ┌──────────────┐ Tool Calls ┌──────────────────┐  │  │
    │  │  │ LLM Node     ├───────────►│ Action Node      │  │  │
    │  │  │ (Gemini 2.5) │            │ (asyncio.gather) │  │  │
    │  │  │ [Async Brain]│◄───────────┤ [Parallel Tools] │  │  │
    │  │  └──────┬───────┘   Data     └────────┬─────────┘  │  │
    │  │         │                             │            │  │
    │  │         │ Final Answer                ▼            │  │
    │  └─────────┼───────────┬──────── ┌────────────────┐  │  │
    │            │           │         │ SQLite (FTS5)  │  │  │
    │            ▼           │         └────────────────┘  │  │
    │     JSON Response      │         ┌────────────────┐  │  │
    │   (Text + Telemetry)   └────────►│ ChromaDB (RAG) │  │  │
    │                                  └────────────────┘  │  │
    └────────────────────────────────────────────────────────┘

## Evaluation Benchmark Scorecard

| Evaluation Metric | Benchmark Score | Description |
| :--- | :---: | :--- |
| **🛡️ Macro Faithfulness** | **100.0%** | Measures factual consistency; verifies zero hallucination against retrieved context. |
| **🎯 Macro Answer Relevance** | **100.0%** | Measures how directly and concisely the answer addresses the user's intent. |
| **📚 Macro Retrieval Precision** | **100.0%** | Verifies that ChromaDB retrieved the exact ground-truth policy sections. |
| **⭐ Overall Quality Index** | **100.0 / 100** | Aggregate benchmark health score across all test categories. |

## Technology Stack
*   **Backend:** Python, FastAPI, Uvicorn, Pydantic
*   **AI/LLM:** Google Gemini 2.5 Flash, Gemini Embeddings
*   **Agent Framework:** LangGraph
*   **Databases:** SQLite (Structured + FTS5), ChromaDB (Vector)
*   **Frontend:** React, JavaScript (ES6+), React Markdown

## Project Structure

    ai-chatbot/
    ├── client/                     # React Frontend Application
    │   ├── src/                    # React source code & telemetry UI
    │   └── package.json
    ├── knowledge_base/             # Unstructured corporate policies
    │   └── company_policies.txt 
    ├── src/                        # Backend Application Source
    │   ├── evals/                  # Automated EvalOps Suite
    │   │   ├── __init__.py
    │   │   ├── golden_dataset.py   # Benchmark ground-truth test cases
    │   │   └── evaluate_rag.py     # LLM-as-a-Judge evaluation runner
    │   ├── models/                 # Pydantic Schemas & State Models
    │   │   └── ask_request_state.py
    │   ├── routes/                 # FastAPI Route Controllers
    │   │   └── ask.py              # Async /ask endpoint
    │   ├── services/               # Database, Search, and Vector Execution Logic
    │   │   ├── project_service.py  # SQLite project operations
    │   │   ├── order_service.py    # SQLite order operations
    │   │   ├── global_search_service.py # SQLite FTS5 full-text search
    │   │   └── rag_service.py      # ChromaDB persistent vector search
    │   ├── tools/                  # Agent tool definitions
    │   │   ├── get_orders.py
    │   │   ├── get_projects.py
    │   │   └── global_search.py
    │   ├── utils/                  # Centralized logging utilities
    │   │   └── logger.py
    │   ├── ai_agent.py             # Main LangGraph Async Engine & Tool Orchestrator
    │   ├── db_setup.py             # SQLite Initialization
    │   └── main.py                 # FastAPI Application Entry Point
    ├── init_vector_db.py           # Script to chunk and vectorize text into ChromaDB
    ├── local_data.db               # SQLite Database
    ├── requirements.txt            # Python Dependencies
    ├── .env                        # Environment Configuration
    ├── PROJECT_AUDIT.md            # Architecture progress & audit tracker
    └── README.md                   # Project Documentation

## Getting Started

### Backend Setup

    git clone https://github.com/yashagrw/smart-search-assistant.git
    cd smart-search-assistant
    python -m venv venv

    # Windows:
    .\venv\Scripts\activate
    # Linux/macOS:
    source venv/bin/activate

    pip install -r requirements.txt

Create a `.env` file in the root directory:

    GEMINI_API_KEY=your_gemini_api_key_here

Initialize the Databases (SQLite & ChromaDB Vector Store):

    python src/db_setup.py
    python init_vector_db.py

Run the backend:

    python -m uvicorn src.main:app --reload --port 8000

Run Automated RAG Evaluations:

    python src/evals/evaluate_rag.py

### Frontend Setup

    cd client
    npm install
    npm start

## Example Queries
*   **Parallel Multi-Intent:** "Check status of Project P185602 and tell cafeteria timings"
*   **Multi-Intent SQL:** "Find project P64852978 and list all cancelled orders."
*   **RAG Document Search:** "My laptop screen is flickering. How do I get it replaced?"
*   **Conversational Memory:** "What is the group number for that project?"

## License
This project is intended for educational and demonstration purposes.