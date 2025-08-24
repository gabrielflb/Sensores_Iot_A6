FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .


RUN apt-get update && apt-get install -y \
    gcc \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/wait-for-mosquitto.sh

EXPOSE 8000
EXPOSE 5683/udp
