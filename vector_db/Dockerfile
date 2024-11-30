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

# Create non-root user
RUN adduser -D appuser
RUN chown -R appuser:appuser /app
USER appuser

COPY main.py .

CMD ["celery", "-A", "main", "worker", "--concurrency=2", "-l", "info", "-Q", "vector_db"]

