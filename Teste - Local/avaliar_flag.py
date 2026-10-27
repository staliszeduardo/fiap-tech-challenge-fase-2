import requests

from config import EVALUATION_URL, HEADERS, NOME_FLAG, USER_ID, mostrar_resposta


parametros = {"user_id": USER_ID, "flag_name": NOME_FLAG}

resposta = requests.get(
    f"{EVALUATION_URL}/evaluate", headers=HEADERS, params=parametros, timeout=10
)
mostrar_resposta(resposta)
