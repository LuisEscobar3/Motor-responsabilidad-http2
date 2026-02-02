import sys
import asyncio
from app.Funciones.procesar_video import procesar_video_gemini
from app.commons.services.llm_manager import load_llms


async def main():
    # Extraer argumentos: job_video.py uri=gs://... case_id=...
    args = {a.split('=')[0]: a.split('=')[1] for a in sys.argv[1:] if '=' in a}
    llms = load_llms()
    g_flash = llms.get("gemini_flash")

    print(f"🎬 Iniciando análisis de video para: {args.get('uri')}")
    resultado = procesar_video_gemini(args.get('uri'), g_flash)
    print(f"✅ Resultado Video: {resultado}")


if __name__ == "__main__":
    asyncio.run(main())