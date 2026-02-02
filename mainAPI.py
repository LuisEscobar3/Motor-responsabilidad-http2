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
import uuid
import time
import requests
import asyncio
from fastapi import FastAPI, HTTPException
from google.auth import default
from google.auth.transport.requests import Request
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Motor Marcus API")

PROJECT_ID = "sb-iapatrimoniales-dev"
REGION = "us-east1"


class CaseRequest(BaseModel):
    case_id: str
    urls_visuales: List[str] = []
    urls_audios: List[str] = []
    urls_videos: List[str] = []


async def run_job_and_get_result(job_name: str, args_list: list):
    """
    Lanza el Job y espera a que termine.
    Para devolver datos sin GCS, Marcus y las IAs deben escribir su JSON en la última línea de logs.
    """
    credentials, _ = default()
    credentials.refresh(Request())
    token = credentials.token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Ejecutar Job
    url = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{job_name}:run"
    payload = {"overrides": {"containerOverrides": [{"args": args_list}]}}
    r = requests.post(url, json=payload, headers=headers)
    if not r.ok: raise RuntimeError(f"Error lanzando {job_name}: {r.text}")

    exec_name = r.json()["metadata"]["name"]
    exec_url = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/executions/{exec_name}"

    # 2. Polling (Espera activa)
    while True:
        status = requests.get(exec_url, headers=headers).json()
        conditions = status.get("status", {}).get("conditions", [])
        if any(c["type"] == "Completed" and c["status"] == "True" for c in conditions):
            # Aquí deberías recuperar el log final si quieres el dato puro.
            # Por ahora, simulamos el retorno del dato procesado.
            return "Resultado procesado por la IA"
        if any(c["type"] == "Failed" and c["status"] == "True" for c in conditions):
            raise RuntimeError(f"Job {job_name} falló.")
        await asyncio.sleep(2)


@app.post("/process-case")
async def process_case(request: CaseRequest):
    t_inicio = time.perf_counter()
    case_id = request.case_id

    try:
        # --- 1. PROCESAMIENTO IA PARALELO ---
        t_ia_start = time.perf_counter()

        # Ejecutamos los jobs y esperamos sus resultados de texto
        tareas = []
        if request.urls_audios:
            for url in request.urls_audios:
                tareas.append(run_job_and_get_result("job-audio", ["job_audio.py", f"uri={url}"]))
        if request.urls_videos:
            for url in request.urls_videos:
                tareas.append(run_job_and_get_result("job-video", ["job_video.py", f"uri={url}"]))
        if request.urls_visuales:
            tareas.append(
                run_job_and_get_result("job-visual", ["job_visual.py", f"uris={','.join(request.urls_visuales)}"]))

        resultados_ia = await asyncio.gather(*tareas)
        t_ia_total = time.perf_counter() - t_ia_start

        # --- 2. RAZONAMIENTO MARCUS ---
        t_marcus_start = time.perf_counter()

        # Le pasamos a Marcus los resultados de texto obtenidos arriba
        # Marcus recibe DATOS, no URLs.
        resultado_final = await run_job_and_get_result("job-marcus", [
            "job_marcus.py",
            f"datos_ia={json.dumps(resultados_ia)}"
        ])

        t_marcus_total = time.perf_counter() - t_marcus_start
        t_total = time.perf_counter() - t_inicio

        # --- 3. RETORNO EXACTO ---
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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}