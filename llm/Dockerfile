FROM huggingface/transformers-pytorch-cpu:latest

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential 

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /bin/bash appuser

RUN chown -R appuser:appuser /app

USER appuser

COPY main.py legal_llm_analysis.py ./

CMD ["celery", "-A", "main", "worker", "-l", "info", "-Q", "llm"]

