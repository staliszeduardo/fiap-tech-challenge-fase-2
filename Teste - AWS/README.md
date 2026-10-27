# Testes AWS - ToggleMaster

Execute estes scripts no seu Windows. Esta pasta tem configuracao propria e nao importa nem altera arquivos de `Teste API`.

## Preparacao

No PowerShell:

```powershell
Set-Location 'D:\MEGA\4.Documentos Faculdade\POS Graduacao Fiap\Fase 2\Tech Challenge\Teste AWS'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Copie o modelo somente na primeira vez. Em execucoes futuras, preserve seu `.env` e suas chaves. Abra o arquivo e confira os endpoints. Os valores publicos do ambiente conhecido ja estao preenchidos. Se recriou recursos, ajuste-os.

Para abreviar os exemplos abaixo, ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se a ativacao estiver bloqueada, substitua `python` por `.\.venv\Scripts\python.exe` nos exemplos. Nao e necessario alterar a politica do Windows.

Os scripts boto3 usam as credenciais que voce ja configurou com `aws configure` ou seu perfil AWS. Para outro perfil, preencha `AWS_PROFILE` no `.env`. As roles IRSA sao dos Pods, nao do Python local. Nao salve access keys neste projeto.

```powershell
python ver_ambiente.py
```

Esse comando consulta STS, atributos da fila e estrutura da tabela, sem escrever dados. O perfil precisa de `sqs:GetQueueAttributes`, `sqs:SendMessage`, `dynamodb:DescribeTable` e `dynamodb:Scan` para todas as funcionalidades AWS desta pasta. Nenhum script altera IAM automaticamente.

Para as APIs autenticadas, preencha `API_KEY` com uma chave da aplicacao AWS. Se ainda nao possui uma, preencha `MASTER_KEY` e execute:

```powershell
python criar_chave.py
```

Ele cria uma chave na API e salva `API_KEY` somente no `.env` desta pasta, sem exibir a chave. As chaves de `Teste API` nao sao copiadas automaticamente.

O Ingress exige `API_HOST=togglemaster.local`. O `API_URL` do modelo e o NLB publico. Para testar rotas autenticadas por port-forward, mantenha `kubectl port-forward -n nginx-ingress service/nginx-ingress-controller 8080:80` em outro terminal e use `API_URL=http://127.0.0.1:8080`. O mesmo Host continua necessario.

## Menu

```powershell
python main.py
```

Cada opcao mostra seu resultado no terminal. Os scripts tambem funcionam individualmente:

| Script | O que mostra ou executa |
| --- | --- |
| `ver_ambiente.py` | Conta/perfil efetivo, endpoints, fila e chave da tabela DynamoDB. |
| `criar_chave.py` | Cria API_KEY para os testes e salva no `.env` desta pasta. |
| `testar_api.py` | Cria/le flags e regras, atualiza descricao, avalia a flag e aguarda seu evento no DynamoDB. |
| `enviar_eventos.py` | Envia mensagens validas diretamente a SQS, em lotes de ate 10, com identificador de teste. |
| `monitorar_aws.py` | Exibe fila, registros encontrados no DynamoDB e, com `--cluster`, replicas do analytics; salva CSV. |
| `consultar_dynamodb.py` | Lista amostra de eventos e informa se o Scan foi completo ou parcial. |
| `gerar_carga.py` | Faz avaliacoes HTTP concorrentes e mostra sucessos, erros, resultados true/false e latencias p50/p95. |
| `cluster.py` | Mostra Pods/HPA/KEDA ou pausa/retoma o analytics pelo ScaledObject. Requer kubectl. |
| `consultar_rds.py` | Le diretamente as tabelas SQL, com transacao somente leitura e senha digitada localmente. Exige acesso privado/tunel. |

Use `python nome_do_script.py --help` para consultar argumentos.

## Testar o codigo da aplicacao, incluindo o analytics

```powershell
python testar_api.py --manter
```

O script cria uma flag exclusiva, regra de 100%, confirma as leituras pelas APIs que usam RDS, atualiza e rele a descricao, faz `/evaluate` esperando `true` e aguarda ate 120 segundos para encontrar o evento no DynamoDB. Isso verifica o caminho HTTP -> evaluation -> SQS -> analytics -> DynamoDB. As leituras HTTP nao sao apresentadas como consulta SQL independente; para isso ha o script opcional de RDS.

Com `--manter`, a flag/regra ficam disponiveis para carga e o nome e exibido no final. Sem essa opcao, os dados exclusivos criados pelo teste sao removidos das APIs. Eventos historicos no DynamoDB permanecem.

```powershell
python testar_api.py
python testar_api.py --sem-dynamodb
python testar_api.py --espera 180 --paginas 100
```

Nao execute o teste completo enquanto o analytics estiver pausado: o evento precisa ser consumido para a verificacao terminar.

## Demonstracao KEDA: fila cresce, Pods sobem e DynamoDB recebe eventos

