import os
import json
import uuid
import dotenv
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool

# --- TU PROYECTO ---
from app.commons.services.llm_manager import load_llms
from app.commons.services.matrix_loader import cargar_matriz_marcus

from app.Funciones.procesar_audio import transcribir_audio_gemini
from app.Funciones.procesar_imagen import procesar_evidencia_visual  # Función actualizada para bytes
from app.Funciones.procesar_video import procesar_video_gemini  # Nuevo módulo
from app.Funciones.Procesar_circunstancias import evaluar_circunstancias_marcus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# LIFESPAN: Carga única de modelos y matriz
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    dotenv.load_dotenv()
    os.environ["APP_ENV"] = os.environ.get("APP_ENV", "sbx")

    # 1) Carga independiente de LLMs (Flash y Pro)
    try:
        app.state.llms = load_llms()
        if not app.state.llms.get("gemini_flash") or not app.state.llms.get("gemini_pro"):
            raise RuntimeError("Faltan modelos Gemini en la configuración")

        # 2) Carga de Matriz Marcus
        marcus_path = os.environ.get("MARCUS_XLSX_PATH", "app/utils/Descripción Circunstancias.xlsx")
        app.state.contexto_marcus = cargar_matriz_marcus(marcus_path)
        logger.info("✅ Modelos y Matriz Marcus cargados exitosamente.")
    except Exception as e:
        logger.error(f"❌ Error crítico en inicio: {e}")
        raise e

    yield


app = FastAPI(title="Motor Responsabilidad API v2", lifespan=lifespan)


# ============================================================
# UTILIDADES ASÍNCRONAS
# ============================================================
async def safe_run_task(func, *args):
    """Ejecuta una función en un hilo separado y captura errores sin detener el pipeline."""
    try:
        if args[0] is None: return None  # Si no hay datos (bytes), no ejecutar
        return await run_in_threadpool(func, *args)
    except Exception as e:
        logger.error(f"⚠️ Error en {func.__name__}: {e}")
        return {"error": str(e)}


# ============================================================
# ENDPOINT PRINCIPAL (Optimizado con HTTP/2 y Paralelismo)
# ============================================================
@app.post("/process-case")
async def process_case(
        archivos_visuales: List[UploadFile] = File(None),  # PDF o múltiples imágenes
        audio: Optional[UploadFile] = File(None),
        video: Optional[UploadFile] = File(None),
        case_id: Optional[str] = Form(None),
):
    case_id = case_id or uuid.uuid4().hex
    llms = app.state.llms

    # 1. Lectura de bytes (Sin escritura en disco para máxima velocidad)
    visual_payload = []
    if archivos_visuales:
        for f in archivos_visuales:
            visual_payload.append({"bytes": await f.read(), "mime": f.content_type})

    aud_bytes = await audio.read() if audio else None
    vid_bytes = await video.read() if video else None

    # 2. Ejecución en Paralelo (Independencia de IAs)
    # Usamos Gemini Flash para las tareas de extracción por su baja latencia
    logger.info(f"🚀 Procesando caso {case_id} en paralelo...")

    tareas = [
        safe_run_task(procesar_evidencia_visual, visual_payload, llms["gemini_flash"]),
        safe_run_task(transcribir_audio_gemini, aud_bytes, llms["gemini_flash"]),
        safe_run_task(procesar_video_gemini, vid_bytes, llms["gemini_flash"])
    ]

    # asyncio.gather espera a que todas terminen simultáneamente
    resultados = await asyncio.gather(*tareas)

    res_visual = resultados[0]
    res_audio = resultados[1]
    res_video = resultados[2]

    # 3. Evaluación Final de Marcus (Carga de Razonamiento Independiente)
    # Se utiliza Gemini Pro para la decisión final basada en la Matriz
    try:
        # Consolidamos las fuentes visuales (Imágenes/PDF + Video)
        contexto_visual_total = {
            "evidencia_estatica": res_visual,
            "evidencia_dinamica_video": res_video
        }

        logger.info("⚖️ Iniciando adjudicación Marcus...")
        resultado_final = await run_in_threadpool(
            evaluar_circunstancias_marcus,
            llm=llms["gemini_pro"],
            contexto_marcus=app.state.contexto_marcus,
            json_visual=json.dumps(contexto_visual_total),
            json_transcripcion=str(res_audio)
        )

        return {
            "ok": True,
            "case_id": case_id,
            "status": "success",
            "resultado": resultado_final
        }

    except Exception as e:
        logger.error(f"❌ Error en evaluación de Marcus: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "case_id": case_id, "error": "Fallo en razonamiento final", "detalle": str(e)}
        )


@app.get("/health")
def health():
    return {"status": "ok", "http2_ready": True}