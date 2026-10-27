# ToggleMaster no Kubernetes da VM — roteiro manual

Estes YAMLs reproduzem a **topologia da aplicacao** do enunciado sem criar recursos na AWS: 3 PostgreSQL independentes (auth, flag, targeting), Redis, DynamoDB Local, ElasticMQ (SQS), 5 microsservicos, Ingress e HPA para evaluation e analytics. Os manifests criam 11 Deployments. Os PostgreSQL locais representam os tres RDS; na AWS eles ficarao fora do cluster. Uma tabela DynamoDB e uma fila SQS bastam.

O roteiro pressupoe Kubernetes, Metrics Server, Nginx Ingress e MetalLB disponiveis na VM. Confirme esses componentes antes de aplicar os manifests.

## Antes dos YAMLs: construir e importar as imagens

No PowerShell do Windows, na raiz do projeto:

```powershell
.\k8s\vm\construir-imagens.ps1
```

Isso cria `togglemaster-images.tar` em `$env:TEMP`. Copie os arquivos de `k8s/vm` para `~/togglemaster/k8s/vm` no control plane. Transfira o tar para **cada um** dos workers (`10.10.10.141` e `10.10.10.142`). Em cada worker, execute:

```sh
sudo ctr -n k8s.io images import ~/togglemaster-images.tar
sudo ctr -n k8s.io images ls | grep togglemaster
```

O YAML 06 usa `imagePullPolicy: Never`: sem importar a imagem em ambos os workers, um Pod agendado no worker sem a imagem falhara com `ErrImageNeverPull`. Depois de importar, o tar pode ser apagado dos workers.

## Aplicar em ordem no control plane

Execute os comandos em `~/togglemaster`. `sudo` e necessario porque o kubeconfig do cluster fica em `/etc/kubernetes/admin.conf`.

```sh
cd ~/togglemaster
export KUBECONFIG=/etc/kubernetes/admin.conf

# 1. Namespace
sudo kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/vm/01-namespace.yaml

# 2. SQL de inicializacao, URLs internas e configuracao da fila
sudo kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/vm/02-configmaps.yaml

# 3. Gere senhas e chaves novas; o script cria .env e um YAML Secret com data em base64
sh k8s/vm/03-gerar-secrets.sh
sudo kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/vm/03-secrets.yaml

# 4. Tres PostgreSQL separados
sudo kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/vm/04-postgresql.yaml
sudo kubectl --kubeconfig "$KUBECONFIG" -n togglemaster rollout status deploy/postgres-auth --timeout=300s
sudo kubectl --kubeconfig "$KUBECONFIG" -n togglemaster rollout status deploy/postgres-flag --timeout=300s
sudo kubectl --kubeconfig "$KUBECONFIG" -n togglemaster rollout status deploy/postgres-targeting --timeout=300s

# 5. Redis, DynamoDB Local e fila SQS local
sudo kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/vm/05-servicos-locais.yaml

# 6. Cinco microsservicos e seus Services ClusterIP
sudo kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/vm/06-microsservicos.yaml

# 7. Roteamento HTTP (host togglemaster.local)
sudo kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/vm/07-ingress.yaml

# 8. HPA por CPU para evaluation e analytics
sudo kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/vm/08-hpa.yaml
```

O arquivo `03-secrets.example.yaml` e apenas um modelo: **nao** o aplique. Base64 e codificacao, nao criptografia. O arquivo gerado `03-secrets.yaml` e `.env` estao no `.gitignore`; nao os publique.

## Inspecionar e testar

```sh
sudo kubectl --kubeconfig /etc/kubernetes/admin.conf -n togglemaster get pods,deploy,svc,ingress,hpa
sudo kubectl --kubeconfig /etc/kubernetes/admin.conf -n togglemaster logs deploy/analytics-service --tail=30
```

Para testar as APIs a partir do Windows ou Linux, siga o [README de Teste - Local](../../Teste%20-%20Local/README.md). Use o modelo `.env.remoto.example`, com `API_URL=http://10.10.10.201` e `API_HOST=togglemaster.local`, e preencha a `MASTER_KEY` gerada no `.env` do control plane. Execute `python criar_chave.py` e `python testar_fluxo.py` na pasta dos testes. Nao e necessario executar Python com `sudo` nem copiar um kubeconfig para o computador de teste.

O teste exercita as APIs de autenticacao, flags, regras e avaliacao. Para verificar o consumo de eventos pelo analytics, consulte os logs do servico e os registros no DynamoDB separadamente. O Ingress atual publica `/admin`, `/validate`, `/flags`, `/rules` e `/evaluate`; ele nao publica `/health` nem uma consulta de eventos de analytics.

Os dados dos PostgreSQL e do DynamoDB Local usam `emptyDir` e **se perdem quando o Pod e recriado**. Isso e suficiente para exercitar a aplicacao, mas nao simula a durabilidade de RDS/DynamoDB. Os recursos AWS de EKS, ECR, RDS, ElastiCache, DynamoDB e SQS do enunciado precisam ser provisionados na conta de nuvem para a etapa final; estes YAMLs sao para a VM.

Para apagar apenas o laboratorio ToggleMaster quando terminar: `sudo kubectl --kubeconfig /etc/kubernetes/admin.conf delete namespace togglemaster`.
