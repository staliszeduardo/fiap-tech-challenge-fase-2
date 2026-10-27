import requests

from config import AUTH_URL, HEADERS_API, mostrar_resposta


resposta = requests.get(f"{AUTH_URL}/validate", headers=HEADERS_API, timeout=10)
mostrar_resposta(resposta)
