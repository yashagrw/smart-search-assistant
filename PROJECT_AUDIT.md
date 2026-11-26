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
- [x] Built persistent ChromaDB vector store using Gemini 3072-dim embeddings.

### Milestone 3: Concurrency, Telemetry & Latency Optimization (COMPLETED ✅)
- [x] Converted end-to-end orchestration to non-blocking async execution (`generate_content_async` & `app.ainvoke`).
- [x] Implemented parallel tool dispatching using `asyncio.gather` and background thread pooling (`asyncio.to_thread`).
- [x] Added runtime telemetry tracing: per-node latency (ms) and token consumption metrics.
- [x] Integrated live telemetry badges into React UI (`App.js`).
- [x] Configured runtime `recursion_limit` (8 hops) as a cost and runaway loop circuit breaker.

### Milestone 4: Automated EvalOps Suite (COMPLETED ✅)
- [x] Curated ground-truth benchmark dataset covering cancellations, HR policies, IT SLAs, and hallucination traps.
- [x] Built automated LLM-as-a-Judge evaluation engine (`src/evals/evaluate_rag.py`).
- [x] **Benchmark Results:** 100.0% Macro Faithfulness, Relevance, and Retrieval Precision.
- [x] Automated 8/8 `pytest` suite for API endpoint AsyncMocking and SQLite execution verification.

### Milestone 5: Containerization & Cloud Deployment (COMPLETED ✅)
- [x] Authored production-ready `Dockerfile` and `.dockerignore` with build-time vs runtime secret separation.
- [x] Deployed FastAPI backend to Microsoft Azure Linux App Service (Basic B1 tier) with `pysqlite3-binary` fix.
- [x] Deployed React frontend to Azure Static Web Apps CDN with `.npmrc` peer dependency resolution.
- [x] Integrated database initialization into FastAPI `lifespan` startup hook.
- [x] Established automated dual-pipeline CI/CD using GitHub Actions on every `main` branch push.

### Milestone 6: Model Context Protocol (MCP) Architecture (COMPLETED ✅)
- [x] Decoupled agent from direct tool invocations using Anthropic's open-standard MCP SDK (`MCPServer`).
- [x] Built isolated domain servers: `SQLite-MCP-Server` and `RAG-MCP-Server`.
- [x] Implemented `MCPClientRouter` for dynamic JSON-schema discovery and parallel JSON-RPC dispatching.

### Milestone 7: Enterprise Security Guardrails (COMPLETED ✅)
- [x] Implemented Prompt Injection firewall (Input Guardrail) to block jailbreaks and destructive SQL (`DROP TABLES`).
- [x] Implemented PII redaction pipeline (Output Guardrail) for masking emails and sensitive identifiers.

### Milestone 8: LLM Gateway & High Availability (COMPLETED ✅)
- [x] Replaced vendor-locked Gemini SDK with universal `LiteLLM` router framework.
- [x] Configured automated failover routing (`fallbacks`) to ensure 99.99% uptime during rate limits.
- [x] Standardized tool schemas into universal OpenAI function-calling format.

---

## 📊 Technical Debt & Production War Stories Log
| Item / Incident | Root Cause | Engineering Resolution | Status |
| :--- | :--- | :--- | :---: |
| **App Service F1 Quota 503** | F1 Free tier daily 60 CPU minutes exhausted during heavy pip compilation. | Scaled App Service plan up to Basic B1 using $200 trial credits with dedicated compute. | Resolved ✅ |
| **Linux SQLite 3.35 ChromaDB Crash** | Azure Linux base image contained legacy SQLite 3.31, causing `RuntimeError` on ChromaDB import. | Injected `pysqlite3-binary` wheel override into `sys.modules['sqlite3']` at application entrypoints. | Resolved ✅ |
| **React Build ERESOLVE Failure** | React 19 conflicted with legacy `@botui/react` peer dependency in GitHub Actions. | Removed dead dependency from `package.json`, added `legacy-peer-deps=true` to `.npmrc`, and set `CI: false`. | Resolved ✅ |
| **Empty Query Results `[]` on Cloud** | Relative path directory drift and non-deterministic random IDs in `db_setup.py`. | Seeded deterministic benchmark records, locked absolute `BASE_DIR` paths, and wired setup into FastAPI `lifespan`. | Resolved ✅ |