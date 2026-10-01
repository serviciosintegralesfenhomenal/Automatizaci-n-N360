import os
import requests
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# CONFIGURACIÓN DE CREDENCIALES
SANITY_PROJECT_ID = "r5pvd6kj"
SANITY_DATASET = "production"
SANITY_TOKEN = "skCWw2XQF0IsvyrUPsD8JGzTfK1lCtOSzj5x84ZmrCEKLTfeE0vX7JuFMgj7F2FGzVeLEbYQnMLCwC8Bx563LxehFeICKBhWXZ6IL901oPIiOAidkrCbTVXBH0eN9W2foN4iDUTwxF1ijFhiQQUy2VbxWtwtS6od8OpNKfXtkqBq4ZfhUVUW"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SANITY_API_URL = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2021-06-07/data/mutate/{SANITY_DATASET}"
FEED_RSS_URL = "https://news.google.com/rss?hl=es-419&gl=MX&ceid=MX:es-419"

def generar_slug(texto):
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    return re.sub(r'[\s-]+', '-', texto).strip('-')

def obtener_ultima_noticia_rss():
    response = requests.get(FEED_RSS_URL)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        item = root.find('.//channel/item')
        if item is not None:
            titulo = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            return titulo, link
    return None, None

def procesar_con_gemini(titulo_original):
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY no encontrada. Generando respuesta básica.")
        return {
            "titulo": titulo_original,
            "contenido": f"Síntesis informativa sobre: {titulo_original}",
            "categoria": "General",
            "copyRedes": f"📲 {titulo_original} #Noticias #Informe360"
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    Actúa como un editor senior del medio periodístico "Informe 360".
    Toma este titular de noticia reciente: "{titulo_original}".
    
    Genera una respuesta en formato JSON estricto con la siguiente estructura:
    {{
      "titulo": "Un titular llamativo y profesional para la nota",
      "contenido": "Un resumen periodístico de 2 párrafos, neutro, claro e informativo.",
      "categoria": "Una categoría adecuada (ej. Política, Economía, Nacional, Tecnología, Deportes)",
      "copyRedes": "Un copy atractivo para Facebook e Instagram con gancho, emojis y 3 o 4 hashtags."
    }}
    Responde ÚNICAMENTE con el objeto JSON válido, sin bloques de código ni markdown.
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        try:
            res_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            res_clean = re.sub(r'^```json\s*|```$', '', res_text.strip(), flags=re.MULTILINE)
            return json.loads(res_clean)
        except Exception as e:
            print(f"Error procesando JSON de Gemini: {e}")
    return None

def guardar_nota_en_sanity(nota_data):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SANITY_TOKEN}"
    }

    documento_noticia = {
        "_type": "noticia",
        "titulo": nota_data["titulo"],
        "slug": {
            "_type": "slug",
            "current": generar_slug(nota_data["titulo"])
        },
        "contenido": nota_data["contenido"],
        "categoria": nota_data["categoria"],
        "copyRedes": nota_data["copyRedes"],
        "fechaPublicacion": datetime.utcnow().isoformat() + "Z"
    }

    payload = {"mutations": [{"create": documento_noticia}]}
    response = requests.post(SANITY_API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        print("✅ Nota procesada con Gemini y creada exitosamente en Sanity.io")
        return response.json()
    else:
        print(f"❌ Error al guardar en Sanity: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    print("🔍 Buscando última noticia en el Feed RSS...")
    titulo_rss, link_rss = obtener_ultima_noticia_rss()
    
    if titulo_rss:
        print(f"📰 Noticia detectada: {titulo_rss}")
        print("🤖 Procesando y redactando con Gemini...")
        nota_procesada = procesar_con_gemini(titulo_rss)
        
        if nota_procesada:
            guardar_nota_en_sanity(nota_procesada)
    else:
        print("No se encontraron noticias en el feed RSS.")
