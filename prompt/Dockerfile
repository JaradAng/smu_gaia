FROM python:3.9-alpine

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    gcc \
    musl-dev \
    python3-dev

# Copy gaia utils module
COPY gaia/utils /app/gaia/utils

# Copy service files
COPY prompt/requirements.txt .
RUN pip install -r requirements.txt

# Create non-root user
RUN adduser -D appuser
RUN chown -R appuser:appuser /app
USER appuser

COPY prompt/main.py prompt/prompt_generator.py ./

CMD ["celery", "-A", "main", "worker", "--concurrency=2", "-l", "info", "-Q", "prompt"]