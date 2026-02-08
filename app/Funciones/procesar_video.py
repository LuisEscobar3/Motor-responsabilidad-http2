import time
from google.cloud import storage
from vertexai.generative_models import Part
from app.commons.services.miscelaneous import load_prompts_generales

def procesar_video_gemini(uri_gcs, llms_resource):
    try:
        model = llms_resource["gemini_pro"]
        labels = llms_resource["config"]["labels"]
        params = llms_resource["config"]["params_pro"]

        # --- CARGA DEL PROMPT DESDE YAML ---
        prompt_base = load_prompts_generales("extraction_visual")

        client = storage.Client()
        bucket_name = uri_gcs.split("/")[2]
        blob_name = "/".join(uri_gcs.split("/")[3:])

        blob = client.bucket(bucket_name).blob(blob_name)
        video_bytes = blob.download_as_bytes()

        video_part = Part.from_data(data=video_bytes, mime_type="video/mp4")

        respuesta = model.generate_content(
            [prompt_base, video_part],
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": params.get("max_tokens", 8192),
            },
            labels=labels
        )
        return respuesta.text
    except Exception as e:
        return f"Error video: {str(e)}"