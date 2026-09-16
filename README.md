# 🚀 Smart Search Assistant: Enterprise-Grade Agentic Search Engine

An autonomous, multi-tenant AI search assistant built with **LangGraph**, **Google Gemini 2.5 Flash**, **FastAPI**, and **React**, deployed globally on **Microsoft Azure**. The system intelligently resolves complex multi-intent queries across structured relational databases (SQLite), full-text search indexes (FTS5), and unstructured corporate knowledge bases (ChromaDB Vector RAG), featuring real-time observability, automated evaluation pipelines (EvalOps), and dual-track CI/CD automation.

---

## 🌐 Live Production Deployments
- **🖥️ Live React Web Application:** [https://brave-desert-0c8ba5800.6.azurestaticapps.net](https://brave-desert-0c8ba5800.6.azurestaticapps.net)
- **⚡ Live FastAPI Swagger API:** [https://smart-search-api-h5dzh8hkdqhbf3bu.centralindia-01.azurewebsites.net/docs](https://smart-search-api-h5dzh8hkdqhbf3bu.centralindia-01.azurewebsites.net/docs)

---

## 🏗️ Architectural Overview

    ┌────────────────────────────────────────────────────────┐
    │     React Frontend (Azure Static Web Apps CDN)         │
    │        - Session Isolation via React useRef            │
    │        - Real-Time Telemetry & Latency Chips           │
    └───────────────────────────┬────────────────────────────┘
                                │ HTTP POST /ask (JSON Payload)
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │     FastAPI Controller (Azure Linux App Service)       │
    │        - Async Lifespan DB & ChromaDB Bootstrapper     │
    │        - Linux SQLite3 Override via pysqlite3-binary   │
    └───────────────────────────┬────────────────────────────┘
                                │ await app.ainvoke
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │               LangGraph StateGraph Workflow            │
    │                                                        │
    │  ┌────────────────┐ Tool Invocations ┌───────────────┐ │
    │  │   agent_node   ├─────────────────►│   tool_node   │ │
    │  │ (Gemini Flash) │                  │(asyncio.gather│ │
    │  │ [Async Brain]  │◄─────────────────┤+to_thread pool│ │
    │  └───────┬────────┘  Aggregated Data └───────┬───────┘ │
    │          │                                   │         │
    │          │ Synthesized Response              ▼         │
    │  └───────┼────────────────────────── ┌───────────────┐ │
    │          │                           │ SQLite (FTS5) │ │
    │          ▼                           └───────────────┘ │
    │   JSON Payload                       ┌───────────────┐ │
    │ (Text + Telemetry)                   │ ChromaDB(RAG) │ │
    │                                      └───────────────┘ │
    └────────────────────────────────────────────────────────┘

---

## ✨ Core Engineering Capabilities

### 1. Cyclical Agentic Orchestration (LangGraph)
- **Dynamic Reasoning Loop:** Replaced rigid rule-based routers with an autonomous cyclical StateGraph (`agent_node` <-> `tool_node`).
- **Autonomous Tool Selection:** Leverages strict Python docstrings as semantic schemas to automatically generate SQL queries, trigger global fallbacks, and query vector stores.
- **Circuit Breakers:** Configured runtime `recursion_limit` (8 hops) to protect against infinite reasoning loops and prevent budget exhaustion.

### 2. High-Performance Concurrency & Telemetry
- **Non-Blocking Runtime:** End-to-end asynchronous pipeline using `generate_content_async` and `app.ainvoke`.
- **Parallel Tool Execution:** Dispatches multiple database and vector search queries concurrently using `asyncio.gather` and background thread pooling (`asyncio.to_thread`), reducing multi-hop query latency by over **60%** (from ~20.6s baseline to ~7.3s - 9.4s).
- **Real-Time Observability:** Telemetry metrics tracked inside state, displaying total latency, token consumption, and per-tool execution times directly in the UI.

### 3. Multi-Tenant Conversational Memory (MemorySaver)
- **Isolated Sessions:** Uses LangGraph's `MemorySaver` checkpointer with React `useRef` session tokens to guarantee multi-user state isolation across browser tabs.
- **Append-Only Reducer:** Employs `chat_history: Annotated[list, operator.add]` state schema to prevent context overwriting and maintain multi-turn conversational context.

### 4. Multi-Engine Hybrid Retrieval
- **Structured Text-to-SQL:** Automated SQLite query generation for `projects` and `orders` tables with deterministic seed benchmarks.
- **Agentic Fallback:** Automatically cascades to SQLite FTS5 (Full-Text Search) when specific SQL filters return empty records.
- **Unstructured Vector RAG:** Custom 3072-dimensional Gemini embeddings (`models/gemini-embedding-001`) with chunk-level metadata extraction powering persistent ChromaDB retrieval.

### 5. Automated EvalOps Suite (LLM-as-a-Judge)
- **Scientific Benchmarking:** Integrated evaluation harness (`src/evals/evaluate_rag.py`) scoring RAG performance against a curated golden benchmark dataset.
- **Hallucination & Retrieval Auditing:** Computes Faithfulness, Answer Relevance, and Context Precision metrics with rate-limiting backoff resilience.

### 6. Cloud Native Infrastructure & CI/CD
- **Containerized Architecture:** Production `Dockerfile` with build-time secret isolation and cold-start idempotency checks (`init_vector_db.py`).
- **Microsoft Azure Cloud:** Hosted on Azure Linux App Service (Backend) and Azure Static Web Apps (Frontend CDN).
- **Automated GitOps:** Dual GitHub Actions workflows automatically build, package, test, and deploy code upon PR merge into `main`.

---

## 📊 Evaluation & Benchmark Scorecard

| Evaluation Metric | Benchmark Score | Description |
| :--- | :---: | :--- |
| **🛡️ Macro Faithfulness** | **100.0%** | Measures factual consistency; verifies zero hallucination against retrieved context. |
| **🎯 Macro Answer Relevance** | **100.0%** | Measures how directly and concisely the answer addresses the user's intent. |
| **📚 Macro Retrieval Precision** | **100.0%** | Verifies that ChromaDB retrieved the exact ground-truth policy sections. |
| **⭐ Overall Quality Index** | **100.0 / 100** | Aggregate benchmark health score across all test categories. |

---

## 📁 Directory Structure

    ai-chatbot/
    ├── .github/
    │   └── workflows/          # Automated GitHub Actions CI/CD workflows
    │       ├── main_smart-search-api.yml
    │       └── azure-static-web-apps-*.yml
    ├── client/                 # React Frontend Application
    │   ├── src/
    │   │   ├── App.js          # Chat UI with live telemetry pills & Azure API bridge
    │   │   └── App.css         # UI Styling
    │   ├── .npmrc              # Legacy peer-deps configuration
    │   └── package.json
    ├── knowledge_base/         # Corporate Policy Documents
    │   └── company_policies.txt 
    ├── src/                    # Backend Application Source
    │   ├── evals/              # Automated EvalOps Suite
    │   │   ├── __init__.py
    │   │   ├── golden_dataset.py # Benchmark ground-truth test cases
    │   │   └── evaluate_rag.py   # LLM-as-a-Judge evaluation runner
    │   ├── models/             # Pydantic Schemas & State Models
    │   │   └── ask_request_state.py
    │   ├── routes/             # FastAPI Route Controllers (Async /ask)
    │   │   └── ask.py
    │   ├── services/           # Database, Search, and Vector Execution Logic
    │   │   ├── project_service.py # SQLite project service with absolute paths
    │   │   ├── order_service.py   # SQLite order service with absolute paths
    │   │   ├── global_search_service.py # SQLite FTS5 service with absolute paths
    │   │   └── rag_service.py     # ChromaDB retrieval service
    │   ├── tools/              # Agent tool definitions
    │   │   ├── get_orders.py
    │   │   ├── get_projects.py
    │   │   └── global_search.py
    │   ├── utils/              # Centralized logging utilities
    │   │   └── logger.py
    │   ├── ai_agent.py         # Main LangGraph Async Engine & Tool Orchestrator
    │   ├── db_setup.py         # SQLite Schema & Deterministic Seed Initializer
    │   └── main.py             # FastAPI App with Lifespan & pysqlite3 override
    ├── init_vector_db.py       # Idempotent ChromaDB embedding vectorizer
    ├── Dockerfile              # Production container recipe
    ├── .dockerignore           # Container build exclusions
    ├── requirements.txt        # Pinned Python Dependencies
    ├── .env                    # Local Environment Configuration
    ├── PROJECT_AUDIT.md        # Architecture audit & roadmap tracker
    └── README.md               # Project documentation

---

## 🛠️ Getting Started

### Local Setup
```bash
# 1. Clone repository
git clone https://github.com/yashagrw/smart-search-assistant.git
cd smart-search-assistant

# 2. Setup Virtual Environment
python -m venv venv
.\venv\Scripts\activate      # Windows
source venv/bin/activate     # macOS/Linux

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Environment Variables (.env)
GEMINI_API_KEY=your_gemini_api_key_here

# 5. Initialize Databases
python src/db_setup.py
python init_vector_db.py

# 6. Run Backend
python -m uvicorn src.main:app --reload --port 8000

# 7. Run Frontend (in separate terminal)
cd client
npm install
npm start
```

### Running Automated Evaluations
```bash
python src/evals/evaluate_rag.py
```

## License
This project is intended for educational and demonstration purposes.