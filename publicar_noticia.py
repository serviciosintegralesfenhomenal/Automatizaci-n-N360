import requests

SANITY_PROJECT_ID = "r5pvd6kj"
SANITY_DATASET = "production"
SANITY_TOKEN = "skT2d9JcWH5rlbANAPQjIeqGWIlzGADDycVxSn8RpRxnDhYKt8B0E4bBugJiKpozjQFRqTOKvCM76ymiENCuzuEHRvuhIPMqsSX4LmVAgTLgC5u7DxQMVaPBrcb0sAG8dq0CZjW1rXldVOg4UAgs2Oy8oXp5bT1WydO4sfp9DONY1jWqgEi5"

# 1. Obtener los IDs de todas las notas actuales
url_query = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2021-06-07/data/query/{SANITY_DATASET}?query=*[_type=='noticia']._id"
res = requests.get(url_query).json()
ids = res.get("result", [])

if ids:
    # 2. Eliminar todas las publicaciones de prueba
    mutations = [{"delete": {"id": doc_id}} for doc_id in ids]
    url_mutate = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2021-06-07/data/mutate/{SANITY_DATASET}"
    headers = {"Authorization": f"Bearer {SANITY_TOKEN}", "Content-Type": "application/json"}
    
    requests.post(url_mutate, headers=headers, json={"mutations": mutations})
    print(f"✅ Se eliminaron {len(ids)} noticias de prueba exitosamente.")
else:
    print("No hay noticias registradas para borrar.")
