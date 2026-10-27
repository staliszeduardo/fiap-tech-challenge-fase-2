"""Configuracao, HTTP e consultas AWS compartilhadas pelos scripts desta pasta."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import boto3
import requests
from boto3.dynamodb.conditions import Attr
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

PASTA = Path(__file__).resolve().parent
ENV_FILE = PASTA / ".env"
load_dotenv(ENV_FILE, override=False)
if os.environ.get("AWS_PROFILE") == "":
    os.environ.pop("AWS_PROFILE")
API_URL = os.getenv("API_URL", "").strip().rstrip("/")
API_HOST = os.getenv("API_HOST", "togglemaster.local").strip()
API_KEY = os.getenv("API_KEY", "").strip()
MASTER_KEY = os.getenv("MASTER_KEY", "").strip()
NOME_FLAG = os.getenv("NOME_FLAG", "update-user").strip()
REGION = os.getenv("AWS_REGION", "us-east-1").strip()
QUEUE_URL = os.getenv("AWS_SQS_URL", "").strip()
TABLE_NAME = os.getenv("AWS_DYNAMODB_TABLE", "ToggleMasterAnalytics").strip()
EXPECTED_ACCOUNT = os.getenv("EXPECTED_AWS_ACCOUNT_ID", "608541039538").strip()
SDK_CONFIG = Config(connect_timeout=5, read_timeout=15, retries={"mode": "standard", "total_max_attempts": 3})


def positivo(texto):
    numero = int(texto)
    if numero <= 0:
        raise argparse.ArgumentTypeError("Informe um inteiro maior que zero.")
    return numero


def agora():
    return datetime.now(timezone.utc).isoformat()


def salvar_resultado(nome, dados):
    pasta = PASTA / "resultados"
    pasta.mkdir(exist_ok=True)
    destino = pasta / nome
    destino.write_text(json.dumps(dados, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return destino


def executar_cli(acao):
    """Fronteira CLI: apresenta falhas e preserva um codigo de saida diferente de zero."""
    try:
        return acao() or 0
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario.")
        return 130
    except (BotoCoreError, ClientError, requests.RequestException, subprocess.SubprocessError, ValueError, RuntimeError, OSError) as erro:
        mensagem = str(erro)
        for segredo in (API_KEY, MASTER_KEY):
            if segredo:
                mensagem = mensagem.replace(segredo, "[oculto]")
        print(f"ERRO: {mensagem}", file=sys.stderr)
        return 1


class Api:
    def __init__(self, chave=API_KEY):
        if urlsplit(API_URL).scheme not in {"http", "https"} or not urlsplit(API_URL).netloc:
            raise ValueError("Configure API_URL no .env de Teste AWS.")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if API_HOST:
            self.session.headers["Host"] = API_HOST
        if chave:
            self.session.headers["Authorization"] = f"Bearer {chave}"
        self.timeout = float(os.getenv("HTTP_TIMEOUT", "10"))
        if self.timeout <= 0:
            raise ValueError("HTTP_TIMEOUT precisa ser maior que zero.")

    def chamar(self, metodo, rota, *, esperado=200, mostrar=True, **opcoes):
        # Nao segue redirects para evitar transmitir chaves para outro destino.
        resposta = self.session.request(metodo, API_URL + rota, timeout=self.timeout, allow_redirects=False, **opcoes)
        if mostrar:
            print(f"{metodo} {resposta.url} | HTTP {resposta.status_code} | {resposta.elapsed.total_seconds()*1000:.0f} ms", flush=True)
        if resposta.status_code != esperado:
            raise RuntimeError(f"{metodo} {rota}: esperado HTTP {esperado}, recebido {resposta.status_code}.")
        return resposta.json() if resposta.content else None

    def close(self):
        self.session.close()


class Aws:
    def __init__(self):
        perfil = os.getenv("AWS_PROFILE", "").strip() or None
        self.session = boto3.Session(profile_name=perfil, region_name=REGION)
        self.identity = self.session.client("sts", config=SDK_CONFIG).get_caller_identity()
        if self.identity["Account"] != EXPECTED_ACCOUNT:
            raise RuntimeError(f"Conta atual {self.identity['Account']}; esperado {EXPECTED_ACCOUNT}. Confira o perfil AWS.")
        partes = urlsplit(QUEUE_URL)
        caminho = partes.path.strip("/").split("/")
        if partes.scheme != "https" or partes.hostname != f"sqs.{REGION}.amazonaws.com" or len(caminho) != 2 or caminho[0] != EXPECTED_ACCOUNT:
            raise ValueError("AWS_SQS_URL precisa apontar para a fila HTTPS da conta e regiao configuradas.")
        self.sqs = self.session.client("sqs", config=SDK_CONFIG)
        # Interface com tipos Python nativos, inclusive nas paginas retornadas.
        self.dynamo = self.session.resource("dynamodb", config=SDK_CONFIG).meta.client

    def fila(self):
        atributos = self.sqs.get_queue_attributes(QueueUrl=QUEUE_URL, AttributeNames=[
            "ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible", "ApproximateNumberOfMessagesDelayed"
        ])["Attributes"]
        return {
            "disponiveis": int(atributos.get("ApproximateNumberOfMessages", 0)),
            "em_processamento": int(atributos.get("ApproximateNumberOfMessagesNotVisible", 0)),
            "atrasadas": int(atributos.get("ApproximateNumberOfMessagesDelayed", 0)),
        }

    def eventos(self, flag=None, paginas=20, limite=20):
        """Scan paginado com limite de trabalho; nunca apresenta amostra como total da tabela."""
        parametros = {"TableName": TABLE_NAME, "ConsistentRead": True, "PaginationConfig": {"PageSize": 200}}
        if flag:
            parametros["FilterExpression"] = Attr("flag_name").eq(flag)
        encontrados = avaliados = quantidade_paginas = 0
        amostra = []
        parcial = False
        for pagina in self.dynamo.get_paginator("scan").paginate(**parametros):
            quantidade_paginas += 1
            encontrados += pagina.get("Count", 0)
            avaliados += pagina.get("ScannedCount", 0)
            amostra.extend(pagina.get("Items", []))
            amostra = sorted(amostra, key=lambda item: item.get("timestamp", ""), reverse=True)[:limite]
            parcial = bool(pagina.get("LastEvaluatedKey"))
            if quantidade_paginas >= paginas:
                break
        return {"encontrados": encontrados, "avaliados": avaliados, "paginas": quantidade_paginas, "parcial": parcial, "itens": amostra}


if __name__ == "__main__":
    print("Use python main.py para abrir o menu.")
