import os
import time
import json
import uuid
import asyncio
import sys
import traceback
from contextlib import asynccontextmanager
from typing import List, Optional
from pydantic import BaseModel

from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from google.cloud import storage

# --- IMPORTACIONES ---
from app.commons.services.llm_manager import load_llms
from app.commons.services.matrix_loader import cargar_matriz_marcus
from app.Funciones.procesar_audio import transcribir_audio_gemini
from app.Funciones.procesar_imagen import procesar_evidencia_visual
from app.Funciones.procesar_video import procesar_video_gemini
from app.Funciones.Procesar_circunstancias import evaluar_circunstancias_marcus

# --- CONFIGURACIÓN ---
PROJECT_ID = "sb-iapatrimoniales-dev"
BUCKET_NAME = "bucket-motor-responsabilidad"


class CaseRequest(BaseModel):
    case_id: str
    urls_visuales: List[str] = []
    urls_audios: List[str] = []
    urls_videos: List[str] = []


# --- PERSISTENCIA EN MEMORIA ---
# Declaramos las variables a nivel de módulo para que persistan
# mientras el proceso de Python no muera.
MODELOS_IA = {
    "gemini_flash": None,
    "gemini_pro": None,
    "contexto_marcus": None
}


def eliminar_de_gcs(urls: List[str]):
    if not urls: return
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        for url in urls:
            blob_name = url.replace(f"gs://{BUCKET_NAME}/", "")
            bucket.blob(blob_name).delete()
            print(f"🗑️ [LIMPIEZA] Eliminado: {blob_name}", flush=True)
    except Exception as e:
        print(f"⚠️ [LIMPIEZA] Error: {e}", flush=True)


async def inicializar_recursos():
    """Carga los modelos solo si no están ya en memoria."""
    if MODELOS_IA["gemini_flash"] is None:
        print("🔄 [MEMORIA] Cargando modelos por primera vez...", flush=True)
        t_start = time.perf_counter()

        task_llm = run_in_threadpool(load_llms)
        task_matriz = run_in_threadpool(cargar_matriz_marcus, "app/utils/Descripción Circunstancias.xlsx")

        llms, matriz = await asyncio.gather(task_llm, task_matriz)

        MODELOS_IA["gemini_flash"] = llms.get("gemini_flash")
        MODELOS_IA["gemini_pro"] = llms.get("gemini_pro")
        MODELOS_IA["contexto_marcus"] = matriz

        print(f"✅ [LISTO] Modelos en RAM ({time.perf_counter() - t_start:.2f}s)", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.environ["APP_ENV"] = "sbx"
    # Intentamos carga inicial, pero si falla el contenedor sube igual
    # y lo reintenta en la primera petición (evita fallo de Health Check).
    try:
        await inicializar_recursos()
    except Exception as e:
        print(f"⚠️ [STARTUP] Advertencia: Los modelos cargarán en la primera petición: {e}")
    yield


app = FastAPI(title="Motor Marcus GCS", lifespan=lifespan)


@app.post("/process-case")
async def process_case(request: CaseRequest):
    t_inicio = time.perf_counter()

    # ASEGURAR QUE NO VOLVIÓ A DEFAULT
    # Si la instancia sigue viva, esto es instantáneo.
    # Si es nueva, carga los modelos sin tumbar el servicio.
    await inicializar_recursos()

    case_id = request.case_id
    print(f"\n--- 📥 PETICIÓN: {case_id} ---", flush=True)

    try:
        tareas = []
        nombres = []

        # Usamos MODELOS_IA en lugar de app.state para mayor persistencia
        g_flash = MODELOS_IA["gemini_flash"]
        g_pro = MODELOS_IA["gemini_pro"]
        c_marcus = MODELOS_IA["contexto_marcus"]

        if request.urls_visuales:
            tareas.append(run_in_threadpool(procesar_evidencia_visual, request.urls_visuales, g_flash))
            nombres.append("IA_VISUAL")

        if request.urls_audios:
            for i, url in enumerate(request.urls_audios):
                tareas.append(run_in_threadpool(transcribir_audio_gemini, url, g_flash))
                nombres.append(f"IA_AUDIO_{i}")

        if request.urls_videos:
            for i, url in enumerate(request.urls_videos):
                tareas.append(run_in_threadpool(procesar_video_gemini, url, g_flash))
                nombres.append(f"IA_VIDEO_{i}")

        if not tareas:
            return {"ok": False, "error": "Sin evidencias."}

        resultados_lista = await asyncio.gather(*tareas)
        res_map = dict(zip(nombres, resultados_lista))

        # RAZONAMIENTO
        transcripciones = [v for k, v in res_map.items() if "AUDIO" in k]
        videos_data = [v for k, v in res_map.items() if "VIDEO" in k]

        resultado_final = await run_in_threadpool(
            evaluar_circunstancias_marcus,
            llm=g_pro,
            contexto_marcus=c_marcus,
            json_visual=json.dumps({"estatica": res_map.get("IA_VISUAL", "N/A"), "videos": videos_data}),
            json_transcripcion=" | ".join(transcripciones) if transcripciones else "N/A"
        )

        # LIMPIEZA Y CIERRE
        urls_a_borrar = request.urls_visuales + request.urls_audios + request.urls_videos
        await run_in_threadpool(eliminar_de_gcs, urls_a_borrar)

        return {
            "ok": True,
            "case_id": case_id,
            "resultado": resultado_final
        }

    except Exception as e:
        print(f"❌ [ERROR]: {str(e)}", flush=True)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@app.get("/health")
def health():
    # El health check ahora es súper ligero para que Cloud Run no lo tumbe
    return {"status": "ok", "models_loaded": MODELOS_IA["gemini_flash"] is not None}