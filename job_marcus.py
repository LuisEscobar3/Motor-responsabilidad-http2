import sys
import asyncio
import json
from app.Funciones.Procesar_circunstancias import evaluar_circunstancias_marcus
from app.commons.services.llm_manager import load_llms
from app.commons.services.matrix_loader import cargar_matriz_marcus

async def main():
    args = {a.split('=')[0]: a.split('=')[1] for a in sys.argv[1:] if '=' in a}
    llms = load_llms()
    g_pro = llms.get("gemini_pro")
    c_marcus = cargar_matriz_marcus("app/utils/Descripción Circunstancias.xlsx")

    # Marcus procesa los datos que le llegan por argumentos
    resultado = evaluar_circunstancias_marcus(
        llm=g_pro,
        contexto_marcus=c_marcus,
        json_visual=args.get("urls_visuales", "N/A"),
        json_transcripcion=args.get("urls_audios", "N/A")
    )
    print(f"⚖️ Resultado Marcus: {json.dumps(resultado)}")

if __name__ == "__main__":
    asyncio.run(main())