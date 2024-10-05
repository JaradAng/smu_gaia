FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libsqlite3-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY main.py .

CMD ["python", "main.py"]