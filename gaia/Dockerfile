FROM python:3.9-alpine

WORKDIR /app

# Install build dependencies and sqlite
RUN apk add --no-cache \
    build-base \
    gcc \
    musl-dev \
    python3-dev \
    sqlite \
    sqlite-dev \
    libffi-dev \
    docker-cli \
    docker-py \
    py3-pip \
    openssl-dev \
    rust \
    cargo

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]