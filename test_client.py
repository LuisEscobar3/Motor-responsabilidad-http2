import sys

import httpx
import asyncio
import os
import time
from google.cloud import storage

# --- CONFIGURACIÓN GCP ---
PROJECT_ID = "sb-iapatrimoniales-dev"
BUCKET_NAME = "bucket-motor-responsabilidad"

storage_client = storage.Client(project=PROJECT_ID)


def verificar_descarga_completa(blob_name):
    """
    Simula exactamente lo que hará el proceso:
    Descargar el archivo completo desde el bucket.
    """
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)

        t_descarga_ini = time.perf_counter()
        # Intentamos descargar los bytes completos a RAM
        contenido = blob.download_as_bytes()
        t_descarga_fin = time.perf_counter() - t_descarga_ini

        tamano_mb = len(contenido) / (1024 * 1024)
        print(f"📥 [VERIFICACIÓN] Descarga exitosa: {blob_name}")
        print(f"   -> Tamaño: {tamano_mb:.2f} MB")
        print(f"   -> Tiempo de descarga: {t_descarga_fin:.2f}s")
        return True
    except Exception as e:
        print(f"❌ [VERIFICACIÓN] Error descargando {blob_name}: {e}")
        return False


def subir_a_gcs(ruta_local):
    """Sube y verifica descarga inmediata."""
    if not os.path.exists(ruta_local):
        print(f"⚠️ Archivo no encontrado: {ruta_local}")
        return None

    nombre_archivo = os.path.basename(ruta_local)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(nombre_archivo)

    print(f"📤 Subiendo {nombre_archivo}...", end=" ", flush=True)
    blob.upload_from_filename(ruta_local)
    print("✅")

    # REALIZAR LA VERIFICACIÓN DE DESCARGA
    if verificar_descarga_completa(nombre_archivo):
        return f"gs://{BUCKET_NAME}/{nombre_archivo}"
    else:
        return None


async def ejecutar_test():
    url_api = "http://127.0.0.1:8000/process-case"

    archivos = {
        "pdf": "ejemplo/sebastian.ortiz.matiz@segurosbolivar.com - 15400065559/15400065559.pdf",
        "audio1": "ejemplo/sebastian.ortiz.matiz@segurosbolivar.com - 15400065559/Llamada1-10e45b09-4ef7-426d-b05f-d45307b2170f.MP3",
        "audio2": "ejemplo/sebastian.ortiz.matiz@segurosbolivar.com - 15400065559/Llamada1-e9181c80-9ec7-4d8f-aed5-8c3b71b7cf09.MP3"
    }

    print("\n🚀 [PASO 1] Iniciando Subida y Verificación de Descarga...")
    uris = {}
    for key, path in archivos.items():
        uri = subir_a_gcs(path)
        if not uri:
            print(f"🛑 FALLO CRÍTICO: No se pudo verificar la descarga de {key}. El proceso fallará.")
            return
        uris[key] = uri

    # 2. Llamada al API
    payload = {
        "case_id": f"TEST-GCS-{int(time.time())}",
        "urls_visuales": [uris["pdf"]],
        "urls_audios": [uris["audio1"], uris["audio2"]],
        "urls_videos": []
    }

    print(f"\n📡 [PASO 2] Enviando URLs al proceso...")

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            response = await client.post(url_api, json=payload)
            if response.status_code == 200:
                print("✅ API completada.")
                print("Resultado:",
                      response.json().get('resultado', {})['conclusion_general_del_caso']['dinamica_consolidada'][:150],
                      "...")
            else:
                print(f"❌ Error API: {response.text}")
        except Exception as e:
            print(f"❌ Error de conexión: {e}")


if __name__ == "__main__":
    asyncio.run(ejecutar_test())