import os
import sys
import asyncio
from app.commons.services.llm_manager import load_llms
from app.Funciones.procesar_audio import transcribir_audio_gemini


def get_gemini():
    """Carga Gemini Flash para procesamiento multimedia."""
    os.environ["APP_ENV"] = os.environ.get("APP_ENV", "sbx")
    llms = load_llms()
    if "gemini_flash" not in llms:
        raise RuntimeError("❌ Error: 'gemini_flash' no encontrado en la configuración.")
    return llms["gemini_flash"]


async def main():
    # Obtener argumentos: uri=gs://...
    args = dict(arg.split('=') for arg in sys.argv[1:] if '=' in arg)
    uri = args.get('uri')

    # Cargar LLM dentro del Job
    gemini = get_gemini()

    if uri:
        print(f"🎙️ Iniciando Job Audio para: {uri}")
        resultado = transcribir_audio_gemini(uri, gemini)
        # Imprimimos el resultado para que sea capturado por los logs
        print(f"RESULTADO_IA_AUDIO: {resultado}")


if __name__ == "__main__":
    asyncio.run(main())