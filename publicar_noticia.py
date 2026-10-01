def procesar_con_gemini(titulo_original):
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY no encontrada. Usando titular real directamente.")
        return {
            "titulo": titulo_original,
            "contenido": f"Información de última hora sobre: {titulo_original}.",
            "categoria": "Nacional",
            "copyRedes": f"📲 Lee más sobre {titulo_original} en Informe 360. #Noticias #Informe360"
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

    # Respaldo con noticia real si falla la llamada
    return {
        "titulo": titulo_original,
        "contenido": f"Síntesis informativa de última hora sobre: {titulo_original}.",
        "categoria": "Última Hora",
        "copyRedes": f"📲 {titulo_original} #Noticias #Informe360"
    }
