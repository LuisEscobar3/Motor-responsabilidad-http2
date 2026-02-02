import sys
import asyncio
from app.Funciones.procesar_imagen import procesar_evidencia_visual
from app.commons.services.llm_manager import load_llms


async def main():
    args = {a.split('=')[0]: a.split('=')[1] for a in sys.argv[1:] if '=' in a}
    llms = load_llms()
    g_flash = llms.get("gemini_flash")

    urls = args.get("uris").split(",")
    print(f"📸 Procesando {len(urls)} imágenes/PDFs")
    resultado = procesar_evidencia_visual(urls, g_flash)
    print(f"✅ Resultado Visual: {resultado}")


if __name__ == "__main__":
    asyncio.run(main())