import httpx
import asyncio
import os
import time
from google.cloud import storage

# --- CONFIG ---
URL_API = "https://ia-mv-motor-responsabilidad-993828145189.us-east1.run.app/process-case"
PROJECT_ID = "sb-iapatrimoniales-dev"
BUCKET_NAME = "bucket-motor-responsabilidad"


async def ejecutar_test():
    # El payload que espera tu API
    payload = {
        "case_id": f"TEST-GCS-{int(time.time())}",
        "urls_visuales": [f"gs://{BUCKET_NAME}/evidencia.pdf"],
        "urls_audios": [f"gs://{BUCKET_NAME}/audio1.mp3"],
        "urls_videos": []
    }

    print(f"🚀 Enviando petición a: {URL_API}")

    # Timeout de 10 minutos (600s)
    async with httpx.AsyncClient(http2=False, timeout=600.0) as client:
        try:
            t_ini = time.perf_counter()
            response = await client.post(URL_API, json=payload)
            t_total = time.perf_counter() - t_ini

            print(f"⏱️ Tiempo: {t_total:.2f}s")
            print(f"📊 Status: {response.status_code}")

            if response.status_code == 200:
                print("✅ Éxito:", response.json())
            else:
                print(f"❌ Error: {response.text}")

        except Exception as e:
            print(f"❌ Error de conexión: {e}")


if __name__ == "__main__":
    asyncio.run(ejecutar_test())