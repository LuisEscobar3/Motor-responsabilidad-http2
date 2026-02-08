import time
from google.cloud import storage
from vertexai.generative_models import Part
from app.commons.services.miscelaneous import load_prompts_generales


def transcribir_audio_gemini(uri_gcs, llms_resource):
    try:
        model = llms_resource["gemini_flash"]
        labels = llms_resource["config"]["labels"]
        params = llms_resource["config"]["params_flash"]

        # --- CARGA DEL PROMPT DESDE YAML ---
        prompt_base = load_prompts_generales("transcription_audio")

        client = storage.Client()
        bucket_name = uri_gcs.split("/")[2]
        blob_name = "/".join(uri_gcs.split("/")[3:])

        blob = client.bucket(bucket_name).blob(blob_name)
        audio_bytes = blob.download_as_bytes()

        audio_part = Part.from_data(data=audio_bytes, mime_type="audio/mpeg")

        t_ia = time.perf_counter()
        # Se envía el prompt_base cargado del YAML
        respuesta = model.generate_content(
            [prompt_base, audio_part],
            generation_config={
                "temperature": params.get("temperature", 0.0),
                "max_output_tokens": params.get("max_tokens", 8192),
            },
            labels=labels
        )
        return respuesta.text
    except Exception as e:
        return f"Error en audio: {str(e)}"