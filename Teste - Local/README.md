# Teste da API em Python

Mesmo estilo da Fase 1: scripts pequenos com `requests`, um `.env` e um arquivo para cada operação. O `config.py` apenas compartilha URLs, chaves e a exibição das respostas.

## 1. Instalar

No PowerShell, a partir da raiz do projeto:

```powershell
cd ".\Teste - Local"
python -m pip install -r requirements.txt
```

No Linux, use `cd "Teste - Local"`, `python3` e `cp` no lugar de `Copy-Item` nos exemplos abaixo. Os scripts funcionam nos dois sistemas e podem ser executados de qualquer pasta.

## 2. Escolher o ambiente

**Local, com Docker Compose:**

Primeiro suba a aplicação conforme o [README da raiz](../README.md). Depois, nesta pasta:

```powershell
Copy-Item .env.example .env
```

O modelo usa `localhost:8001` a `localhost:8004`. Abra o `.env` e copie para `MASTER_KEY` o valor da mesma variável no `.env` da **raiz**, gerado por `setup-local.ps1` ou `setup-local.sh`.

**Remoto, pelo Ingress da VM:**

```powershell
Copy-Item .env.remoto.example .env
```

O modelo já aponta para:

```env
API_URL=http://10.10.10.201
API_HOST=togglemaster.local
MASTER_KEY=
API_KEY=
```

Preencha `MASTER_KEY` com a chave do **ambiente remoto**. O endereço deve estar acessível pelo computador que executa os testes. Ajuste `API_URL` para o IP ou domínio do seu Ingress. O `API_HOST` corresponde ao host do manifesto `k8s/vm/07-ingress.yaml`; mantenha `togglemaster.local` para esse laboratório. Se outro ambiente usar um domínio próprio, ajuste ou esvazie `API_HOST` conforme o Ingress dele.

Se o remoto expuser serviços em portas separadas, deixe `API_URL` e `API_HOST` vazios e preencha `AUTH_URL`, `FLAG_URL`, `TARGETING_URL` e `EVALUATION_URL` com as respectivas URLs acessíveis. Preencher `API_URL` faz todos esses serviços usarem a mesma base.

Escolha o modelo antes de preencher as chaves: copiar um modelo por cima de `.env` substitui a configuração anterior. O `.env` desta pasta é independente do `.env` da raiz e é ignorado pelo Git.

## 3. Usar o menu interativo

Depois de configurar o `.env`, execute nesta pasta:

```powershell
python main.py
```

Digite o número da operação e pressione Enter. Antes de consultar, editar, excluir, configurar uma regra ou avaliar, o menu mostra as flags existentes com seu estado ativo/inativo. Escolha a flag pelo número ou pelo nome. Para distinguir um nome numérico do número da lista, digite `nome:123`. `0` nessa lista cancela a operação; Enter reaproveita a última flag, quando ela ainda existe.

As operações são:

| Opção | O que você informa |
| --- | --- |
| **1** ou **15** — Criar flag | Nome único, descrição opcional e se começa ativa. |
| **2** — Listar flags | Mostra todas as flags. |
| **3** — Consultar flag | Escolhe qual flag consultar. |
| **4** — Editar flag | Escolhe a flag, altera a descrição e decide se fica ativa ou inativa. |
| **5** — Excluir flag | Escolhe qual flag excluir. |
| **6** — Criar regra | Escolhe a flag, a porcentagem de usuários (0 a 100) e se a regra fica ativa. |
| **7** — Consultar regra | Escolhe a flag da regra. |
| **8** — Editar regra | Escolhe a flag e altera a porcentagem e o estado da regra. |
| **9** — Excluir regra | Escolhe a flag da regra a excluir. |
| **10** — Avaliar flag | Escolhe a flag e informa o ID do usuário. |
| **11** — Criar chave de API | Informa o nome da chave; a nova `API_KEY` é salva no `.env`. |
| **12** — Validar chave | Valida a `API_KEY` configurada. |
| **13** — Teste completo | Executa o fluxo automático usando uma flag exclusiva e limpa seus dados. |
| **14** — Referências da sessão | Escolhe uma flag e o usuário sugeridos nas próximas operações. |
| **0** — Sair | Encerra o menu. |

Na edição, Enter mantém o valor atual. Para limpar a descrição, digite `-`. Em perguntas de ativação, use `S` ou `N`: `S/n` indica que Enter usa sim, e `s/N` indica que Enter usa não. A edição da descrição preserva o estado da flag quando você não o altera. O nome da flag é seu identificador e continua o mesmo; os campos editáveis são descrição e estado ativo/inativo.

Por exemplo, para ativar `nova-hospedagem`, escolha **4**, informe o nome ou o número dela, pressione Enter para manter a descrição e responda `S` à pergunta de ativação. Para alterar só a descrição, informe o texto novo e pressione Enter na pergunta de ativação.

