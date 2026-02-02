import uuid
import requests
from fastapi import FastAPI, HTTPException
from google.auth import default
from google.auth.transport.requests import Request
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Motor Marcus API", version="1.0.0")

# CONFIGURACIÓN
PROJECT_ID = "sb-iapatrimoniales-dev"
REGION = "us-east1"


class CaseRequest(BaseModel):
    case_id: str
    urls_visuales: List[str] = []
    urls_audios: List[str] = []
    urls_videos: List[str] = []


def run_gcp_job(job_name: str, args_list: list):
    """Lanzador genérico que envía los argumentos directamente al contenedor del Job."""
    credentials, _ = default()
    credentials.refresh(Request())

    url = f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT_ID}/jobs/{job_name}:run"

    payload = {
        "overrides": {
            "containerOverrides": [{
                "args": args_list
            }]
        }
    }

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }
    r = requests.post(url, json=payload, headers=headers)
    if not r.ok:
        raise RuntimeError(f"Error al lanzar {job_name}: {r.text}")
    return r.json()


@app.get("/health")
def health():
    """Endpoint de verificación solicitado."""
    return {"status": "ok", "region": REGION}


@app.post("/process-case")
async def process_case(request: CaseRequest):
    case_id = request.case_id
    print(f"🆔 Procesando caso: {case_id}")

    try:
        # 1. Lanzar Job de Audio
        if request.urls_audios:
            for url in request.urls_audios:
                run_gcp_job("job-audio", ["job_audio.py", f"uri={url}", f"case_id={case_id}"])

        # 2. Lanzar Job de Video
        if request.urls_videos:
            for url in request.urls_videos:
                run_gcp_job("job-video", ["job_video.py", f"uri={url}", f"case_id={case_id}"])

        # 3. Lanzar Job Visual (Imágenes/PDF)
        if request.urls_visuales:
            run_gcp_job("job-visual",
                        ["job_visual.py", f"uris={','.join(request.urls_visuales)}", f"case_id={case_id}"])

        # 4. Lanzar Job de Marcus (Análisis final)
        # Se envían los mismos datos de la petición para que Marcus los procese
        run_gcp_job("job-marcus", [
            "job_marcus.py",
            f"case_id={case_id}",
            f"urls_visuales={','.join(request.urls_visuales)}",
            f"urls_audios={','.join(request.urls_audios)}",
            f"urls_videos={','.join(request.urls_videos)}"
        ])

        return {"ok": True, "message": "Procesamientos de IA iniciados en us-east1", "case_id": case_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))