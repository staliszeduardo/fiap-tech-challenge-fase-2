"""Cria uma chave na API AWS e salva somente no .env desta pasta."""
import argparse
import sys

from dotenv import set_key

from comum import Api, ENV_FILE, MASTER_KEY, executar_cli


def executar():
    if not ENV_FILE.exists():
        raise ValueError("Copie .env.example para .env nesta pasta primeiro.")
    if not MASTER_KEY:
        raise ValueError("Preencha MASTER_KEY no .env de Teste AWS, ou use uma API_KEY existente nos outros scripts.")
    api = Api(MASTER_KEY)
    try:
        dados = api.chamar("POST", "/admin/keys", esperado=201, json={"name": "testes-python-aws"})
        chave = dados.get("key")
        if not chave:
            raise RuntimeError("A API nao retornou a chave esperada.")
        set_key(str(ENV_FILE), "API_KEY", chave)
        print("API_KEY salva no .env de Teste AWS. O valor nao foi exibido.")
    finally:
        api.close()


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    return executar_cli(executar)


if __name__ == "__main__":
    sys.exit(main())