Na criação, escolha um nome de flag que ainda não exista, com até 100 caracteres e sem `/`, `?`, `#` ou `%`; `.` e `..` também não são nomes válidos. O menu permite criar quantas flags desejar pelas opções **1** e **15**; a última flag usada é apenas uma referência, e você pode trocar de flag em cada operação. O usuário também pode ser trocado em cada avaliação. As referências valem para a sessão, sem editar o `.env`.

Se ainda não tiver `API_KEY`, comece por **11** e **12**. A nova chave é usada já na próxima operação. Após cada operação, pressione Enter para voltar; erros HTTP também permitem continuar usando o menu. O cache de avaliação pode manter os valores anteriores por até 30 segundos após mudanças.

## 4. Criar e validar a chave pelos scripts

```powershell
python criar_chave.py
python validar_chave.py
```

`criar_chave.py` usa `MASTER_KEY` e salva a nova `API_KEY` automaticamente no `.env` desta pasta. Se já tiver uma chave válida, basta preencher `API_KEY` e executar `validar_chave.py`. A `SERVICE_API_KEY` do ambiente também pode ser copiada para `API_KEY`.

## 5. Testar como na Fase 1

```powershell
python criar_flag.py
python listar_flags.py
python consultar_flag.py
python criar_regra.py
python consultar_regra.py
python avaliar_flag.py
```

Por padrão, os scripts individuais usam `NOME_FLAG=update-user` e `USER_ID=usuario-123` do `.env`. O menu solicita os valores durante a execução. Os scripts de criação e alteração também aceitam parâmetros; use `--help` para consultar as opções. Por exemplo:

```powershell
python criar_flag.py --nome novo-checkout --descricao "Nova tela de pagamento" --inativa
python atualizar_flag.py --descricao "Descrição atualizada" --ativa
python criar_regra.py --porcentagem 75 --ativa
python atualizar_regra.py --porcentagem 25 --inativa
```

Os scripts de consulta, alteração e exclusão usam a flag definida em `NOME_FLAG`; no menu, o alvo é sempre a flag escolhida na lista. Sem parâmetros, os exemplos preservam os valores usados pelo teste automático: flag criada ativa, atualização desativa a flag, regra criada em 100% e regra atualizada para 50%.

A flag é criada ativa e a regra libera 100% dos usuários; nessa situação, a avaliação deve retornar `"result": true`.

Para alterar a regra para 50% ou desativar a flag:

```powershell
python atualizar_regra.py
python atualizar_flag.py
```

O serviço de avaliação mantém cache por até **30 segundos**. Aguarde esse intervalo após alterações antes de executar `avaliar_flag.py` novamente. Uma flag desativada deve retornar `"result": false`.

Para remover os dados criados manualmente, execute por último:

```powershell
python excluir_regra.py
python excluir_flag.py
```

Todos os scripts mostram o método HTTP, a URL completa, o endereço, os IPs resolvidos, a porta e a rota (incluindo parâmetros de consulta), seguidos do status HTTP e da resposta. Isso também aparece nas consultas feitas pelo próprio menu para escolher uma flag ou carregar uma regra. Quando configurado, o cabeçalho `Host` do Ingress é mostrado; o cabeçalho `Authorization` é omitido.

Por exemplo, ao excluir uma flag em uma API configurada com `http://127.0.0.1:8002`, a saída identifica o destino `DELETE http://127.0.0.1:8002/flags/nova-hospedagem`, a porta `8002` e a rota `/flags/nova-hospedagem`, mesmo que a resposta seja `HTTP 204` sem corpo. Na avaliação, a URL também inclui `user_id` e `flag_name`.

O endereço exibido é o destino acessado pelo computador que executa os testes: no Compose local, as portas publicadas em `localhost`; no ambiente remoto, o IP ou domínio do Ingress. Os IPs de um domínio são os resultados da resolução DNS, que podem incluir IPv4 e IPv6. Eles não representam uma inspeção da conexão TCP nem os IPs internos dos contêineres. Para URLs sem porta explícita, é mostrada a porta padrão do protocolo: `80` para HTTP e `443` para HTTPS.

`201` indica criação, `200` consulta/alteração e `204` exclusão sem corpo. `401` ou `403` pede conferir as chaves e o ambiente; `409` indica que o nome já existe — consulte, atualize ou use outro `NOME_FLAG`.

## Testar o fluxo com um comando

Depois de configurar e validar `API_KEY`:

```powershell
python testar_fluxo.py
```

Esse script executa os exemplos de autenticação, criação, consulta, alteração e exclusão de flags e regras. Ele também confirma que uma flag ativa com regra de 100% retorna `true`. Usa um nome exclusivo por execução e tenta excluir sua regra e sua flag ao terminar, inclusive se ocorrer uma falha nas etapas seguintes à criação.

Os testes acessam somente as APIs HTTP: funcionam local e remotamente sem Docker CLI, `kubectl`, acesso direto aos bancos ou credenciais AWS no computador de teste. Eles não confirmam a entrega assíncrona dos eventos no DynamoDB. O `analytics-service` é um consumidor da fila e não oferece uma API de consulta dos eventos.
