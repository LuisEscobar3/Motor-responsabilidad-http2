import sys
import httpx
import asyncio
import os
import time
import json
from google.cloud import storage

# --- CONFIGURACIÓN GCP ---
PROJECT_ID = "sb-iapatrimoniales-dev"
BUCKET_NAME = "bucket-motor-responsabilidad"

# Inicializamos el cliente de Storage
# Nota: Asegúrate de tener la variable GOOGLE_APPLICATION_CREDENTIALS en tu entorno
storage_client = storage.Client(project=PROJECT_ID)


def verificar_descarga_completa(blob_name):
    """Verifica la existencia y accesibilidad del archivo en GCS."""
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)

        if not blob.exists():
            print(f"❌ [VERIFICACIÓN] El archivo {blob_name} no existe en el bucket.")
            return False

        t_descarga_ini = time.perf_counter()
        # Descarga de prueba
        contenido = blob.download_as_bytes()
        t_descarga_fin = time.perf_counter() - t_descarga_ini

        tamano_mb = len(contenido) / (1024 * 1024)
        print(f"📥 [VERIFICACIÓN] Descarga exitosa: {blob_name} ({tamano_mb:.2f} MB) en {t_descarga_fin:.2f}s")
        return True
    except Exception as e:
        print(f"❌ [VERIFICACIÓN] Error descargando {blob_name}: {e}")
        return False


def subir_a_gcs(ruta_local):
    """Sube el archivo local al bucket y retorna su URI gs://"""
    if not os.path.exists(ruta_local):
        print(f"⚠️ Archivo no encontrado localmente: {ruta_local}")
        return None

    nombre_archivo = os.path.basename(ruta_local)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(nombre_archivo)

    print(f"📤 Subiendo {nombre_archivo}...", end=" ", flush=True)
    blob.upload_from_filename(ruta_local)
    print("✅")

    # Validamos que subió correctamente antes de proceder
    if verificar_descarga_completa(nombre_archivo):
        return f"gs://{BUCKET_NAME}/{nombre_archivo}"
    else:
        return None


async def ejecutar_test():
    # URL del servicio Cloud Run (desplegado en modo HTTP/1.1)
    url_api = "https://ia-motor-api-993828145189.us-east1.run.app/process-case"
    #url_api = "http://127.0.0.1:8000/process-case"

    # Diccionario con tus archivos locales
    archivos_locales = {
        "pdf": "ejemplo/sebastian.ortiz.matiz@segurosbolivar.com - 15400065559/15400065559.pdf",
        "audio1": "ejemplo/sebastian.ortiz.matiz@segurosbolivar.com - 15400065559/Llamada1-10e45b09-4ef7-426d-b05f-d45307b2170f.MP3",
        "audio2": "ejemplo/sebastian.ortiz.matiz@segurosbolivar.com - 15400065559/Llamada1-e9181c80-9ec7-4d8f-aed5-8c3b71b7cf09.MP3"
    }

    print("\n" + "=" * 50)
    print("🚀 [PASO 1] SUBIDA Y VALIDACIÓN DE ARCHIVOS")
    print("=" * 50)

    uris = {}
    for key, path in archivos_locales.items():
        uri = subir_a_gcs(path)
        if not uri:
            print(f"🛑 Error crítico en el archivo {key}. El test se detendrá.")
            return
        uris[key] = uri

    # Construcción del Payload con URIs dinámicas
    payload = {
        "case_id": f"TEST-GCS-{int(time.time())}",
        "urls_visuales": [uris["pdf"]],
        "urls_audios": [uris["audio1"], uris["audio2"]],
        "urls_videos": []
    }

    print("\n" + "=" * 50)
    print("📡 [PASO 2] ENVIANDO PETICIÓN A CLOUD RUN")
    print("=" * 50)

    # CONFIGURACIÓN DE COMPATIBILIDAD TOTAL:
    # Desactivamos HTTP/2 para evitar el Error 502 Protocol Error
    # Timeout de 600 segundos (10 minutos)
    async with httpx.AsyncClient(http1=True, http2=False, timeout=600.0) as client:
        try:
            t_ini = time.perf_counter()
            response = await client.post(url_api, json=payload)
            t_total = time.perf_counter() - t_ini

            print(f"⏱️ Tiempo de respuesta: {t_total:.2f}s")
            print(f"📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                print("✅ API completada con éxito.")
                data = response.json()

                print("\n" + "=" * 50)
                print("📝 RESULTADO DEL ANÁLISIS (JSON)")
                print("=" * 50)

                # Imprimimos el JSON con formato legible e indentación
                print(json.dumps(data, indent=4, ensure_ascii=False))

            else:
                print(f"❌ Error API ({response.status_code}): {response.text}")

        except httpx.ReadTimeout:
            print("❌ Error: Se excedió el tiempo de espera del servidor (Timeout).")
        except Exception as e:
            print(f"❌ Error de conexión: {e}")


if __name__ == "__main__":
    # Verificamos credenciales antes de empezar
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("⚠️  AVISO: La variable GOOGLE_APPLICATION_CREDENTIALS no está configurada.")
        print("Asegúrate de haber corrido: export GOOGLE_APPLICATION_CREDENTIALS='tu-archivo.json'")

    asyncio.run(ejecutar_test())