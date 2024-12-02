FROM python:3.9-alpine
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    gcc \
    musl-dev \
    python3-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

# Create shared data directory
RUN mkdir /shared_data

# Create non-root user
RUN adduser -D appuser
RUN chown -R appuser:appuser /app /shared_data
USER appuser
COPY main.py neo4j_input.py .

CMD ["celery", "-A", "main", "worker", "--concurrency=2", "-l", "info", "-Q", "graph_db", "--max-memory-per-child", "51200", "--max-tasks-per-child", "250"]
