# ToggleMaster no EKS - roteiro para executar no PowerShell

Esta versao usa as cinco imagens ECR `:1.0` e o RDS unico aprovado pelo professor, com os databases `authdb`, `flagdb` e `targetingdb`. Redis, SQS e DynamoDB ficam na AWS. Os arquivos de `k8s/vm` continuam destinados ao laboratorio local.

Execute os blocos na ordem. Se um comando falhar, pare nessa etapa e consulte o diagnostico no fim deste roteiro.

## 1. Conectar ao cluster

Abra o PowerShell na raiz do projeto:

```powershell
Set-Location 'D:\MEGA\4.Documentos Faculdade\POS Graduacao Fiap\Fase 2\Tech Challenge'
aws sts get-caller-identity
aws eks update-kubeconfig --region us-east-1 --name fiap-techchallenge
kubectl config current-context
kubectl get nodes
kubectl top nodes
kubectl get pods -n nginx-ingress
```

Confirme a conta `608541039538`, o cluster `fiap-techchallenge`, os dois workers `Ready` e o NGINX pronto. Metrics Server, NGINX e AWS Load Balancer Controller ja foram instalados. Os workers ja possuem a politica para baixar imagens ECR; nao e necessario executar `docker login` nos nos nem criar `imagePullSecrets` para estes repositorios da mesma conta.

## 2. Namespace, ConfigMap e credenciais

```powershell
kubectl apply -f .\k8s\aws\01-namespace.yaml
kubectl apply -f .\k8s\aws\02-configmaps.yaml
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\k8s\aws\gerar-secrets.ps1
kubectl apply -f .\k8s\aws\03-secrets.yaml
```

O script pede a senha ATUAL do usuario `postgres` do RDS, sem exibi-la. Nao invente uma senha nova: esse script nao altera a senha do RDS. Ele gera as chaves da aplicacao e as tres URLs PostgreSQL com `sslmode=require`, escapando caracteres especiais da senha. O Secret usa `data` em base64 e esta no `.gitignore`. Base64 nao criptografa as credenciais.

O arquivo nao e sobrescrito se ja existir. Em uma nova tentativa, reutilize `03-secrets.yaml` e pule o gerador. Se o endpoint ou o usuario do RDS mudou, use os parametros `-RdsHost` e `-RdsUser` na primeira geracao.

O ConfigMap usa os endpoints confirmados no ambiente:

- Redis com TLS: `rediss://master.redis-fiap.y4wj4j.use1.cache.amazonaws.com:6379`.
- Fila: `https://sqs.us-east-1.amazonaws.com/608541039538/fiap-evaluation-analytics-queue`.
- Tabela: `ToggleMasterAnalytics`, chave `event_id` String.

Se recriar esses recursos, atualize os endpoints antes de aplicar. Nao aplique os manifests de bancos ou emuladores de `k8s/vm` no EKS.

## 3. IRSA para evaluation e analytics

