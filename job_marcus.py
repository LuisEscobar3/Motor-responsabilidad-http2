import sys
import json
import asyncio
from app.Funciones.Procesar_circunstancias import evaluar_circunstancias_marcus
from app.commons.services.llm_manager import load_llms
from app.commons.services.matrix_loader import cargar_matriz_marcus


async def main():
    # Marcus recibe el payload de datos por línea de comandos
    args = {a.split('=')[0]: a.split('=')[1] for a in sys.argv[1:] if '=' in a}
    datos_ia = json.loads(args.get("datos_ia", "[]"))

    llms = load_llms()
    matriz = cargar_matriz_marcus("app/utils/Descripción Circunstancias.xlsx")

    # Ejecución
    resultado = evaluar_circunstancias_marcus(
        llm=llms.get("gemini_pro"),
        contexto_marcus=matriz,
        json_visual=str(datos_ia),  # Datos ya procesados
        json_transcripcion="Datos consolidados"
    )

    # Imprime el resultado para que la API lo vea en logs
    print(json.dumps(resultado))


if __name__ == "__main__":
    asyncio.run(main())