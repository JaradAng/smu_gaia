FROM python:3.9-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential 

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
RUN useradd --create-home --shell /bin/bash appuser

RUN chown -R appuser:appuser /app

USER appuser

COPY main.py .
COPY neo4j_input.py .

CMD ["celery", "-A", "main", "worker", "-l", "info", "-Q", "graph_db"]

