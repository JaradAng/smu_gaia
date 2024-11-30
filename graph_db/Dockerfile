FROM python:3.9-alpine
WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential 

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN adduser -D appuser
RUN chown -R appuser:appuser /app
USER appuser

COPY main.py .
COPY neo4j_input.py .

CMD ["celery", "-A", "main", "worker", "--concurrency=2", "-l", "info", "-Q", "graph_db"]

