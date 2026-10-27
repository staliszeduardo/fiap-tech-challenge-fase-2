"""URLs e chaves compartilhadas pelos exemplos de teste."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from http_info import mostrar_solicitacao


PASTA = Path(__file__).resolve().parent
ARQUIVO_ENV = PASTA / ".env"
load_dotenv(ARQUIVO_ENV)

# API_URL preenchida: todos os serviços passam pelo mesmo Ingress.
# API_URL vazia: cada serviço usa sua própria URL (Compose ou portas remotas).
API_URL = os.getenv("API_URL", "").strip().rstrip("/")
AUTH_URL = API_URL or os.getenv("AUTH_URL", "http://localhost:8001").rstrip("/")
FLAG_URL = API_URL or os.getenv("FLAG_URL", "http://localhost:8002").rstrip("/")
TARGETING_URL = API_URL or os.getenv("TARGETING_URL", "http://localhost:8003").rstrip("/")
EVALUATION_URL = API_URL or os.getenv("EVALUATION_URL", "http://localhost:8004").rstrip("/")

MASTER_KEY = os.getenv("MASTER_KEY", "")
API_KEY = os.getenv("API_KEY", "")
NOME_FLAG = os.getenv("NOME_FLAG", "update-user")
USER_ID = os.getenv("USER_ID", "usuario-123")

# O Ingress da VM exige Host: togglemaster.local, mesmo ao acessar pelo IP.
HEADERS = {"Accept": "application/json"}
if os.getenv("API_HOST"):
    HEADERS["Host"] = os.environ["API_HOST"]
HEADERS_API = {**HEADERS, "Authorization": f"Bearer {API_KEY}"}


def mostrar_resposta(resposta):
    """Mostra também erros em texto e respostas DELETE sem JSON."""
    mostrar_solicitacao(resposta.request)
    print(f"HTTP {resposta.status_code}")
    if resposta.content:
        try:
            print(json.dumps(resposta.json(), ensure_ascii=False, indent=2))
        except ValueError:
            print(resposta.text)
    if not resposta.ok:
        raise SystemExit(1)
