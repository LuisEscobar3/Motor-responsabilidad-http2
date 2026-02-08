import json
import logging
from typing import Optional, Any, Tuple
from vertexai.generative_models import GenerativeModel
from app.commons.services.miscelaneous import load_prompts_generales

def _strip_code_fences(text: str) -> str:
    """Elimina bloques de código Markdown de la respuesta."""
    if not isinstance(text, str):
        return text
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text

def _extract_json(text: str) -> Tuple[Optional[Any], Optional[Exception]]:
    """Intenta extraer y parsear JSON de la respuesta del modelo."""
    if text is None:
        return None, ValueError("Respuesta vacía")
    try:
        return json.loads(text), None
    except Exception:
        pass
    stripped = _strip_code_fences(text)
    try:
        return json.loads(stripped), None
    except Exception:
        pass
    try:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(stripped[start:end + 1]), None
    except Exception as e:
        return None, e
    return None, ValueError("No se pudo parsear el JSON")

def evaluar_circunstancias_marcus(
        llms_resource: dict,
        contexto_marcus: str,
        json_visual: str,
        json_transcripcion: str
) -> Any:
    """
    Aplica la matriz Marcus usando Gemini 1.5 Pro nativo y el prompt del YAML.
    """
    try:
        # 1. Recuperar recursos del cliente nativo
        model = llms_resource["gemini_pro"]
        labels = llms_resource["config"]["labels"]
        params = llms_resource["config"]["params_pro"]

        # 2. Cargar el prompt experto desde el YAML
        prompt_base = load_prompts_generales("evaluar_circunstancias_marcus")
        if not prompt_base:
            return {"error": "❌ Prompt 'evaluar_circunstancias_marcus' no encontrado en el YAML."}

        # 3. Construir el prompt final inyectando los datos del caso
        # El prompt_base del YAML ya contiene la estructura JSON de salida
        user_prompt = f"""
        {prompt_base}

        ### DATOS PARA EL ANÁLISIS ###
        - CONTEXTO MARCUS: {contexto_marcus}
        - JSON ANÁLISIS VISUAL: {json_visual}
        - JSON TRANSCRIPCIONES: {json_transcripcion}
        """

        # 4. Invocación al modelo Gemini Pro
        logging.info("📨 Enviando análisis lógico Marcus a Gemini Pro (Nativo)...")
        respuesta = model.generate_content(
            user_prompt,
            generation_config={
                "temperature": 0.0,  # Precisión máxima para adjudicación
                "max_output_tokens": params.get("max_tokens", 8192),
                "response_mime_type": "application/json" # Obliga al modelo a responder en JSON
            },
            labels=labels # Trazabilidad de costos para Movilidad
        )

        # 5. Procesamiento de salida
        raw_text = respuesta.text
        parsed, err = _extract_json(raw_text)

        if parsed is None:
            logging.error(f"❌ Falló la generación de JSON en Marcus: {err}")
            return {"error": f"JSON inválido: {str(err)}", "raw": raw_text}

        return parsed

    except Exception as e:
        logging.error(f"❌ Error crítico en evaluar_circunstancias_marcus: {e}")
        return {"error": str(e)}