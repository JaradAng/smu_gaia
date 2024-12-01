# Use the official Milvus image as the base
FROM milvusdb/milvus:v2.3.0

WORKDIR /app

# # Install additional dependencies for Python (if needed for integration tasks)
# RUN apt-get update && apt-get install -y \
#     python3 \
#     python3-pip \
#     build-essential \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# # Install Python packages (if necessary for your application)
# COPY requirements.txt .
# RUN pip3 install --no-cache-dir -r requirements.txt

# Add custom configurations for Milvus (if applicable)
# COPY ./custom_configs /milvus/configs/

# Copy Python code or other application files
COPY main.py .

# Ensure Milvus binary is available and standalone mode is used
CMD ["milvus", "run", "standalone"]


# # Install build dependencies
# RUN apk add --no-cache \
#     build-base \
#     gcc \
#     musl-dev \
#     python3-dev

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Create non-root user
# RUN adduser -D appuser
# RUN chown -R appuser:appuser /app
# USER appuser

# COPY main.py .

# # CMD ["celery", "-A", "main", "worker", "--concurrency=2", "-l", "info", "-Q", "vector_db"]

# # # Add any customizations here, if needed
# # COPY ./custom_configs /milvus/configs/

# # Ensure the `milvus` binary is available
# CMD ["milvus", "run", "standalone"]