import requests

from config import FLAG_URL, HEADERS_API, NOME_FLAG, mostrar_resposta


resposta = requests.delete(f"{FLAG_URL}/flags/{NOME_FLAG}", headers=HEADERS_API, timeout=10)
mostrar_resposta(resposta)
