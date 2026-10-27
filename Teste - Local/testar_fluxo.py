"""Executa os exemplos com uma flag exclusiva e remove os dados do teste."""

import os
import subprocess
import sys
from uuid import uuid4

import requests

from config import API_KEY, EVALUATION_URL, HEADERS, PASTA, mostrar_resposta


if not API_KEY:
    raise SystemExit("Execute python criar_chave.py ou preencha API_KEY no .env antes do teste.")

# Cada execução usa seu próprio nome, sem alterar NOME_FLAG no .env.
nome_flag = f"teste-python-{uuid4().hex[:12]}"
ambiente = {**os.environ, "NOME_FLAG": nome_flag}


def executar(script):
    print(f"\n--- {script} ---", flush=True)
    subprocess.run([sys.executable, str(PASTA / script)], env=ambiente, check=True)


executar("validar_chave.py")
executar("criar_flag.py")
try:
    executar("listar_flags.py")
    executar("consultar_flag.py")
    executar("criar_regra.py")
    try:
        executar("consultar_regra.py")

        print("\n--- Avaliação com flag ativa e regra de 100% ---", flush=True)
        resposta = requests.get(
            f"{EVALUATION_URL}/evaluate",
            headers=HEADERS,
            params={"user_id": "teste-python", "flag_name": nome_flag},
            timeout=10,
        )
        mostrar_resposta(resposta)
        if resposta.json().get("result") is not True:
            raise SystemExit("Falha: a avaliação deveria retornar true.")

        executar("atualizar_regra.py")
        executar("atualizar_flag.py")
    finally:
        executar("excluir_regra.py")
finally:
    executar("excluir_flag.py")

print("\nSucesso: autenticação, flags, regras e avaliação responderam como esperado.")
