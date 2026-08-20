# Smart Search Assistant Audit

## Active Runtime Components
- **Backend:** FastAPI, Uvicorn, Pydantic
- **Frontend:** React
- **AI/LLM:** Google Gemini 2.5 Flash (via `google-generativeai`)
- **Agent Orchestration:** LangGraph (StateGraph, MemorySaver)
- **Structured Database:** SQLite (with FTS5 Virtual Tables)
- **Vector Database (RAG):** ChromaDB (Persistent)
- **Embeddings:** Gemini Embeddings (`models/gemini-embedding-001`)

## Current Architecture Flow
1. User submits a query via React frontend (with a unique `thread_id` via `useRef`).
2. FastAPI receives the request and initializes the LangGraph Agent.
3. LangGraph retrieves chat history using `MemorySaver`.
4. Gemini LLM evaluates the query and context to determine required tools.
5. **Tool Execution Options:**
   - `search_project_database`: Generates SQL for project tracking.
   - `search_order_database`: Generates SQL for order management.
   - `search_global_database`: Fallback FTS5 full-text keyword search.
   - `search_company_policies`: RAG pipeline utilizing ChromaDB for unstructured data (via `src/services/rag_service.py`).
6. The Agent synthesizes tool results and loops until a comprehensive answer is formed.
7. Final formatted Markdown response is sent back to the frontend.

## Key Milestones Achieved
- [x] Replaced legacy single-intent routing with LangGraph Autonomous Agent.
- [x] Implemented Thread-Isolated Memory (Ghajini-cure) for multi-turn conversations.
- [x] Added dynamic Text-to-SQL generation through Tool Docstrings.
- [x] Integrated Production-Grade RAG Pipeline (Chunk Overlap, Metadata Injection, Upsert operations).
- [x] Extracted RAG logic to dedicated `rag_service` for clean architecture (Separation of Concerns).

## Future / Pending Considerations
- Multi-Agent Teams (Supervisor + Specialized Workers).
- Async execution (`ainvoke`) for higher concurrency scaling.