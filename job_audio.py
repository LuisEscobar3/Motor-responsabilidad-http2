import sys
import asyncio
from app.Funciones.procesar_audio import transcribir_audio_gemini
from app.commons.services.llm_manager import load_llms


async def main():
    args = {a.split('=')[0]: a.split('=')[1] for a in sys.argv[1:] if '=' in a}
    llms = load_llms()
    g_flash = llms.get("gemini_flash")

    print(f"🎙️ Procesando audio: {args.get('uri')}")
    resultado = transcribir_audio_gemini(args.get('uri'), g_flash)
    print(f"✅ Resultado Audio: {resultado}")


if __name__ == "__main__":
    asyncio.run(main())