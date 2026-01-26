import time
from google.cloud import storage
from langchain_core.messages import HumanMessage


def procesar_video_gemini(uri_gcs, llm):
    try:
        client = storage.Client()
        bucket_name = uri_gcs.split("/")[2]
        blob_name = "/".join(uri_gcs.split("/")[3:])

        # Descarga de bytes
        t_start = time.perf_counter()
        blob = client.bucket(bucket_name).blob(blob_name)
        video_bytes = blob.download_as_bytes()
        print(f"⏱️  [VIDEO] Descarga GCS: {time.perf_counter() - t_start:.2f}s")

        # Petición a IA
        mensaje = HumanMessage(content=[
            {"type": "text",
             "text": "Analiza este video del accidente. Describe la secuencia de eventos, quién impacta a quién y cualquier infracción visible."},
            {
                "type": "media",
                "data": video_bytes,
                "mime_type": "video/mp4"
            }
        ])

        t_ia = time.perf_counter()
        respuesta = llm.invoke([mensaje])
        print(f"⏱️  [VIDEO] IA Procesamiento: {time.perf_counter() - t_ia:.2f}s")

        return respuesta.content
    except Exception as e:
        print(f"❌ Error Video: {str(e)}")
        return f"Error video: {str(e)}"