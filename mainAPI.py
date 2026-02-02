import time
import asyncio
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from google.auth import default
from google.auth.transport.requests import Request

app = FastAPI(title="Motor Marcus Orquestador")

PROJECT_ID = "sb-iapatrimoniales-dev"
REGION = "us-east1"


class CaseRequest(BaseModel):
    case_id: str
    urls_visuales: List[str] = []
    urls_audios: List[str] = []
    urls_videos: List[str] = []


async def run_job_and_wait(job_name: str, args_list: list):
    """Lanza un Job de Cloud Run y espera a que termine."""
    credentials, _ = default()
    credentials.refresh(Request())
    headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}

    url = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{job_name}:run"
    payload = {"overrides": {"containerOverrides": [{"args": args_list}]}}

    r = requests.post(url, json=payload, headers=headers)
    if not r.ok:
        raise RuntimeError(f"Error lanzando {job_name}: {r.text}")

    exec_name = r.json()["metadata"]["name"]
    exec_url = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/executions/{exec_name}"

    while True:
        status = requests.get(exec_url, headers=headers).json()
        conditions = status.get("status", {}).get("conditions", [])
        if any(c["type"] == "Completed" and c["status"] == "True" for c in conditions):
            return "OK"
        if any(c["type"] == "Failed" and c["status"] == "True" for c in conditions):
            raise RuntimeError(f"El Job {job_name} falló.")
        await asyncio.sleep(5)


@app.post("/process-case")
async def process_case(request: CaseRequest):
    t_inicio = time.perf_counter()
    case_id = request.case_id

    try:
        # --- 1. PROCESAMIENTO IA PARALELO ---
        t_ia_start = time.perf_counter()
        tareas = []

        if request.urls_audios:
            for url in request.urls_audios:
                tareas.append(run_job_and_wait("job-audio", ["job_audio.py", f"uri={url}"]))

        if request.urls_videos:
            for url in request.urls_videos:
                tareas.append(run_job_and_wait("job-video", ["job_video.py", f"uri={url}"]))

        if request.urls_visuales:
            tareas.append(run_job_and_wait("job-visual", ["job_visual.py", f"uris={','.join(request.urls_visuales)}"]))

        if not tareas:
            raise HTTPException(status_code=400, detail="No hay evidencias para procesar.")

        await asyncio.gather(*tareas)
        t_ia_total = time.perf_counter() - t_ia_start

        # --- 2. RAZONAMIENTO MARCUS ---
        t_marcus_start = time.perf_counter()
        # Marcus se lanza para consolidar los resultados
        await run_job_and_wait("job-marcus", ["job_marcus.py", f"case_id={case_id}"])
        t_marcus_total = time.perf_counter() - t_marcus_start

        t_total = time.perf_counter() - t_inicio

        # --- 3. RETORNO DE RESPUESTA ---
        return {
            "ok": True,
            "case_id": case_id,
            "tiempos": {
                "ia_paralela": f"{t_ia_total:.2f}s",
                "marcus": f"{t_marcus_total:.2f}s",
                "total_proceso": f"{t_total:.2f}s"
            },
            "resultado": "Análisis completado exitosamente."
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}