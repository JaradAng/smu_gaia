FROM python:3.9-slim

WORKDIR /app

# Copy gaia utils module
COPY gaia/utils /app/gaia/utils

# Copy service files
COPY prompt/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /bin/bash appuser

RUN chown -R appuser:appuser /app

USER appuser

COPY prompt/main.py prompt/prompt_generator.py ./

CMD ["celery", "-A", "main", "worker", "-l", "info", "-Q", "prompt"]
