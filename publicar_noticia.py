import os
import requests
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# CONFIGURACIÓN DE CREDENCIALES
SANITY_PROJECT_ID = "r5pvd6kj"
SANITY_DATASET = "production"
SANITY_TOKEN = "skT2d9JcWH5rlbANAPQjIeqGWIlzGADDycVxSn8RpRxnDhYKt8B0E4bBugJiKpozjQFRqTOKvCM76ymiENCuzuEHRvuhIPMqsSX4LmVAgTLgC5u7DxQMVaPBrcb0sAG8dq0CZjW1rXldVOg4UAgs2Oy8oXp5bT1WydO4sfp9DONY1jWqgEi5"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SANITY_API_URL = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2021-06-07/data/mutate/{SANITY_DATASET}"
FEED_RSS_URL = "https://news.google.com/rss?hl=es-419&gl=MX&ceid=MX:es-419"

def generar_slug(texto):
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    return re.sub(r'[\s-]+', '-', texto).strip('-')

def obtener_imagen_de_url(url_noticia):
    """ Desenvuelve la redirección de Google News y extrae la fotografía real og:image del medio """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        # Resolver redirección de Google News
        res = requests.get(url_noticia, headers=headers, timeout=8, allow_redirects=True)
        url_real = res.url
        html_content = res.text

        # Si aterrizó en la web original, buscar la meta og:image
        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if match and "google" not in match.group(1).lower():
            return match.group(1)
            
        match_alt = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html_content, re.IGNORECASE)
        if match_alt and "google" not in match_alt.group(1).lower():
            return match_alt.group(1)
            
    except Exception as e:
        print(f"⚠️️ No se pudo extraer imagen real de la fuente: {e}")
    
    # Fotografía temática de prensa en alta resolución si el sitio bloquea el rastreo
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80"

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
        print("⚠️ GEMINI_API_KEY no encontrada en entorno. Procesando texto directo.")
        return {
            "titulo": titulo_original,
            "contenido": f"Atención e información de última hora: {titulo_original}. Las autoridades y servicios oficiales se mantienen en alerta ante los recientes acontecimientos en la región. Se recomienda a la población mantenerse informada a través de los canales institucionales.",
            "categoria": "Nacional"
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    Actúa como un editor periodístico senior del medio "Informe 360".
    Toma este titular de noticia en vivo: "{titulo_original}".
    
    Escribe un artículo periodístico completo, formal, objetivo y bien redactado de 3 a 4 párrafos informativos basados en el hecho. No agregues copies ni texto para redes sociales.
    
    Genera la respuesta estrictamente en JSON con la siguiente estructura:
    {{
      "titulo": "Un titular periodístico claro, profesional e impactante",
      "contenido": "Primer párrafo: Introducción periodística del hecho.\\n\\nSegundo párrafo: Contexto y detalles de las autoridades o partes involucradas.\\n\\nTercer párrafo: Conclusión y perspectivas del acontecimiento.",
      "categoria": "Una categoría profesional (ej. Clima, Política, Nacional, Economía, Tecnología)"
    }}
    Responde ÚNICAMENTE con el JSON válido, sin delimitadores de código ni markdown.
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            res_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            res_clean = re.sub(r'^```json\s*|```$', '', res_text.strip(), flags=re.MULTILINE)
            return json.loads(res_clean)
        else:
            print(f"⚠️ Error API Gemini ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"⚠️ Excepción al llamar a Gemini: {e}")

    return {
        "titulo": titulo_original,
        "contenido": f"Atención e información de última hora sobre {titulo_original}. Reportes oficiales en desarrollo indican seguimiento por parte de las autoridades competentes.",
        "categoria": "Última Hora"
    }

def guardar_nota_en_sanity(nota_data, url_imagen):
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
        "imagenUrl": url_imagen,
        "fechaPublicacion": datetime.utcnow().isoformat() + "Z"
    }

    payload = {"mutations": [{"create": documento_noticia}]}
    response = requests.post(SANITY_API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        print("✅ Nota formal redactada y publicada exitosamente en Sanity.io")
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
        print("🖼️ Extrayendo fotografía real del medio de origen...")
        imagen_url = obtener_imagen_de_url(link_rss)
        print(f"📸 URL Imagen Obtenida: {imagen_url}")
        
        print("🤖 Procesando y redactando con Gemini...")
        nota_procesada = procesar_con_gemini(titulo_rss)
        
        if nota_procesada:
            guardar_nota_en_sanity(nota_procesada, imagen_url)
    else:
        print("No se encontraron noticias en el feed RSS.")
