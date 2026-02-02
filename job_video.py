import os
import sys
import asyncio
from app.commons.services.llm_manager import load_llms
from app.Funciones.procesar_video import procesar_video_gemini


def get_gemini():
    os.environ["APP_ENV"] = os.environ.get("APP_ENV", "sbx")
    llms = load_llms()
    return llms.get("gemini_flash")


async def main():
    args = dict(arg.split('=') for arg in sys.argv[1:] if '=' in arg)
    uri = args.get('uri')

    gemini = get_gemini()

    if uri:
        print(f"🎥 Iniciando Job Video para: {uri}")
        resultado = procesar_video_gemini(uri, gemini)
        print(f"RESULTADO_IA_VIDEO: {resultado}")


if __name__ == "__main__":
    asyncio.run(main())