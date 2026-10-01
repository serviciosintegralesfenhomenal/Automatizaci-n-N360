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

SANITY_MUTATE_URL = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2021-06-07/data/mutate/{SANITY_DATASET}"
SANITY_QUERY_URL = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2021-06-07/data/query/{SANITY_DATASET}"
FEED_RSS_URL = "https://news.google.com/rss?hl=es-419&gl=MX&ceid=MX:es-419"

def generar_slug(texto):
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    return re.sub(r'[\s-]+', '-', texto).strip('-')

def ya_existe_noticia(titulo):
    """ Consulta en Sanity si ya existe una noticia con ese título idéntico o similar """
    try:
        query = encode_query = requests.utils.quote(f'*[_type == "noticia" && titulo == "{titulo}"]')
        url = f"{SANITY_QUERY_URL}?query={query}"
        res = requests.get(url, timeout=5).json()
        resultados = res.get("result", [])
        return len(resultados) > 0
    except Exception as e:
        print(f"⚠️ Error al verificar duplicados en Sanity: {e}")
        return False

def obtener_imagen_de_url(url_noticia):
    """ Extrae la imagen real de la nota original desenvolviendo el link de Google News """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url_noticia, headers=headers, timeout=8, allow_redirects=True)
        html_content = res.text

        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if match and "google" not in match.group(1).lower():
            return match.group(1)
            
        match_alt = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html_content, re.IGNORECASE)
        if match_alt and "google" not in match_alt.group(1).lower():
            return match_alt.group(1)
            
    except Exception as e:
        print(f"⚠️ No se pudo extraer la imagen fuente: {e}")
    
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80"

def obtener_noticias_rss():
    response = requests.get(FEED_RSS_URL)
    noticias = []
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        items = root.findall('.//channel/item')
        for item in items[:5]: # Revisa los 5 más recientes
            titulo = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            if titulo and link:
                noticias.append((titulo, link))
    return noticias

def procesar_con_gemini(titulo_original):
    if not GEMINI_API_KEY:
        return {
            "titulo": titulo_original,
            "contenido": f"Atención e información de última hora: {titulo_original}. Las autoridades y servicios oficiales se mantienen en alerta ante los recientes acontecimientos en la región.",
            "categoria": "Nacional"
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    Actúa como un editor periodístico senior del medio "Informe 360".
    Toma este titular de noticia en vivo: "{titulo_original}".
    
    Escribe un artículo periodístico completo, formal, objetivo y bien redactado de 3 a 4 párrafos informativos basados en el hecho.
    
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
    response = requests.post(SANITY_MUTATE_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        print(f"✅ Publicada exitosamente: {nota_data['titulo']}")
        return response.json()
    else:
        print(f"❌ Error al guardar en Sanity: {response.status_code}")
        return None

if __name__ == "__main__":
    print("🔍 Revisando noticias recientes en el Feed RSS...")
    noticias_rss = obtener_noticias_rss()
    
    noticia_publicada = False
    for titulo_rss, link_rss in noticias_rss:
        print(f"Checking: {titulo_rss}")
        if ya_existe_noticia(titulo_rss):
            print("⏩ Esta noticia ya fue publicada previamente. Omitiendo duplicado.")
            continue
        
        print(f"📰 Nueva noticia no registrada detectada: {titulo_rss}")
        print("🖼️ Extrayendo fotografía de la fuente original...")
        imagen_url = obtener_imagen_de_url(link_rss)
        
        print("🤖 Procesando y redactando con Gemini...")
        nota_procesada = procesar_con_gemini(titulo_rss)
        
        if nota_procesada:
            if ya_existe_noticia(nota_procesada["titulo"]):
                print("⏩ El título redactado por Gemini ya existe en Sanity. Omitiendo duplicado.")
                continue
                
            guardar_nota_en_sanity(nota_procesada, imagen_url)
            noticia_publicada = True
            break # Publica solo 1 noticia nueva por cada hora/ejecución

    if not noticia_publicada:
        print("ℹ️ No hay noticias completamente nuevas en este momento.")