Primeiro confira o KEDA e o nome do ScaledObject no `.env`:

```powershell
python cluster.py status
```

Em um segundo PowerShell, na mesma pasta e com o mesmo ambiente Python, deixe o monitor rodando:

```powershell
python monitorar_aws.py --cluster --flag demonstracao-keda
```

No primeiro terminal, pause o analytics em zero replicas, aguarde os Pods terminarem e envie um lote:

```powershell
python cluster.py pausar
python cluster.py status
python enviar_eventos.py --quantidade 1000 --flag demonstracao-keda
```

O monitor deve mostrar aumento de mensagens disponiveis. Retome a escala:

```powershell
python cluster.py retomar
```

Observe a fila diminuir, as replicas do analytics aumentarem conforme a carga e os eventos encontrados no DynamoDB crescerem. Depois da fila esvaziar, o KEDA pode voltar a zero respeitando `cooldownPeriod`. O numero efetivo de replicas depende da velocidade do consumidor e da configuracao do ScaledObject.

Esse envio direto exercita SQS/KEDA/analytics/DynamoDB. Para produzir eventos pelo codigo do evaluation, use o gerador HTTP:

```powershell
python gerar_carga.py --flag NOME_DA_FLAG_CRIADA_NO_TESTE --duracao 60 --usuarios 10
```

O script retorna codigo de erro se houver falhas HTTP e salva o resumo. Um HTTP 200 nao prova que o envio assincrono chegou ao banco; acompanhe o monitor e consulte os eventos.

Para limitar a taxa de envio direto a 50 mensagens por segundo:

```powershell
python enviar_eventos.py --quantidade 1000 --taxa 50
```

Se interromper o teste depois de pausar, execute `python cluster.py retomar` para reativar o consumidor. Nenhum script purga a fila ou apaga eventos do DynamoDB.

## Consulta e evidencias

```powershell
python consultar_dynamodb.py --flag demonstracao-keda --limite 10
python monitorar_aws.py --cluster --duracao 120
```

CSV do monitor e resumos JSON ficam em `resultados/`, ignorado pelo Git. Esses arquivos ajudam a registrar a demonstracao.

- SQS fornece contagens aproximadas; a fila pode ficar baixa porque o consumidor processa rapidamente. O monitor so consulta atributos; nao recebe, oculta ou apaga mensagens.
- A coluna DynamoDB e atualizada a cada 10 segundos. Ela conta correspondencias nas paginas percorridas. `SCAN_PARCIAL=sim` significa que ha mais dados e voce pode aumentar `--paginas`.
- Sem `--flag`, o monitor conta todos os eventos percorridos, incluindo testes antigos. Use um nome de flag novo por demonstracao para acompanhar somente aquela execucao.
- DynamoDB e consultado por Scan porque a chave e `event_id`, nao `flag_name`. O filtro nao evita ler os outros itens; o limite de paginas controla esse trabalho. Nao ha um contador exato instantaneo nem uma garantia de snapshot unico entre paginas.
- SQS Standard pode entregar mensagens novamente; o analytics gera outro `event_id` ao processa-las. A contagem de registros pode superar a quantidade de envios.
- `gerar_carga.py` informa latencia HTTP, nao tempo de processamento da fila.

## RDS privado: consulta SQL opcional

O RDS atual esta em rede privada. O Python da sua maquina nao vai acessa-lo diretamente pelo endpoint publico da Internet. O teste HTTP ja le flags/regras pelas APIs. Para SELECT independente, estabeleca um tunel por uma maquina que tenha acesso a VPC e configure `RDS_HOST`, `RDS_PORT` e `RDS_USER` no `.env`.

Exemplo quando um tunel previamente criado escuta em localhost:15432:

```dotenv
RDS_HOST=127.0.0.1
RDS_PORT=15432
RDS_USER=postgres
RDS_SSLMODE=require
```

```powershell
python consultar_rds.py --database flagdb --nome NOME_DA_FLAG
python consultar_rds.py --database targetingdb --nome NOME_DA_FLAG
python consultar_rds.py --database authdb --limite 5
```

O script pede a senha atual sem salva-la, usa conexao somente leitura e nao consulta hashes de chaves. Nao abre security groups, nao cria tunel e nao expoe o RDS. Se usar verificacao de certificado (`verify-full`), configure host/certificado de acordo com seu tunel e o CA do RDS.

## Validacao offline dos scripts

```powershell
python -m unittest discover -s tests -v
```

Os testes usam respostas simuladas do SDK e um servidor HTTP local; nao geram carga na AWS. A demonstracao real e feita pelos comandos acima.

Referencias: [SQS batch](https://docs.aws.amazon.com/boto3/latest/reference/services/sqs/client/send_message_batch.html), [atributos da fila](https://docs.aws.amazon.com/boto3/latest/reference/services/sqs/client/get_queue_attributes.html), [Scan paginado](https://docs.aws.amazon.com/boto3/latest/reference/services/dynamodb/paginator/Scan.html).
