# 1. Base Image: Lightweight Debian Linux with Python 3.11
FROM python:3.11-slim

# 2. Set environment variables for optimized Python execution
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set container working directory
WORKDIR /app

# 4. Install system dependencies required for SQLite and ChromaDB builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 5. Leverage Docker layer caching: Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy application source code into the container
COPY . .

# 7. Expose the FastAPI network port
EXPOSE 8000

# 8. Container startup entrypoint: Initialize DBs with secure runtime keys, then launch Uvicorn
CMD ["sh", "-c", "python src/db_setup.py && python init_vector_db.py && uvicorn src.main:app --host 0.0.0.0 --port 8000"]