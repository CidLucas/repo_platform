# Missão: Sistema Blu completo no ar no Cloud Run

Leia este arquivo inteiro antes de agir. Ele consolida o estado real da
infraestrutura em 2026-07-10 — verifique o que mudou desde então antes de
repetir qualquer passo. O runbook complementar é `docs/cloud-run-deploy.md`.

## Objetivo

Colocar os 3 serviços no ar em produção no Cloud Run, com CI/CD contínuo
(push na `main` → Cloud Build → deploy) e **todos os segredos no Secret
Manager** (nada de chave em env var plana):

1. `tool-pool-api` — `services/tool_pool_api/Dockerfile`
2. `agent-api` — `services/agent_api/Dockerfile` (depende do URL do tool-pool-api)
3. `blu-v3` — `apps/blu_v3/Dockerfile` (frontend nginx, **container port 80**)

## Identidade e acesso

- Projeto GCP: **`blu-control-panel`** (número `960100281317`)
- Região: **`southamerica-east1`** | Branch: `main` | Repo GitHub: `CidLucas/repo_platform`
- Conta com acesso: **`cid.lucas@gmail.com`** — use `--account=cid.lucas@gmail.com --project=blu-control-panel` em todo comando gcloud (a config ativa do gcloud aponta para OUTRO projeto; não mude a config global)
- ADC já configurado para essa conta (login feito em 2026-07-10) → o MCP server `cloud-run` (cloud-run-mcp, registrado no escopo local deste repo) deve funcionar. Prefira as tools do MCP quando cobrirem a operação; gcloud para o resto.
- URLs determinísticos: `https://<serviço>-960100281317.southamerica-east1.run.app`

## Estado em 2026-07-10 (verifique antes de agir)

- **tool-pool-api: DEPLOYADO e Ready** ✅ — build `994a4b02` passou (Build,
  Push e Deploy) após correção do trigger (contexto raiz +
  `-f services/tool_pool_api/Dockerfile` + includedFiles). Porém:
  - **ZERO env vars/secrets configurados** no serviço — ele sobe mesmo assim
    (a exigência de `REDIS_URL` é lazy, estoura em runtime), mas as tools
    quebram. Configurar tudo via revisão nova (`gcloud run services update`
    com `--set-secrets`/`--set-env-vars`).
  - **IAM exige autenticação (HTTP 403)** — política vazia. Depois de
    configurar as env vars, liberar público:
    `gcloud run services add-iam-policy-binding tool-pool-api
    --member=allUsers --role=roles/run.invoker --region=southamerica-east1`.
  - Imagens ficam em `southamerica-east1-docker.pkg.dev/blu-control-panel/cloud-run-source-deploy/repo_platform/<serviço>:<sha>`.
- **agent-api e blu-v3: serviços NÃO existem.** O trigger padrão usa
  `gcloud run services update`, que falha se o serviço não existe — o primeiro
  deploy de cada um precisa ser `gcloud run deploy` (cria o serviço) com a
  imagem já pushada pelo build.
- **Triggers de agent-api e blu-v3 NÃO existem ainda.** Crie-os clonando o
  padrão do trigger existente (`gcloud builds triggers describe
  rmgpgab-tool-pool-api-southamerica-east1-CidLucas-repo-platfjug` → montar
  YAML → `gcloud builds triggers import`). Regras: contexto `.` (raiz),
  `-f <caminho do Dockerfile>`, includedFiles por serviço
  (`services/agent_api/**`+`libs/**`; `apps/blu_v3/**`+`packages/**`).
- **Mudanças locais no repo ainda não commitadas** (pré-requisito de TODOS os
  builds):
  - Frontend: `apps/blu_v3/Dockerfile` (ARGs VITE_* com URLs de prod
    embutidos), `apps/blu_v3/nginx.conf` + `apps/blu_v3/index.html` (CSP
    liberando os backends *.run.app e Google Picker)
  - Backends: `libs/blu_llm_service/` (provider DeepSeek + langchain-openai
    obrigatório) e `poetry.lock` regenerados em `services/agent_api/` e
    `services/tool_pool_api/`
  - Docs: `docs/cloud-run-deploy.md`, este arquivo
  Commite e pushe na `main` ANTES de rodar qualquer build.

