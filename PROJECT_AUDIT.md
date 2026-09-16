# 📋 Smart Search Assistant: Technical Architecture & Progress Audit

## Executive Summary
This document serves as the single source of truth for the architectural evolution, benchmarking metrics, production deployments, and roadmap status of the Smart Search Assistant system.

---

## 🌐 Production Deployments
- **Frontend URL (Azure Static Web Apps):** `https://brave-desert-0c8ba5800.6.azurestaticapps.net`
- **Backend API Docs (Azure App Service):** `https://smart-search-api-h5dzh8hkdqhbf3bu.centralindia-01.azurewebsites.net/docs`

---

## 🏗️ Architectural Milestone Audit

### Milestone 1: Agent Framework & Text-to-SQL Migration (COMPLETED ✅)
- [x] Migrated from monolithic `if-else` intent router to cyclical LangGraph StateGraph.
- [x] Replaced LangChain LLM abstraction with native Google Gemini SDK (`google-generativeai==0.8.6`).
- [x] Automated Text-to-SQL using strict table schema docstrings for `projects` and `orders`.
- [x] Implemented agentic fallback to SQLite FTS5 full-text search upon empty SQL queries.

### Milestone 2: Conversational Memory & Multi-Tenant State Isolation (COMPLETED ✅)
- [x] Integrated LangGraph `MemorySaver` global checkpointer.
- [x] Designed append-only state reducer `chat_history: Annotated[list, operator.add]`.
- [x] Implemented React `useRef` session isolation to guarantee multi-tab thread separation.
- [x] Built persistent ChromaDB vector store using Gemini 3072-dim embeddings (`rag_service.py`).

### Milestone 3: Concurrency, Telemetry & Latency Optimization (COMPLETED ✅)
- [x] Converted end-to-end orchestration to non-blocking async execution (`generate_content_async` & `app.ainvoke`).
- [x] Implemented parallel tool dispatching using `asyncio.gather` and background thread pooling (`asyncio.to_thread`).
- [x] Added runtime telemetry tracing: per-node latency (ms) and token consumption metrics.
- [x] Integrated live telemetry badges into React UI (`App.js`).
- [x] Configured runtime `recursion_limit` (8 hops) as a cost and runaway loop circuit breaker.
- [x] **Benchmark Impact:** Reduced multi-hop resolution latency from **~20.6s baseline to ~7.3s - 9.4s** (>60% reduction).
- [x] **Token Optimization:** Reduced multi-intent query consumption from **3696 tokens to 2804 tokens** (~24% savings).

### Milestone 4: Automated EvalOps Suite (COMPLETED ✅)
- [x] Curated ground-truth benchmark dataset (`src/evals/golden_dataset.py`) covering cancellations, refund escalations, IT hardware support, cafeteria rules, and hallucination traps.
- [x] Built automated LLM-as-a-Judge evaluation engine (`src/evals/evaluate_rag.py`).
- [x] Implemented automated metric scoring across Faithfulness, Answer Relevance, and Context Precision.
- [x] Added exponential backoff and pacing mechanisms for API quota resilience.
- [x] **Benchmark Results:**
  - **Macro Faithfulness (Zero Hallucination):** 100.0%
  - **Macro Answer Relevance:** 100.0%
  - **Macro Retrieval Precision:** 100.0%
  - **Overall RAG Quality Index:** 100.0 / 100

### Milestone 5: Containerization & Cloud Deployment (COMPLETED ✅)
- [x] Authored production-ready `Dockerfile` and `.dockerignore` with build-time vs runtime secret separation.
- [x] Optimized vector store cold-start latency using an idempotency check (`init_vector_db.py`).
- [x] Deployed FastAPI backend to Microsoft Azure Linux App Service (Basic B1 tier).
- [x] Resolved Linux ChromaDB runtime conflict by injecting `pysqlite3-binary` to supply modern SQLite >= 3.35.0.
- [x] Deployed React frontend to Azure Static Web Apps CDN with `.npmrc` peer dependency resolution.
- [x] Integrated database initialization into FastAPI `lifespan` startup hook.
- [x] Unified absolute path resolution (`os.path.abspath`) across all SQLite and FTS5 service modules.
- [x] Established automated dual-pipeline CI/CD using GitHub Actions on every `main` branch push.

---

## 🔮 Upcoming Roadmap Milestones

### Milestone 6: Model Context Protocol (MCP) (UP NEXT ⏳)
- [ ] Convert SQLite database tools and ChromaDB vector tools into official Anthropic-standard MCP Servers.
- [ ] Connect MCP clients to expose standardized agent tool interfaces.

### Milestone 7: Enterprise Guardrails & Anti-Jailbreak (PLANNED ⏳)
- [ ] Implement Prompt Injection defense and strict corporate boundary filters.
- [ ] Add PII sanitization and input/output safety firewalls.

### Milestone 8: LLM Gateways & High Availability (PLANNED ⏳)
- [ ] Implement LiteLLM router for automated cross-model failover (Gemini -> Claude / OpenAI fallback).
- [ ] Configure circuit-breaker fallbacks during provider rate limits or outages.

---

## 📊 Technical Debt & Production War Stories Log
| Item / Incident | Root Cause | Engineering Resolution | Status |
| :--- | :--- | :--- | :---: |
| **App Service F1 Quota 503** | F1 Free tier daily 60 CPU minutes exhausted during heavy pip compilation. | Scaled App Service plan up to Basic B1 using $200 trial credits with dedicated compute. | Resolved ✅ |
| **Linux SQLite 3.35 ChromaDB Crash** | Azure Linux base image contained legacy SQLite 3.31, causing `RuntimeError` on ChromaDB import. | Injected `pysqlite3-binary` wheel override into `sys.modules['sqlite3']` at application entrypoints. | Resolved ✅ |
| **React Build ERESOLVE Failure** | React 19 conflicted with legacy `@botui/react` peer dependency in GitHub Actions. | Removed dead dependency from `package.json`, added `legacy-peer-deps=true` to `.npmrc`, and set `CI: false`. | Resolved ✅ |
| **Empty Query Results `[]` on Cloud** | Relative path directory drift and non-deterministic random IDs in `db_setup.py`. | Seeded deterministic benchmark records, locked absolute `BASE_DIR` paths, and wired setup into FastAPI `lifespan`. | Resolved ✅ |