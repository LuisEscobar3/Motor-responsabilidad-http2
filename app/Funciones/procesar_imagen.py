import time
from google.cloud import storage
from vertexai.generative_models import Part
from app.commons.services.miscelaneous import load_prompts_generales


def procesar_evidencia_visual(urls_gcs, llms_resource):
    try:
        model = llms_resource["gemini_pro"]
        labels = llms_resource["config"]["labels"]
        params = llms_resource["config"]["params_pro"]

        # --- CARGA DEL PROMPT DESDE YAML ---
        prompt_base = load_prompts_generales("extraction_visual")

        # Iniciamos la lista de contenido con el prompt del YAML
        contenido_mensaje = [prompt_base]

        client = storage.Client()
        for url in urls_gcs:
            bucket_name = url.split("/")[2]
            blob_name = "/".join(url.split("/")[3:])
            blob = client.bucket(bucket_name).blob(blob_name)
            data_bytes = blob.download_as_bytes()

            mime = "application/pdf" if url.lower().endswith(".pdf") else "image/jpeg"
            contenido_mensaje.append(Part.from_data(data=data_bytes, mime_type=mime))

        respuesta = model.generate_content(
            contenido_mensaje,
            generation_config={
                "temperature": params.get("temperature", 0.0),
                "max_output_tokens": params.get("max_tokens", 8192),
            },
            labels=labels
        )
        return respuesta.text
    except Exception as e:
        return f"Error visual: {str(e)}"