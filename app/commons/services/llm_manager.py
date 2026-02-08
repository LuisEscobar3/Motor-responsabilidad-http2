import vertexai
import time
from vertexai.generative_models import GenerativeModel
from app.commons.services.miscelaneous import load_llm_parameters


def load_llms():
    """
    Inicializa el SDK de Vertex AI y carga los modelos en memoria.
    Se usa print para mayor velocidad de log en GCP.
    """
    t_init = time.perf_counter()
    PROJECT_ID = "sb-iapatrimoniales-dev"
    LOCATION = "us-central1"

    try:
        # Inicialización proactiva de la conexión
        vertexai.init(project=PROJECT_ID, location=LOCATION)

        # Etiquetas de facturación para Seguros Bolívar
        billing_labels = {
            'billing-tag': 'ia-mv-motor-responsabilidadv1',
            'team': 'movilidad',
            'vp': 'patrimoniales',
            'tipo': 'proyecto'
        }

        # Carga de parámetros técnicos
        params_pro = load_llm_parameters("gemini-2.5-pro").get("model_parameters", {})
        params_flash = load_llm_parameters("gemini-2.5-flash").get("model_parameters", {})

        print(f"🚀 [LLM_INIT] Vertex SDK Nativo inicializado en {time.perf_counter() - t_init:.2f}s", flush=True)

        return {
            "gemini_pro": GenerativeModel("gemini-2.5-pro"),
            "gemini_flash": GenerativeModel("gemini-2.5-flash"),
            "config": {
                "labels": billing_labels,
                "params_pro": params_pro,
                "params_flash": params_flash
            }
        }
    except Exception as e:
        print(f"❌ [LLM_ERROR] Error en inicialización: {str(e)}", flush=True)
        raise e