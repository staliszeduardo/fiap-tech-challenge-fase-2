import argparse

import requests

from config import FLAG_URL, HEADERS_API, NOME_FLAG, mostrar_resposta


def validar_nome(valor):
    nome = valor.strip()
    if not nome:
        raise argparse.ArgumentTypeError("O nome da flag não pode ficar vazio.")
    if len(nome) > 100:
        raise argparse.ArgumentTypeError("O nome da flag deve ter até 100 caracteres.")
    if nome in {".", ".."}:
        raise argparse.ArgumentTypeError("O nome da flag não pode ser apenas '.' ou '..'.")
    if any(caractere in nome for caractere in "/?#%"):
        raise argparse.ArgumentTypeError("O nome da flag não pode conter /, ?, # ou %.")
    return nome


def main():
    parser = argparse.ArgumentParser(description="Cria uma flag com nome, descrição e estado personalizados.")
    parser.add_argument(
        "--nome", type=validar_nome, default=NOME_FLAG,
        help="Nome único da flag (padrão: NOME_FLAG da configuração).",
    )
    parser.add_argument(
        "--descricao", default="Teste da Fase 2 em Python",
        help="Descrição da flag (padrão: Teste da Fase 2 em Python).",
    )
    estado = parser.add_mutually_exclusive_group()
    estado.add_argument("--ativa", dest="ativa", action="store_true", help="Cria a flag ativa (padrão).")
    estado.add_argument("--inativa", dest="ativa", action="store_false", help="Cria a flag inativa.")
    parser.set_defaults(ativa=True)
    argumentos = parser.parse_args()

    dados = {
        "name": argumentos.nome,
        "description": argumentos.descricao,
        "is_enabled": argumentos.ativa,
    }
    resposta = requests.post(f"{FLAG_URL}/flags", headers=HEADERS_API, json=dados, timeout=10)
    mostrar_resposta(resposta)


if __name__ == "__main__":
    main()
