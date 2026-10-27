import argparse

import requests

from config import FLAG_URL, HEADERS_API, NOME_FLAG, mostrar_resposta


def main():
    parser = argparse.ArgumentParser(description="Altera a descrição ou o estado da flag selecionada.")
    parser.add_argument("--descricao", help="Nova descrição da flag.")
    estado = parser.add_mutually_exclusive_group()
    estado.add_argument("--ativa", dest="ativa", action="store_true", help="Ativa a flag.")
    estado.add_argument("--inativa", dest="ativa", action="store_false", help="Desativa a flag.")
    parser.set_defaults(ativa=None)
    argumentos = parser.parse_args()

    dados = {}
    if argumentos.descricao is not None:
        dados["description"] = argumentos.descricao
    if argumentos.ativa is not None:
        dados["is_enabled"] = argumentos.ativa
    if not dados:
        dados["is_enabled"] = False

    resposta = requests.put(
        f"{FLAG_URL}/flags/{NOME_FLAG}", headers=HEADERS_API, json=dados, timeout=10
    )
    mostrar_resposta(resposta)


if __name__ == "__main__":
    main()
