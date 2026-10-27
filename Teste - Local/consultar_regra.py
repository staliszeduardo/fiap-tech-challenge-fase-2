import requests

from config import HEADERS_API, NOME_FLAG, TARGETING_URL, mostrar_resposta


resposta = requests.get(
    f"{TARGETING_URL}/rules/{NOME_FLAG}", headers=HEADERS_API, timeout=10
)
mostrar_resposta(resposta)
