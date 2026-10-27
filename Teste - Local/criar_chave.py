import argparse

import requests
from dotenv import set_key

from config import ARQUIVO_ENV, AUTH_URL, HEADERS, MASTER_KEY, mostrar_resposta


def validar_nome(valor):
    nome = valor.strip()
    if not nome:
        raise argparse.ArgumentTypeError("O nome da chave não pode ficar vazio.")
    if len(nome) > 100:
        raise argparse.ArgumentTypeError("O nome da chave deve ter até 100 caracteres.")
    return nome


def main():
    parser = argparse.ArgumentParser(description="Cria uma chave de API e a salva no .env desta pasta.")
    parser.add_argument(
        "--nome", type=validar_nome, default="teste-python",
        help="Nome da chave de API (padrão: teste-python).",
    )
    argumentos = parser.parse_args()

    if not MASTER_KEY:
        raise SystemExit("Preencha MASTER_KEY no arquivo Teste API/.env.")

    dados = {"name": argumentos.nome}
    headers = {**HEADERS, "Authorization": f"Bearer {MASTER_KEY}"}

    resposta = requests.post(f"{AUTH_URL}/admin/keys", headers=headers, json=dados, timeout=10)
    mostrar_resposta(resposta)

    # Os próximos scripts já poderão usar a chave criada.
    set_key(ARQUIVO_ENV, "API_KEY", resposta.json()["key"])
    print("API_KEY salva no .env desta pasta.")


if __name__ == "__main__":
    main()
