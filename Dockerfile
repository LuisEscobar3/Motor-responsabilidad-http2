FROM python:3.11-slim

# Evita que Python genere archivos .pyc y asegura que los logs salgan directo a GCP
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalamos dependencias del sistema esenciales para procesamiento de IA y Audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instalamos uvicorn con soporte completo para HTTP/2 (h2)
RUN pip install --no-cache-dir -r requirements.txt uvicorn[standard] h2

COPY . .

EXPOSE 8080

# AJUSTE TÉCNICO:
# 1. --timeout-graceful-shutdown: Da tiempo a la IA a terminar antes de matar el contenedor.
# 2. --keep-alive-timeout: Crucial para que Cloud Run no piense que la conexión murió.
# 3. --workers 1: En Cloud Run con 4 CPUs, es mejor dejar que Cloud Run escale instancias
#    en lugar de saturar una sola con demasiados workers de Python (evita bloqueos).

# Eliminamos --http h2 para evitar el error de importación
# Cloud Run se encarga de la terminación HTTP/2 y se comunica con Uvicorn
CMD ["uvicorn", "mainAPI:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "650"]