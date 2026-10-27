import requests

from config import FLAG_URL, HEADERS_API, mostrar_resposta


resposta = requests.get(f"{FLAG_URL}/flags", headers=HEADERS_API, timeout=10)
mostrar_resposta(resposta)
