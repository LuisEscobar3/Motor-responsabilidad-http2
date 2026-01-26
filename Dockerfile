FROM python:3.11-slim

# Configuraciones esenciales de Python para Nube
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalamos ffmpeg para procesamiento de audio y herramientas de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Instalamos dependencias (Asegúrate de que Pydantic esté en tu requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY . .

EXPOSE 8080

# 🚀 INICIO LIMPIO:
# Usamos el modo estándar de uvicorn que es 100% compatible con Apps Script
CMD ["uvicorn", "mainAPI:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "650"]