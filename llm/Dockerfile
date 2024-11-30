# Use the Hugging Face transformers PyTorch CPU image
FROM huggingface/transformers-pytorch-cpu:latest

# Set the locale
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Install minimal required system dependencies
RUN apt-get update && apt-get install -y \
    dnsutils \
    gcc \
    g++ \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Copy application scripts
COPY main.py legal_llm_analysis.py test_model_download.py ./

# Define the default command
CMD ["celery", "-A", "main", "worker", "-l", "info", "-Q", "llm"]
