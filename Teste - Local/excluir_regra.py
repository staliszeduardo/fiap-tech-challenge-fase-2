import requests

from config import HEADERS_API, NOME_FLAG, TARGETING_URL, mostrar_resposta


resposta = requests.delete(
    f"{TARGETING_URL}/rules/{NOME_FLAG}", headers=HEADERS_API, timeout=10
)
mostrar_resposta(resposta)
