import os
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

def obtener_ultima_noticia():
    print("Buscando últimas noticias vía RSS...")
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        raise Exception("No se pudieron obtener entradas del Feed RSS.")
    
    # Tomar la primera noticia
    entry = feed.entries[0]
    titulo = entry.title
    link = entry.link
    resumen = getattr(entry, 'summary', titulo)
    
    # Intentar extraer URL de imagen si existe en media
    imagen_url = FALLBACK_IMAGE
    if hasattr(entry, 'media_content') and entry.media_content:
        imagen_url = entry.media_content[0].get('url', FALLBACK_IMAGE)
    
    return titulo, resumen, link, imagen_url

def redactar_noticia_gemini(titulo, resumen):
    print("Generando redacción periodística profunda con Gemini...")
    
    prompt = f"""
    Actúa como un periodista sénior y editor jefe del portal de noticias "Informe 360". 
    Tu objetivo es redactar una nota periodística completa, objetiva, profesional y de alta calidad técnica a partir de la siguiente información de origen:

    TITULO DE ORIGEN: {titulo}
    DATOS Y RESUMEN DE ORIGEN: {resumen}

    REGLAS OBLIGATORIAS DE REDACCIÓN:
    1. LONGITUD Y PROFUNDIDAD:
       - Para noticias estándar o de desarrollo rápido: Redacta MÍNIMO 3 párrafos sólidos.
       - Para noticias de alto impacto (política, economía nacional, geopolítica, sucesos relevantes): Desarrolla una cobertura profunda de HASTA 8 A 10 PÁRRAFOS.
       - NUNCA generes respuestas breves de un solo párrafo ni resúmenes telegráficos.

    2. ESTRUCTURA PERIODÍSTICA:
       - Párrafo 1: Lead informativo directo (Qué, quién, cuándo, dónde y por qué).
       - Párrafos centrales (2 a 8): Contexto histórico, datos duros, cifras, antecedentes inmediatos y posturas de los involucrados.
       - Párrafo final: Proyección de consecuencias, impacto social/económico y seguimiento del caso.

    3. TONO Y ESTILO:
       - Lenguaje periodístico formal, imparcial, fluido y riguroso.
       - Usa conectores de párrafo elegantes (Por su parte, En este contexto, Cabe destacar, Asimismo, No obstante).
       - Separa claramente cada párrafo con un salto de línea doble.

    Entrega ÚNICAMENTE el texto final de la nota rediseñada, sin notas de autor ni introducciones como "Aquí está la nota:".
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    return response.text.strip()

def guardar_en_sanity(titulo, contenido, imagen_url):
    print("Guardando noticia estructurada en Sanity.io...")
    
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
        print("Error al guardar en Sanity:", res.status_code, res.text)

if __name__ == "__main__":
    try:
        tit, res, link, img = obtener_ultima_noticia()
        contenido_amplio = redactar_noticia_gemini(tit, res)
        guardar_en_sanity(tit, contenido_amplio, img)
    except Exception as e:
        print("Error en la ejecución:", e)
