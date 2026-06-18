# Smart Search Assistant Audit

## Active Runtime Components

- FastAPI
- React
- Gemini (google-generativeai)
- SQLite
- Services Layer

## Current Flow

User
↓
React
↓
/ask
↓
Gemini Router
↓
PROJECT / ORDER / GLOBAL_SEARCH / CHAT
↓
Services
↓
SQLite
↓
Response

## Legacy Candidates

### Tools
- src/tools/get_projects.py
- src/tools/get_orders.py
- src/tools/global_search.py
- src/tools/__init__.py

### Commented Agent Code
- create_react_agent
- MemorySaver

## Installed But Currently Unused

- langgraph
- langchain-google-genai
- langchain-openai
- openai