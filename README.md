# ToggleMaster — Tech Challenge Fase 2

Aplicação composta por cinco microsserviços (auth, flags, targeting, evaluation e analytics), bancos PostgreSQL, Redis, DynamoDB Local e ElasticMQ. O caminho reproduzível para avaliação local usa Docker Compose; Kubernetes na VM e AWS são opções separadas e exigem infraestrutura própria.

## Pré-requisitos para execução local

- Git
- Docker Desktop com contêineres Linux no Windows, ou Docker Engine e Docker Compose no Linux
- Python 3.10 ou superior para os scripts de teste da API

## Subir no Windows

No PowerShell, na raiz do repositório:

```powershell
.\setup-local.ps1
docker compose up -d --build
docker compose ps
```

O script cria um `.env` local com segredos aleatórios. O arquivo fica ignorado pelo Git. Aguarde os serviços ficarem saudáveis. Para acompanhar:

```powershell
docker compose logs -f auth-service flag-service targeting-service evaluation-service analytics-service
```

## Subir no Linux

```sh
sh setup-local.sh
docker compose up -d --build
docker compose ps
```

## Exercitar a API

Em outro terminal, na raiz do repositório:

```powershell
cd "Teste - Local"
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

No Linux, use `cp .env.example .env`. Abra `Teste - Local/.env`, copie o valor de `MASTER_KEY` do `.env` da raiz e execute:

```sh
python criar_chave.py
python testar_fluxo.py
```

O fluxo cria e valida uma chave, exercita criação/consulta/alteração/exclusão de flags e regras, avalia uma flag e limpa os dados de teste. Consulte [Teste - Local/README.md](Teste%20-%20Local/README.md) para executar operações individuais ou apontar para outra API.

## Serviços locais

| Serviço | Porta |
| --- | ---: |
| auth-service | 8001 |
| flag-service | 8002 |
| targeting-service | 8003 |
| evaluation-service | 8004 |
| analytics-service | 8005 |
| DynamoDB Local | 8000 |
| ElasticMQ (SQS) | 9324 |

O Compose cria dez contêineres: cinco microsserviços, dois PostgreSQL, Redis, DynamoDB Local e ElasticMQ. Os códigos estão em `Microserviços/`; os arquivos de inicialização e configuração local estão em `local/`.

## Encerrar

```sh
docker compose down
```

`docker compose down -v` também apaga os dados persistidos. Para implantar em Kubernetes na VM, siga [k8s/vm/README.md](k8s/vm/README.md). Para a AWS, siga [k8s/aws/README.md](k8s/aws/README.md); esse caminho depende de conta AWS, cluster e recursos já provisionados.

## Segurança e arquivos locais

Use somente `.env.example` como modelo versionado. Não publique `.env`, `k8s/aws/03-secrets.yaml`, `k8s/vm/03-secrets.yaml`, chaves privadas, ambientes virtuais nem resultados locais. Os arquivos `03-secrets.yaml` são gerados localmente e o `.gitignore` os exclui.