## Segredos e variáveis

Valores fonte: `.env` na raiz do repo (NUNCA imprima valores; leia
programaticamente). Lista completa por serviço em `docs/cloud-run-deploy.md`.

1. Crie um secret no Secret Manager por segredo (`gcloud secrets create` +
   `gcloud secrets versions add` lendo do `.env`), nomes iguais às env vars.
2. Dê `roles/secretmanager.secretAccessor` à service account de runtime
   `960100281317-compute@developer.gserviceaccount.com`.
3. No deploy, use `--set-secrets VAR=nome-do-secret:latest` para segredos e
   `--set-env-vars` para não-segredos (JWT_ALGORITHM=ES256, DB_MODE=supabase,
   LLM_PROVIDER, LANGFUSE_HOST, DOCKER_MCP_ENABLED=false, CORS_ORIGINS, URLs).

Valores críticos não-segredos:
- Ambos backends: `CORS_ORIGINS=https://blu-v3-960100281317.southamerica-east1.run.app`
- agent-api: `MCP_SERVER_URL=https://tool-pool-api-960100281317.southamerica-east1.run.app/mcp/`
- tool-pool-api: `MCP_AUTH_BASE_URL` e `TOOL_POOL_API_URL` = o próprio URL do serviço
- **NÃO defina `PYTHONPATH`** (o Dockerfile já define; sobrescrever quebra imports)

## ✅ Ex-bloqueadores (resolvidos em 2026-07-10)

1. **Redis**: `REDIS_URL` agora está no `.env` raiz (Redis Cloud, conexão
   plaintext `redis://` — testada com AUTH+PING ok). Basta levar ao Secret
   Manager.
2. **Chaves LLM de produção**: são `OLLAMA_CLOUD_API_KEY`, `HF_TOKEN` e
   `DEEPSEEK_API_KEY` (todas no `.env` raiz, validadas ao vivo em 2026-07-10).
   `GOOGLE/OPENAI/ANTHROPIC_API_KEY` ficam vazias — NÃO são usadas em prod.
   `LLM_PROVIDER=ollama_cloud`. O provider DeepSeek foi adicionado ao
   `blu_llm_service` (modelos `deepseek-v4-flash`/`deepseek-v4-pro`), e
   `langchain-openai` virou dependência obrigatória da lib (HF e DeepSeek
   usam ChatOpenAI) — os `poetry.lock` de agent_api e tool_pool_api já foram
   regenerados. Essas mudanças precisam estar commitadas/pushadas na `main`
   antes dos builds dos backends.

## Configuração dos serviços (deploy)

| | tool-pool-api | agent-api | blu-v3 |
|---|---|---|---|
| Porta | 8080 (default) | 8080 (default) | **80** |
| Memória/CPU | 1–2Gi / 1 | 2Gi / 1 | 256Mi / 1 |
| Instâncias | min 0–1, max 3 | min 1, max 5 | min 0, max 3 |
| Auth | público (`--allow-unauthenticated`) | público | público |

## Ordem de execução

1. Commitar/pushar as mudanças locais pendentes na `main` (lib LLM + locks +
   frontend + docs — ver `git status`)
2. Criar secrets no Secret Manager + IAM do secretAccessor
3. tool-pool-api (já existe): `gcloud run services update` com secrets/env
   vars → liberar `allUsers` como `run.invoker` → smoke test `/health`
4. Criar trigger do agent-api → rodar build → `gcloud run deploy agent-api` → `/health`
5. Commitar/pushar mudanças locais → criar trigger do blu-v3 → build →
   `gcloud run deploy blu-v3 --port 80` → `/healthz`
6. E2E no browser: login → chat (exercita agent-api → tool-pool-api). Erros
   de CORS/CSP aparecem no DevTools console.
7. Confirmar que um push na `main` redeploya só o serviço tocado (includedFiles)

## Critério de pronto

Os 3 serviços servindo nos URLs acima, health checks verdes, fluxo de chat
funcionando no browser, segredos 100% no Secret Manager, e CI/CD disparando
por push com filtro de paths correto.
