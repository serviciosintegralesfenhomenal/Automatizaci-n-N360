import os
import requests

SANITY_PROJECT_ID = "r5pvd6kj"
SANITY_DATASET = "production"
# Toma el nuevo token configurado en tus Secrets de GitHub
SANITY_TOKEN = os.getenv("SANITY_TOKEN", "skT2d9JcWH5rlbANAPQjIeqGWIlzGADDycVxSn8RpRxnDhYKt8B0E4bBugJiKpozjQFRqTOKvCM76ymiENCuzuEHRvuhIPMqsSX4LmVAgTLgC5u7DxQMVaPBrcb0sAG8dq0CZjW1rXldVOg4UAgs2Oy8oXp5bT1WydO4sfp9DONY1jWqgEi5")

def borrar_todas_las_noticias_viejas():
    url = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2021-06-07/data/mutate/{SANITY_DATASET}"
    headers = {
        "Authorization": f"Bearer {SANITY_TOKEN}",
        "Content-Type": "application/json"
    }
    # Instrucción para eliminar todas las noticias antiguas acumuladas
    payload = {
        "mutations": [
            {"delete": {"query": '*[_type == "noticia"]'}}
        ]
    }
    
    print("🧹 Borrando noticias viejas de Sanity...")
    res = requests.post(url, headers=headers, json=payload)
    print("Respuesta de Sanity:", res.text)

if __name__ == "__main__":
    borrar_todas_las_noticias_viejas()
