import os
import sys
import asyncio
from app.commons.services.llm_manager import load_llms
from app.commons.services.matrix_loader import cargar_matriz_marcus
from app.Funciones.Procesar_circunstancias import evaluar_circunstancias_marcus


def get_gemini_pro():
    """Marcus requiere la potencia de Gemini Pro."""
    os.environ["APP_ENV"] = os.environ.get("APP_ENV", "sbx")
    llms = load_llms()
    if "gemini_pro" not in llms:
        raise RuntimeError("❌ Error: 'gemini_pro' no encontrado.")
    return llms["gemini_pro"]


async def main():
    args = dict(arg.split('=') for arg in sys.argv[1:] if '=' in arg)
    case_id = args.get('case_id')

    # Cargar modelos y matriz
    gemini_pro = get_gemini_pro()
    contexto_marcus = cargar_matriz_marcus("app/utils/Descripción Circunstancias.xlsx")

    # Recibe los datos ya procesados por las IAs previas desde los argumentos
    datos_visual = args.get('datos_visual', 'N/A')
    datos_transcripcion = args.get('datos_audio', 'N/A')

    print(f"⚖️ Iniciando Razonamiento Marcus para el caso: {case_id}")

    resultado = evaluar_circunstancias_marcus(
        llm=gemini_pro,
        contexto_marcus=contexto_marcus,
        json_visual=datos_visual,
        json_transcripcion=datos_transcripcion
    )

    print(f"RESULTADO_FINAL_MARCUS: {resultado}")


if __name__ == "__main__":
    asyncio.run(main())