Revise as duas politicas JSON na pasta `iam`. O script abaixo cria duas roles IAM e anexa as politicas inline: evaluation pode enviar mensagens na fila; analytics pode receber/apagar mensagens da mesma fila e inserir itens na tabela indicada. Ele nao muda a role dos workers nem a do Load Balancer Controller.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\k8s\aws\configurar-irsa.ps1
kubectl apply -f .\k8s\aws\04-serviceaccounts.yaml
kubectl get serviceaccount evaluation-service analytics-service -n togglemaster -o yaml
```

As anotacoes esperadas apontam para `ToggleMasterEvaluationRole` e `ToggleMasterAnalyticsRole`. O script consulta o OIDC do cluster atual; nao reutiliza um ID antigo. Reexecutar atualiza somente as roles identificadas como pertencentes a este roteiro. Se algum desses nomes ja pertencer a outra configuracao, ele para sem sobrescrever essa role.

O OIDC do cluster ja esta associado ao IAM. Se voce recriar o cluster e o script informar que o provider nao existe, execute antes: `eksctl utils associate-iam-oidc-provider --cluster fiap-techchallenge --region us-east-1 --approve`.

## 4. Criar os databases e as tabelas no RDS

O Job abaixo conecta ao RDS por dentro do EKS. Cria os tres databases apenas quando ausentes, aplica os schemas dos microsservicos e cadastra o hash da chave interna do evaluation. Nao cria outra instancia RDS nem apaga dados.

```powershell
kubectl apply -f .\k8s\aws\05-rds-init-configmap.yaml
kubectl apply -f .\k8s\aws\05-rds-init-job.yaml
kubectl wait --for=condition=complete job/togglemaster-rds-init -n togglemaster --timeout=300s
kubectl logs job/togglemaster-rds-init -n togglemaster
```

Avance somente depois de o Job terminar com sucesso. Deve aparecer a mensagem `RDS inicializado: authdb, flagdb e targetingdb; chave interna cadastrada.` Se voce ja criou os databases com `03-criar-bancos.sql`, o Job os reutiliza.

Para repetir o Job depois de corrigir um erro, apague apenas esse Job e aplique-o novamente:

```powershell
kubectl delete job togglemaster-rds-init -n togglemaster
kubectl apply -f .\k8s\aws\05-rds-init-job.yaml
kubectl wait --for=condition=complete job/togglemaster-rds-init -n togglemaster --timeout=300s
kubectl logs job/togglemaster-rds-init -n togglemaster
```

## 5. Subir os cinco microsservicos

```powershell
kubectl apply -f .\k8s\aws\06-microsservicos.yaml
kubectl rollout status deployment/auth-service -n togglemaster --timeout=300s
kubectl rollout status deployment/flag-service -n togglemaster --timeout=300s
kubectl rollout status deployment/targeting-service -n togglemaster --timeout=300s
kubectl rollout status deployment/evaluation-service -n togglemaster --timeout=300s
kubectl rollout status deployment/analytics-service -n togglemaster --timeout=300s
kubectl get pods,deployments,services -n togglemaster
```

Os cinco Deployments devem ficar `1/1`. O Pod do Job anterior permanece como `Completed`, o que e esperado. Os Services das aplicacoes sao `ClusterIP`; o LoadBalancer existente continua sendo o Service do NGINX.

Os Deployments usam `imagePullPolicy: IfNotPresent`. Se publicar codigo diferente com a mesma tag `1.0`, os nos podem reutilizar a imagem em cache; prefira publicar uma tag nova e atualizar o manifesto quando fizer alteracoes no codigo.

## 6. Publicar o Ingress e validar acesso externo

```powershell
kubectl apply -f .\k8s\aws\07-ingress.yaml
kubectl get ingress -n togglemaster
kubectl describe ingress togglemaster -n togglemaster
$lb = kubectl get service nginx-ingress-controller -n nginx-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
curl.exe -i -H 'Host: togglemaster.local' "http://$lb/evaluate?user_id=teste-aws&flag_name=flag-inexistente"
```

A resposta esperada e HTTP `200` com `result: false`, se a flag nao existir. A consulta produz um evento para analytics. O header `Host: togglemaster.local` precisa ser enviado: essa e a regra do Ingress. Abrir apenas a raiz do hostname do NLB pode continuar retornando `404`.

## 7. Testar criacao de chave, flag, regra e avaliacao

Para testar as rotas autenticadas sem transmitir as chaves pelo HTTP publico, mantenha este comando rodando em OUTRO PowerShell:

```powershell
kubectl port-forward -n nginx-ingress service/nginx-ingress-controller 8080:80
```

No terminal principal, na raiz do projeto:

```powershell
Set-Location '.\Teste API'
python -m pip install -r requirements.txt
```

Se `Teste API/.env` ainda nao existe, copie o modelo com `Copy-Item .env.remoto.example .env`. Se ja existe, edite-o preservando seus valores e ajustando:

```dotenv
API_URL=http://127.0.0.1:8080
API_HOST=togglemaster.local
MASTER_KEY=<MASTER_KEY do Secret da AWS>
API_KEY=
NOME_FLAG=update-user
USER_ID=usuario-123
```

Para obter sua MASTER_KEY, no seu terminal local:

```powershell
$secret = kubectl get secret togglemaster-secrets -n togglemaster -o json | ConvertFrom-Json
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($secret.data.MASTER_KEY))
```

Cole a chave apenas no seu `.env` local e execute:

```powershell
python criar_chave.py
python validar_chave.py
python testar_fluxo.py
Set-Location '..'
```

`criar_chave.py` salva a nova API_KEY no `.env` dos testes. O teste cria dados com nome exclusivo e tenta remove-los ao terminar. A chave do evaluation ja foi cadastrada pelo Job; ela e independente dessa chave dos testes.

## 8. Confirmar SQS e DynamoDB

```powershell
kubectl logs deployment/evaluation-service -n togglemaster --tail=50
kubectl logs deployment/analytics-service -n togglemaster --tail=50
aws dynamodb scan --table-name ToggleMasterAnalytics --region us-east-1 --limit 5
```

Nos logs, procure envio de evento para SQS e evento salvo no DynamoDB. A fila pode ficar vazia porque o analytics consome e apaga as mensagens rapidamente; isso nao representa falha. O `/health` do analytics, sozinho, nao confirma acesso a SQS/DynamoDB.

## 9. Aplicar o HPA

```powershell
kubectl apply -f .\k8s\aws\08-hpa.yaml
kubectl get hpa -n togglemaster
kubectl top pods -n togglemaster
```

Ha um HPA por CPU para evaluation e outro para analytics: alvo de 70%, minimo de 1 e maximo de 3 replicas. Pode levar cerca de um minuto para as primeiras metricas aparecerem. A escalabilidade sob carga precisa ser demonstrada separadamente; o HPA nao foi testado em carga por este roteiro. KEDA continua opcional, e o limite maximo do Node Group, sozinho, nao configura Cluster Autoscaler.

## Diagnostico

```powershell
kubectl get pods -n togglemaster -o wide
kubectl get events -n togglemaster --sort-by=.lastTimestamp
kubectl describe deployment evaluation-service -n togglemaster
kubectl logs deployment/evaluation-service -n togglemaster --tail=100
kubectl logs deployment/analytics-service -n togglemaster --tail=100
```

- `ImagePullBackOff`: veja `kubectl describe pod <nome> -n togglemaster`; confira tag ECR, acesso de rede e politica ECR do worker.
- Erro no Job: confira senha atual do RDS, endpoint, security group e logs do Job antes de subir as aplicacoes.
- Erro Redis: confira o endpoint e o prefixo `rediss://`, porque o ElastiCache exige TLS.
- `AccessDenied` ou `NoCredentials`: confira role, trust policy com OIDC atual e `serviceAccountName`; nao use as credenciais `local` da VM.
- Pod `Pending`: confira eventos, recursos livres e limite de Pods/IPs dos workers.
- `404` no Ingress: confira o header `Host` e use uma rota publicada, como `/evaluate`, `/flags` ou `/admin/keys`.
- `502`/`503`: confira os Pods prontos, Services e EndpointSlices da aplicacao.

## Referencias

- IRSA: https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html
- SDKs com suporte a IRSA: https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html
- RDS com TLS: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html
- Detalhes das politicas: [iam/README.md](iam/README.md).
