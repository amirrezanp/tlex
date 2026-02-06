# Dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y wireguard curl unzip certbot paramiko && \
    curl -L -o xray.zip https://github.com/XTLS/Xray-core/releases/download/v1.8.0/Xray-linux-64.zip && \
    unzip xray.zip && mv xray /usr/local/bin && chmod +x /usr/local/bin/xray && rm xray.zip && \
    apt-get clean

COPY . /app

WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt  # If requirements.txt, or . for setup.py

ENTRYPOINT ["python", "-m", "tlex.main", "run"]