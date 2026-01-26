FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias de sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Instalación de librerías
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Comando optimizado para HTTP/1.1 (Apps Script Compatible)
CMD ["uvicorn", "mainAPI:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "650"]