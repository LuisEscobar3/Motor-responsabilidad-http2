import time
from google.cloud import storage
from langchain_core.messages import HumanMessage


def procesar_evidencia_visual(urls_gcs, llm):
    try:
        client = storage.Client()
        contenido_mensaje = [{"type": "text",
                              "text": "Analiza las imágenes o PDFs adjuntos. Describe daños, posiciones de vehículos y señales viales."}]

        for url in urls_gcs:
            t_start = time.perf_counter()
            bucket_name = url.split("/")[2]
            blob_name = "/".join(url.split("/")[3:])

            blob = client.bucket(bucket_name).blob(blob_name)
            data_bytes = blob.download_as_bytes()
            print(f"⏱️  [VISUAL] Descarga GCS: {time.perf_counter() - t_start:.2f}s")

            mime = "application/pdf" if url.lower().endswith(".pdf") else "image/jpeg"
            contenido_mensaje.append({
                "type": "media",
                "data": data_bytes,
                "mime_type": mime
            })

        t_ia = time.perf_counter()
        respuesta = llm.invoke([HumanMessage(content=contenido_mensaje)])
        print(f"⏱️  [VISUAL] IA Procesamiento: {time.perf_counter() - t_ia:.2f}s")

        return respuesta.content
    except Exception as e:
        print(f"❌ Error Visual: {str(e)}")
        return f"Error visual: {str(e)}"