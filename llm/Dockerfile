FROM huggingface/transformers-pytorch-cpu:latest

# Set the locale
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Install system dependencies
RUN apt-get update && apt-get install -y \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /bin/bash appuser

RUN chown -R appuser:appuser /app

USER appuser

COPY main.py legal_llm_analysis.py test_model_download.py ./

CMD ["celery", "-A", "main", "worker", "-l", "info", "-Q", "llm"]