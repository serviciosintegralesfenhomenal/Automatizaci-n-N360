import os
import re
import requests
import feedparser
from google import genai

# Configuración de Claves desde Variables de Entorno en GitHub Actions
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SANITY_TOKEN = os.environ.get("SANITY_TOKEN")

SANITY_PROJECT_ID = "r5pvd6kj"
SANITY_DATASET = "production"

# Inicializar cliente Gemini SDK oficial
client = genai.Client(api_key=GEMINI_API_KEY)

# RSS de Noticias Principales de Google News México
RSS_URL = "https://news.google.com/rss?hl=es-419&gl=MX&ceid=MX:es-419"

FALLBACK_IMAGE = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80"

def extraer_url_imagen(entry):
    """Extrae la URL de imagen desde las distintas etiquetas del feed RSS o aplica fallback."""
    try:
        # 1. Buscar en media_content
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if 'url' in media and media['url']:
                    return media['url']

        # 2. Buscar en media_thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            for thumb in entry.media_thumbnail:
                if 'url' in thumb and thumb['url']:
                    return thumb['url']

        # 3. Buscar etiquetas <img> dentro del contenido HTML de la descripción
        summary_html = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
        img_match = re.search(r'src=["\'](https?://[^"\']+)["\']', summary_html)
        if img_match:
            return img_match.group(1)

    except Exception as e:
        print(f"Error extrayendo imagen del RSS: {e}")
    
    return FALLBACK_IMAGE

def obtener_ultima_noticia():
    print("Buscando últimas noticias vía RSS...")
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        raise Exception("No se pudieron obtener entradas del Feed RSS.")
    
    # Seleccionar la primera noticia del feed
    entry = feed.entries[0]
    titulo = entry.title
    link = entry.link
    resumen = getattr(entry, 'summary', titulo)
    
    imagen_url = extraer_url_imagen(entry)
    print(f"Noticia seleccionada: {titulo}")
    print(f"URL de imagen asignada: {imagen_url}")
    
    return titulo, resumen, link, imagen_url

def redactar_noticia_gemini(titulo, resumen):
    print("Generando redacción periodística profunda con Gemini...")
    
    prompt = f"""
    Actúa como un periodista sénior y editor jefe del portal de noticias "Informe 360". 
    Tu objetivo es redactar un artículo periodístico extenso, riguroso, fluido y profesional a partir de la siguiente información de origen:

    TÍTULO DE ORIGEN: {titulo}
    SÍNTESIS DE ORIGEN: {resumen}

    INSTRUCCIONES OBLIGATORIAS DE ESTRUCTURA Y EXTENSIÓN:
    1. EXTENSIÓN: 
       - Genera un artículo de MÍNIMO 3 a 5 párrafos bien desarrollados para noticias breves.
       - Para noticias de gran impacto político, económico o social, amplía la cobertura hasta 8 o 10 párrafos profundos (mínimo 400 palabras en total).
       - Queda estrictamente PROHIBIDO entregar respuestas de 1 o 2 párrafos cortos.

    2. ANATOMÍA DE LA NOTICIA:
       - Párrafo 1 (Lead / Entrada): Presenta los hechos fundamentales respondiendo qué, quién, cuándo, dónde y por qué de la noticia.
       - Párrafo 2 (Contexto y Antecedentes): Explica el marco histórico, decisiones previas o acontecimientos inmediatos que desencadenaron la situación.
       - Párrafos 3 a 7 (Desarrollo y Análisis): Incluye implicaciones de fondo, declaraciones relevantes, cifras/datos clave y las distintas posturas de los actores o instituciones involucradas.
       - Párrafo Final (Proyección): Evalúa las consecuencias a mediano plazo, el impacto en la ciudadanía o los próximos pasos del acontecimiento.

    3. ESTILO REDACCIONAL:
       - Usa un tono formal, periodístico, imparcial y de redacción fluida.
       - Emplea conectores de párrafo elegantes (En este contexto, Por su parte, Asimismo, No obstante, Con base en ello).
       - Separa cada párrafo únicamente con un doble salto de línea. No utilices viñetas ni encabezados en el cuerpo.

    Entrega ÚNICAMENTE el texto periodístico final sin saludos, notas aclaratorias ni prefijos como "Aquí está la nota:".
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    texto_redactado = response.text.strip()
    print(f"Longitud de la nota generada: {len(texto_redactado.split())} palabras.")
    return texto_redactado

def guardar_en_sanity(titulo, contenido, imagen_url):
    print("Guardando noticia en Sanity.io...")
    
    url = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2021-06-07/data/mutate/{SANITY_DATASET}"
    
    documento = {
        "_type": "noticia",
        "titulo": titulo,
        "contenido": contenido,
        "categoria": "Última Hora",
        "imagenUrl": imagen_url,
        "fechaPublicacion": requests.utils.default_headers().get('Date')
    }

    mutations = {
        "mutations": [
            {
                "create": documento
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SANITY_TOKEN}"
    }

    res = requests.post(url, json=mutations, headers=headers)
    if res.status_code == 200:
        print("¡Noticia guardada con éxito en Sanity!")
    else:
        print(f"Error al guardar en Sanity: {res.status_code} - {res.text}")

if __name__ == "__main__":
    try:
        tit, res, link, img = obtener_ultima_noticia()
        contenido_amplio = redactar_noticia_gemini(tit, res)
        guardar_en_sanity(tit, contenido_amplio, img)
    except Exception as e:
        print("Error durante la ejecución del script:", e)
