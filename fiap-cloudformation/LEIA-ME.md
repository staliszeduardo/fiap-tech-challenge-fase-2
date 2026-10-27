# FIAP - CloudFormation v3

## Atualizar a stack existente
1. CloudFormation > Stacks > `rds-redis-temporarios-02` > Update.
2. Replace current template > Upload a template file: `02-rds-redis-dynamodb-sqs.yaml`.
3. Preserve os parametros atuais (VPC, subnets, classes, SGs e senha); confirme os novos parametros DynamoDB ja preenchidos com valores extraidos do codigo `analytics-service`.
4. Revise o CHANGE SET antes de executar. O esperado e adicionar (`Add`) apenas `AnalyticsTable` e `EvaluationAnalyticsQueue`; NAO execute se RDS/Redis aparecem como Replace/Delete.
5. DynamoDB PAY_PER_REQUEST; SQS Standard. Confira custos AWS.
6. Outputs exibem nome e ARN da tabela, URL e ARN da fila.

## Parametros novos
- AnalyticsTableName: nome esperado pelo codigo do analytics-service (obrigatorio).
- AnalyticsPartitionKeyName: nome da chave HASH exigida pelo codigo (obrigatorio).
- AnalyticsPartitionKeyType: S (string), N (numero), B (binario).
- EvaluationAnalyticsQueueName: padrao fiap-evaluation-analytics-queue.

**Atencao:** Template cria apenas a chave HASH. Se o codigo precisar de sort key, GSIs, LSIs, TTL ou streams, adapte o YAML ANTES de executar.
Nao coloque valores hipoteticos em parametros para uso real.

## Aplicacoes
- evaluation-service precisa de permissao SQS SendMessage.
- analytics-service precisa de permissao SQS ReceiveMessage, DeleteMessage, GetQueueAttributes e DynamoDB PutItem/GetItem/Query/UpdateItem conforme codigo.
- DynamoDB e SQS usam APIs regionais. Pods EKS em subnets privadas podem precisar de NAT ou VPC endpoints (DynamoDB gateway endpoint e SQS interface endpoint).
- Os recursos serao eliminados ao deletar a stack. Faca backup/exportacao de dados que queira preservar.
- Credencial mestre do RDS no template anterior usa parametro NoEcho; preserve o valor ao atualizar.

## Valores conferidos no analytics-service
- `AnalyticsTableName`: `ToggleMasterAnalytics` (README.md e `AWS_DYNAMODB_TABLE`).
- `AnalyticsPartitionKeyName`: `event_id` (app.py, `ensure_local_table` e `put_item`).
- `AnalyticsPartitionKeyType`: `S` (String).
- `EvaluationAnalyticsQueueName`: `fiap-evaluation-analytics-queue` e uma escolha configuravel; validar com o codigo `evaluation-service` quando disponivel.
- `analytics-service` precisa de `AWS_REGION=us-east-1`, `AWS_DYNAMODB_TABLE=ToggleMasterAnalytics`, `AWS_SQS_URL=<URL do output EvaluationAnalyticsQueueUrl>`.
- A fila SQS precisa receber JSON com `user_id`, `flag_name`, `result` (booleano) e `timestamp`.

IMPORTANTE: Ao atualizar a stack existente, revise o change set. Apenas `AnalyticsTable` e `EvaluationAnalyticsQueue` devem ser `Add`; nao execute se `Postgres` ou `Redis` forem `Replace`/`Delete`. A senha do RDS deve ser preservada sem mudanca.
