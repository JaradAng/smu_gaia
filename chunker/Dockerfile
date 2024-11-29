FROM python:3.9-slim

WORKDIR /app

# Install only essential build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

COPY main.py .

CMD ["celery", "-A", "main", "worker", "--concurrency=2", "-l", "info", "-Q", "chunker"]

