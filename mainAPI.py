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

# --- IMPORTACIONES DE TUS FUNCIONES ---
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


def eliminar_de_gcs(urls: List[str]):
    """Limpia los archivos temporales del bucket."""
    if not urls: return
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        for url in urls:
            blob_name = url.replace(f"gs://{BUCKET_NAME}/", "")
            bucket.blob(blob_name).delete()
            print(f"🗑️  [LIMPIEZA] Eliminado de GCS: {blob_name}", flush=True)
    except Exception as e:
        print(f"⚠️  [LIMPIEZA] Error: {e}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.environ["APP_ENV"] = "sbx"
    t_start = time.perf_counter()
    print("\n⚡ [STARTUP] Iniciando Motor de Responsabilidad...", flush=True)
    try:
        # Carga paralela inicial
        task_llm = run_in_threadpool(load_llms)
        task_matriz = run_in_threadpool(cargar_matriz_marcus, "app/utils/Descripción Circunstancias.xlsx")
        llms, matriz = await asyncio.gather(task_llm, task_matriz)

        app.state.gemini_flash = llms.get("gemini_flash")
        app.state.gemini_pro = llms.get("gemini_pro")
        app.state.contexto_marcus = matriz

        print(f"✅ [LISTO] Servidor operativo en {time.perf_counter() - t_start:.2f}s\n", flush=True)
    except Exception as e:
        print(f"❌ [CRÍTICO] Error en arranque: {e}", flush=True)
        sys.exit(1)
    yield


app = FastAPI(title="Motor Marcus GCS", lifespan=lifespan)


@app.post("/process-case")
async def process_case(request: CaseRequest):
    t_inicio = time.perf_counter()
    case_id = request.case_id
    print(f"\n--- 📥 NUEVA PETICIÓN: {case_id} ---", flush=True)

    try:
        tareas = []
        nombres = []

        # 1. IDENTIFICACIÓN DE EVIDENCIAS
        if request.urls_visuales:
            print(f"🖼️  Detectadas {len(request.urls_visuales)} imágenes/PDFs", flush=True)
            tareas.append(run_in_threadpool(procesar_evidencia_visual, request.urls_visuales, app.state.gemini_flash))
            nombres.append("IA_VISUAL")

        if request.urls_audios:
            print(f"🎙️  Detectados {len(request.urls_audios)} audios", flush=True)
            for i, url in enumerate(request.urls_audios):
                tareas.append(run_in_threadpool(transcribir_audio_gemini, url, app.state.gemini_flash))
                nombres.append(f"IA_AUDIO_{i}")

        if request.urls_videos:
            print(f"🎥  Detectados {len(request.urls_videos)} videos", flush=True)
            for i, url in enumerate(request.urls_videos):
                tareas.append(run_in_threadpool(procesar_video_gemini, url, app.state.gemini_flash))
                nombres.append(f"IA_VIDEO_{i}")

        if not tareas:
            print("⚠️  Caso sin evidencias. Abortando.", flush=True)
            return {"ok": False, "error": "No se enviaron URLs de evidencia."}

        # 2. PROCESAMIENTO PARALELO
        print(f"🚀 Ejecutando {len(tareas)} procesos de IA simultáneos...", flush=True)
        t_ia_start = time.perf_counter()

        resultados_lista = await asyncio.gather(*tareas)
        res_map = dict(zip(nombres, resultados_lista))

        t_ia_total = time.perf_counter() - t_ia_start
        print(f"⏱️  [PROCESAMIENTO IA] Finalizado en {t_ia_total:.2f}s", flush=True)
        for nombre in nombres:
            status = "✅ OK" if "Error" not in str(res_map[nombre]) else "❌ FALLÓ"
            print(f"   -> {nombre}: {status}", flush=True)

        # 3. RAZONAMIENTO MARCUS
        print("⚖️  Iniciando razonamiento Marcus (Gemini Pro)...", flush=True)
        t_marcus_start = time.perf_counter()

        # Consolidar entradas
        transcripciones = [v for k, v in res_map.items() if "AUDIO" in k]
        videos_data = [v for k, v in res_map.items() if "VIDEO" in k]

        resultado_final = await run_in_threadpool(
            evaluar_circunstancias_marcus,
            llm=app.state.gemini_pro,
            contexto_marcus=app.state.contexto_marcus,
            json_visual=json.dumps({
                "estatica": res_map.get("IA_VISUAL", "N/A"),
                "videos": videos_data
            }),
            json_transcripcion=" | ".join(transcripciones) if transcripciones else "N/A"
        )

        t_marcus_total = time.perf_counter() - t_marcus_start
        print(f"⏱️  [MARCUS] Análisis completado en {t_marcus_total:.2f}s", flush=True)

        # 4. LIMPIEZA DE BUCKET
        urls_a_borrar = request.urls_visuales + request.urls_audios + request.urls_videos
        await run_in_threadpool(eliminar_de_gcs, urls_a_borrar)

        # 5. RESULTADO FINAL
        t_total = time.perf_counter() - t_inicio
        print(f"🏁 [FINAL] Caso {case_id} procesado en {t_total:.2f}s", flush=True)
        print("-------------------------------------------\n", flush=True)

        return {
            "ok": True,
            "case_id": case_id,
            "tiempos": {
                "ia_paralela": f"{t_ia_total:.2f}s",
                "marcus": f"{t_marcus_total:.2f}s",
                "total_proceso": f"{t_total:.2f}s"
            },
            "resultado": resultado_final
        }

    except Exception as e:
        print(f"❌ [ERROR EN CASO {case_id}]: {str(e)}", flush=True)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@app.get("/health")
def health():
    return {"status": "ok"}