FROM python:3.11-slim

# Configuraciones esenciales de Python para Nube
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definimos el directorio de trabajo
WORKDIR /app

# Instalamos ffmpeg y herramientas base (necesario para procesamiento de video) [cite: 113]
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Instalamos dependencias [cite: 114]
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código fuente asegurando que los scripts estén en /app
COPY . .

# Exponemos el puerto para la API
EXPOSE 8080

# --- CAMBIO CRÍTICO PARA JOBS ---
# Usamos ENTRYPOINT ["python"] para que cualquier argumento enviado al contenedor
# sea interpretado como un script a ejecutar (ej: job_audio.py).
ENTRYPOINT ["python"]

# Por defecto, si no se envían argumentos (como en el servicio de Cloud Run),
# el contenedor ejecutará este comando para iniciar la API.
CMD ["-m", "uvicorn", "mainAPI:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--timeout-keep-alive", "650"]