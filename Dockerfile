FROM python:3.11-slim

WORKDIR /app

# Esto asegura que si una librería necesita compilar algo de gRPC o Audio, no falle.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instalamos las librerías y el soporte para HTTP/2
RUN pip install --no-cache-dir -r requirements.txt uvicorn[standard] h2

COPY . .

EXPOSE 8080

# Ejecución con los timeouts que pediste (10 min) y protocolo h2
CMD ["uvicorn", "mainAPI:app", "--host", "0.0.0.0", "--port", "8080", "--http", "h2", "--timeout-keep-alive", "650"]