# Build stage
FROM python:3.9-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.9-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /opt/venv /opt/venv
COPY main.py .
COPY data/ /app/data

# Set up path and non-root user
ENV PATH="/opt/venv/bin:$PATH"
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Install minimal runtime dependencies if needed
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # Add any runtime-only system dependencies here
    && rm -rf /var/lib/apt/lists/*

USER appuser

CMD ["celery", "-A", "main", "worker", "--concurrency=2", "-l", "info", "-Q", "chunker", "--max-memory-per-child", "51200", "--max-tasks-per-child", "250"]