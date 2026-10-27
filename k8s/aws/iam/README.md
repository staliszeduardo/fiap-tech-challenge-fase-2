# Permissoes das aplicacoes

As duas roles usam IRSA e ficam limitadas ao ServiceAccount correspondente no namespace `togglemaster`, ao OIDC atual do EKS e a audiencia `sts.amazonaws.com`. O script descobre o OIDC em cada execucao.

Revise estes documentos antes de executar `configurar-irsa.ps1`:

- `evaluation-policy.json`: `sqs:SendMessage` apenas na fila `fiap-evaluation-analytics-queue`.
- `analytics-policy.json`: `sqs:ReceiveMessage` e `sqs:DeleteMessage` nessa mesma fila; `dynamodb:PutItem` apenas na tabela `ToggleMasterAnalytics`.

Nao ha access keys estaticas nos Pods. A role dos workers nao recebe essas permissoes.

O baseline do analytics foi gerado pelo IAM Policy Autopilot 0.3.0. Foram removidas as permissoes de criacao de tabela usadas somente com DynamoDB Local e as dependencias opcionais de replicacao, resource policies e KMS. Os ARNs foram restringidos aos recursos existentes. O ambiente usa SSE-SQS, sem chave KMS gerenciada pelo cliente. O evaluation usa AWS SDK Go v1, nao suportado pelo analisador; o mapeamento de `SendMessage` foi confirmado na Service Authorization Reference do SQS.

Para reproduzir a geracao do baseline a partir da raiz do projeto, com `uvx` instalado:

```powershell
uvx iam-policy-autopilot@latest generate-policies (Join-Path (Get-Location) 'analytics-service\app.py') --region us-east-1 --account 608541039538 --service-hints sqs dynamodb --pretty
```

O baseline precisa ser revisado antes de uso. Esse comando nao publica politicas.

Referencias:

- https://github.com/awslabs/iam-policy-autopilot
- https://servicereference.us-east-1.amazonaws.com/v1/sqs/sqs.json
- https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html
- https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html
