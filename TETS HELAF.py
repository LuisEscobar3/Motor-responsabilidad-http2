import requests
import json

# Configura la URL de tu servicio en GCP o Local
# Local: "http://127.0.0.1:8000/health"
# GCP: "https://tu-servicio-cloud-run.a.run.app/health"
URL = "http://127.0.0.1:8000/health"


def check_health():
    print(f"🔍 Verificando estado del motor en: {URL}...")

    try:
        response = requests.get(URL, timeout=10)

        # Si el status code es 200, el servidor está arriba
        if response.status_code == 200:
            data = response.json()
            print("\n✅ SERVIDOR ACTIVO")
            print(f"   - Status: {data.get('status')}")
            print(f"   - Modelos Gemini listos: {'🟢 SÍ' if data.get('ia_ready') else '🔴 NO'}")
            print(f"   - Matriz Excel cargada: {'🟢 SÍ' if data.get('matriz_loaded') else '🔴 NO'}")

            if not data.get('ia_ready') or not data.get('matriz_loaded'):
                print("\n⚠️  ADVERTENCIA: El servidor responde pero los modelos no han terminado de cargar.")
        else:
            print(f"\n❌ ERROR: El servidor respondió con status {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR DE CONEXIÓN: ¿Está el servidor encendido?")
    except Exception as e:
        print(f"\n❌ OCURRIÓ UN ERROR INESPERADO: {e}")


if __name__ == "__main__":
    check_health()