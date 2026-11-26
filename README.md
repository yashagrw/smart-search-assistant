# 🚀 Smart Search Assistant: Enterprise-Grade Agentic Search Engine

An autonomous, multi-tenant AI search assistant built with **LangGraph**, **LiteLLM**, **FastAPI**, and **React**, deployed globally on **Microsoft Azure**. The system intelligently resolves complex multi-intent queries across structured relational databases (SQLite), full-text search indexes (FTS5), and unstructured corporate knowledge bases (ChromaDB Vector RAG).

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
    │        - Regex Input Guardrails (Anti-Jailbreak)       │
    │        - Output Sanitization (PII Redaction)           │
    └───────────────────────────┬────────────────────────────┘
                                │ await app.ainvoke
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │               LangGraph StateGraph Workflow            │
    │                                                        │
    │  ┌────────────────┐                      ┌───────────┐ │
    │  │   agent_node   │                      │ tool_node │ │
    │  │ (LiteLLM HA)   │--- MCP JSON-RPC ---->│ (gather)  │ │
    │  └───────┬────────┘                      └─────┬─────┘ │
    │          │                                     │       │
    └──────────┼─────────────────────────────────────┼───────┘
               │                                     │
               ▼                                     ▼
        [Final Answer]                    ┌────────────────────────────┐
                                          │      MCPClientRouter       │
                                          └──────┬──────────────┬──────┘
                                                 │              │
                                          ┌──────▼──────┐ ┌─────▼──────┐
                                          │ SQLite MCP  │ │  RAG MCP   │
                                          └─────────────┘ └────────────┘

---

## ✨ Core Engineering Capabilities

### 1. High-Availability LLM Gateway (LiteLLM)
- **Multi-Model Routing:** Completely abstracted LLM SDKs using LiteLLM, providing standardized OpenAI-format schemas across Gemini, Claude, and Azure OpenAI models.
- **Failover & Resilience:** Configured automated fallbacks (`gemini-2.5-flash` -> `gemini-1.5-flash`) ensuring 99.99% reasoning uptime during provider rate-limits (429/503).

### 2. Decoupled Tooling via Model Context Protocol (MCP)
- **Microservices Architecture:** Extracted tightly-coupled database functions into two independent MCP Servers (`SQLite-MCP-Server` and `RAG-MCP-Server`).
- **Universal JSON-RPC Integration:** Agent interacts with tools dynamically via a central `MCPClientRouter`, enabling seamless adoption by external clients (Claude Desktop, Cursor IDE).

### 3. Enterprise Guardrails & Anti-Jailbreak 🛡️
- **Input Firewall:** Regex-based pre-processing blocks adversarial prompt injections and destructive SQL commands (0ms latency block).
- **PII Redaction:** Output sanitization pipeline masks sensitive emails and financial identifiers before client delivery.

### 4. Advanced Two-Stage Vector RAG
- **Stage 1 (Broad Fetch):** ChromaDB bi-encoder fetches top-8 candidates across 4 enterprise domains (HR, IT, Finance, Support).
- **Stage 2 (Re-ranking):** Deterministic cross-scoring engine re-evaluates exact term overlap and departmental metadata to return the Top-2 highest precision chunks.

### 5. Automated EvalOps Suite & Pytest
- **Scientific Benchmarking:** Integrated LLM-as-a-Judge evaluation engine scoring RAG performance against a curated golden dataset (100% Faithfulness, Relevance, Precision).
- **Automated Testing:** 8 robust `pytest` cases verifying API Mocking (`AsyncMock`), SQLite logic, and Re-ranking math.

### 6. Cloud Native Infrastructure & CI/CD
- **Microsoft Azure Cloud:** Hosted on Azure Linux App Service (Backend) and Azure Static Web Apps (Frontend CDN).
- **Automated GitOps:** Dual GitHub Actions workflows automatically build, test, and deploy code upon PR merge.

---

## 🛠️ Getting Started
```bash
# 1. Clone repository
git clone https://github.com/yashagrw/smart-search-assistant.git
cd smart-search-assistant

# 2. Setup Virtual Environment
python -m venv venv
.\venv\Scripts\activate      # Windows

# 3. Install Dependencies
pip install -r requirements.txt
pip install mcp litellm pytest httpx

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