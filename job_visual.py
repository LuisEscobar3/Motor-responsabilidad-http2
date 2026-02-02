import os
import sys
import asyncio
from app.commons.services.llm_manager import load_llms
from app.Funciones.procesar_imagen import procesar_evidencia_visual


def get_gemini():
    os.environ["APP_ENV"] = os.environ.get("APP_ENV", "sbx")
    llms = load_llms()
    return llms.get("gemini_flash")


async def main():
    args = dict(arg.split('=') for arg in sys.argv[1:] if '=' in arg)
    # Recibe una lista de URIs separadas por coma
    uris = args.get('uris', '').split(',')

    gemini = get_gemini()

    if uris and uris[0]:
        print(f"🖼️ Iniciando Job Visual para: {len(uris)} archivos")
        resultado = procesar_evidencia_visual(uris, gemini)
        print(f"RESULTADO_IA_VISUAL: {resultado}")


if __name__ == "__main__":
    asyncio.run(main())