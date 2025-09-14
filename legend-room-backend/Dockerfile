FROM python:3.11-slim

# Install system dependencies for building wheels and utilities
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock ./

# Install dependencies (no project files yet)
RUN poetry install --no-interaction --no-ansi

# Copy project files
COPY . .

ENV PORT=8080

CMD ["poetry","run","uvicorn","legend_room_backend.main:app","--host","0.0.0.0","--port","8080"]

