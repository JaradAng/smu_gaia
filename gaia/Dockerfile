FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libsqlite3-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install docker

COPY . .

# EXPOSE 8000  # adjust if we need to go out of docker

CMD ["python", "main.py"]