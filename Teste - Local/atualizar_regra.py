import argparse
import math

import requests

from config import HEADERS_API, NOME_FLAG, TARGETING_URL, mostrar_resposta


def validar_porcentagem(valor):
    try:
        porcentagem = float(valor)
    except ValueError:
        raise argparse.ArgumentTypeError("A porcentagem deve ser um número entre 0 e 100.") from None
    if not math.isfinite(porcentagem) or not 0 <= porcentagem <= 100:
        raise argparse.ArgumentTypeError("A porcentagem deve ser um número finito entre 0 e 100.")
    return porcentagem


def main():
    parser = argparse.ArgumentParser(description="Altera a regra percentual da flag selecionada.")
    parser.add_argument(
        "--porcentagem", type=validar_porcentagem, default=50,
        help="Porcentagem de usuários entre 0 e 100 (padrão: 50).",
    )
    estado = parser.add_mutually_exclusive_group()
    estado.add_argument("--ativa", dest="ativa", action="store_true", help="Ativa a regra (padrão).")
    estado.add_argument("--inativa", dest="ativa", action="store_false", help="Desativa a regra.")
    parser.set_defaults(ativa=True)
    argumentos = parser.parse_args()

    dados = {
        "is_enabled": argumentos.ativa,
        "rules": {"type": "PERCENTAGE", "value": argumentos.porcentagem},
    }
    resposta = requests.put(
        f"{TARGETING_URL}/rules/{NOME_FLAG}", headers=HEADERS_API, json=dados, timeout=10
    )
    mostrar_resposta(resposta)


if __name__ == "__main__":
    main()
