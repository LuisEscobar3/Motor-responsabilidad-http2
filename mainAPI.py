import os
import time
import json
import traceback
import asyncio
from typing import List
from pydantic import BaseModel
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from google.cloud import storage

from app.commons.services.llm_manager import load_llms
from app.commons.services.matrix_loader import cargar_matriz_marcus
from app.Funciones.procesar_audio import transcribir_audio_gemini
from app.Funciones.procesar_imagen import procesar_evidencia_visual
from app.Funciones.procesar_video import procesar_video_gemini
from app.Funciones.Procesar_circunstancias import evaluar_circunstancias_marcus


class GlobalResources:
    LLMS = None
    CONTEXTO_MARCUS = None
    IS_READY = False


resources = GlobalResources()


async def cargar_recursos_proactivamente():
    t_start = time.perf_counter()
    print("\n⚡ [SISTEMA] Iniciando carga proactiva de recursos...", flush=True)
    try:
        resources.LLMS = await run_in_threadpool(load_llms)
        resources.CONTEXTO_MARCUS = await run_in_threadpool(
            cargar_matriz_marcus, "app/utils/Descripción Circunstancias.xlsx"
        )
        resources.IS_READY = True
        print(f"✅ [SISTEMA] Recursos listos en {time.perf_counter() - t_start:.2f}s", flush=True)
    except Exception as e:
        print(f"❌ [SISTEMA_ERROR] Fallo en carga: {e}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loader_task = asyncio.create_task(cargar_recursos_proactivamente())
    yield
    loader_task.cancel()


app = FastAPI(title="Motor Marcus - Centralizado", lifespan=lifespan)


class CaseRequest(BaseModel):
    case_id: str
    urls_visuales: List[str] = []
    urls_audios: List[str] = []
    urls_videos: List[str] = []


@app.post("/process-case")
async def process_case(request: CaseRequest):
    if not resources.IS_READY:
        raise HTTPException(status_code=503, detail="Motor en carga inicial.")

    t_total_inicio = time.perf_counter()
    case_id = request.case_id
    print(f"🚀 [CASO: {case_id}] Inicio de procesamiento multimodal", flush=True)

    try:
        # 1. PROCESAMIENTO MULTIMEDIA (Flash para Audio, Pro para Video/Imagen)
        tareas = []
        nombres = []
        tiempos_detalle = {}

        if request.urls_visuales:
            tareas.append(run_in_threadpool(procesar_evidencia_visual, request.urls_visuales, resources.LLMS))
            nombres.append("IA_VISUAL_PRO")

        if request.urls_audios:
            for i, url in enumerate(request.urls_audios):
                tareas.append(run_in_threadpool(transcribir_audio_gemini, url, resources.LLMS))
                nombres.append(f"IA_AUDIO_FLASH_{i}")

        if request.urls_videos:
            for i, url in enumerate(request.urls_videos):
                tareas.append(run_in_threadpool(procesar_video_gemini, url, resources.LLMS))
                nombres.append(f"IA_VIDEO_PRO_{i}")

        t_ia_parallel_start = time.perf_counter()
        print(f"📡 [CASO: {case_id}] Lanzando tareas multimedia en paralelo...", flush=True)
        resultados_lista = await asyncio.gather(*tareas)
        tiempos_detalle["latencia_multimedia_paralela"] = f"{time.perf_counter() - t_ia_parallel_start:.2f}s"

        res_map = dict(zip(nombres, resultados_lista))

        # 2. RAZONAMIENTO MARCUS (Gemini Pro)
        print(f"🧠 [CASO: {case_id}] Ejecutando análisis lógico Marcus...", flush=True)
        t_marcus_start = time.perf_counter()

        transcripciones = [v for k, v in res_map.items() if "AUDIO" in k]
        videos_data = [v for k, v in res_map.items() if "VIDEO" in k]

        resultado_final = await run_in_threadpool(
            evaluar_circunstancias_marcus,
            llms_resource=resources.LLMS,
            contexto_marcus=resources.CONTEXTO_MARCUS,
            json_visual=json.dumps({"estatica": res_map.get("IA_VISUAL_PRO", "N/A"), "videos": videos_data}),
            json_transcripcion=" | ".join(transcripciones) if transcripciones else "N/A"
        )
        tiempos_detalle["latencia_razonamiento_marcus"] = f"{time.perf_counter() - t_marcus_start:.2f}s"

        tiempos_detalle["latencia_total_api"] = f"{time.perf_counter() - t_total_inicio:.2f}s"
        print(f"🏁 [CASO: {case_id}] Proceso terminado en {tiempos_detalle['latencia_total_api']}", flush=True)

        return {
            "ok": True,
            "case_id": case_id,
            "metricas_tiempos": tiempos_detalle,
            "resultado": resultado_final
        }

    except Exception as e:
        print(f"❌ [CASO_ERROR: {case_id}] Error: {str(e)}", flush=True)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})