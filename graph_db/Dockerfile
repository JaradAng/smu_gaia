FROM python:3.9-alpine
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    linux-headers

# Upgrade pip, setuptools, and wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download SpaCy model
RUN python -m spacy download en_core_web_sm

# Create a non-root user
RUN adduser -D appuser
RUN chown -R appuser:appuser /app
USER appuser

# Copy application files
COPY main.py neo4j_input.py .

# Define the default command
CMD ["celery", "-A", "main", "worker", "--concurrency=2", "-l", "info", "-Q", "graph_db", "--max-memory-per-child", "51200", "--max-tasks-per-child", "250"]
