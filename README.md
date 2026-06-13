# Smart Search Assistant using Gemini and SQLite

## Overview

Smart Search Assistant is an AI-powered application that enables natural language interaction with project and order data. The application combines a React frontend with a FastAPI backend and leverages Gemini 2.5 Flash to intelligently route user requests and generate meaningful responses.

Users can retrieve information using conversational queries instead of manually writing database queries. The system supports project search, order retrieval, and global full-text search across datasets stored in SQLite.

---

## Features

### AI-Powered Query Processing

* Gemini 2.5 Flash integration for intelligent request handling
* Natural language understanding for user queries
* AI-driven routing to determine the appropriate data retrieval strategy
* Human-friendly response formatting

### Project Search

* Retrieve project information using natural language
* Search by project number, status, or other project attributes
* Structured and readable output formatting

### Order Search

* Retrieve order information using conversational queries
* Search by file number, status, or address
* AI-generated SQL queries executed against SQLite

### Global Search

* Full-text search across projects and orders
* SQLite FTS5-powered search capabilities
* Prefix matching and fallback substring matching
* Deduplicated results for improved accuracy

### Frontend Experience

* Modern React-based chat interface
* Rich text rendering for formatted responses
* Loading states and error handling
* Responsive user experience

### Backend Capabilities

* FastAPI-powered REST API
* Environment-based configuration management
* Centralized logging and error handling
* Modular service-oriented architecture

---

## Architecture

```text
┌──────────────────┐
│  React Frontend  │
│   (Port 4000)    │
└────────┬─────────┘
         │ HTTP
         ▼
┌──────────────────┐
│ FastAPI Backend  │
│   (Port 8000)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Gemini 2.5 Flash │
│ AI Query Routing │
└────────┬─────────┘
         │
         ├────────────► Project Search
         │
         ├────────────► Order Search
         │
         └────────────► Global Search
                           │
                           ▼
                  ┌────────────────┐
                  │ SQLite + FTS5  │
                  │ Local Database │
                  └────────────────┘
```

---

## Technology Stack

### Backend

* Python
* FastAPI
* SQLite
* SQLite FTS5
* Google Gemini 2.5 Flash
* Uvicorn
* Pydantic

### Frontend

* React
* JavaScript (ES6+)
* CSS
* React Markdown

### AI & Search

* Gemini 2.5 Flash
* Natural Language to SQL Generation
* Full-Text Search (FTS5)

---

## Project Structure

```text
ai-chatbot/
├── client/
│   ├── public/
│   └── src/
│       ├── App.js
│       ├── App.css
│       └── index.js
│
├── src/
│   ├── ai_agent.py
│   ├── main.py
│   ├── db_setup.py
│   │
│   ├── models/
│   │   └── ask_request_state.py
│   │
│   ├── routes/
│   │   └── ask.py
│   │
│   ├── services/
│   │   ├── project_service.py
│   │   ├── order_service.py
│   │   └── global_search_service.py
│   │
│   ├── tools/
│   │   ├── get_projects.py
│   │   ├── get_orders.py
│   │   ├── global_search.py
│   │   └── __init__.py
│   │
│   └── utils/
│       └── logger.py
│
├── local_data.db
├── requirements.txt
├── .env
└── README.md
```

---

## Getting Started

### Prerequisites

* Python 3.9+
* Node.js 16+
* npm or Yarn
* Gemini API Key

---

## Backend Setup

```bash
git clone <repository-url>
cd ai-chatbot

python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Initialize the local database:

```bash
python src/db_setup.py
```

Run the backend:

```bash
python -m uvicorn src.main:app --reload --port 8000
```

---

## Frontend Setup

```bash
cd client

npm install

npm start
```

---

## Application URLs

Frontend:

```text
http://localhost:4000
```

Backend:

```text
http://localhost:8000
```

API Documentation:

```text
http://localhost:8000/docs
```

---

## Example Queries

### Project Queries

```text
Show open projects

Find project P64852978

List cancelled projects
```

### Order Queries

```text
Show open orders

Find order END9756309

List cancelled orders
```

### Global Search Queries

```text
Maple Dr

Search for Springfield

Find information related to END9756309
```

---

## Error Handling

The application provides user-friendly responses for common issues, including:

* API rate limiting
* Authentication failures
* Empty AI responses
* Unexpected backend exceptions

---

## Future Enhancements

* LangGraph integration for advanced agent workflows
* Tavily search integration for external information retrieval
* Conversation memory support
* Deployment automation
* Enhanced analytics and monitoring

---

## License

This project is intended for educational, learning, and demonstration purposes.
