# Inventário de secrets/credenciais sensíveis — Blu (Mai/2026)

Data: 2026-05-25
Escopo: A2 do Pre-Onboarding Hardening Plan (levantamento rápido, sem leitura de valores)

Regras aplicadas neste inventário:
- Não houve leitura nem exposição de valores de secret.
- Foi consultado apenas `vault.secrets` (metadados). Não foi usado `vault.decrypted_secrets`.
- O `.env` foi auditado somente por nomes de chaves.

## Resumo executivo (top table)

| Secret | Where it lives | Status | Last known rotation | Rotation process (1 linha) |
|---|---|---|---|---|
| `google_oauth_config` (secret_id `7d7d8c90-806b-4938-abad-ef0c327f01b7`) | Supabase Vault (`vault.secrets`) | 🟢 Vault | 2026-05-08 (criação no Vault) | Rotacionar no Google Cloud Console e atualizar via `vault.update_secret(...)` |
| `oauth_google_*` (tokens por conta) | Supabase Vault (`vault.secrets`) | 🟢 Vault | até 2026-05-22 (último registro) | Reautenticar OAuth / refresh e persistir novamente via fluxo backend |
| `rfq_follow_ups_token` | Supabase Vault (`vault.secrets`) | 🟢 Vault | 2026-04-27 | Gerar novo token no emissor e atualizar secret no Vault |
| `CREDENTIALS_ENCRYPTION_KEY` (equivalente operacional ao FERNET_KEY) | `.env` + env de Edge Functions | 🟡 .env only | N/D | Criar nova chave Fernet, recriptografar tokens e redeploy das EFs |
| `ROUTINE_DISPATCH_TOKEN` | `.env` (agent_api) | 🟡 .env only | N/D | Gerar token novo, atualizar env/runtime e reiniciar serviços |
| `SUPABASE_SERVICE_KEY` (`service_role`) | `.env` (backend/libs) | 🟡 .env only | N/D | Rotacionar no Supabase Dashboard, atualizar runtime e validar jobs/RPCs |
| `SUPABASE_DB_URL` | `.env` + Edge Functions | 🟡 .env only | N/D | Trocar credencial DSN no Supabase e atualizar consumidores |
| `SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY` | `.env`/frontend/backend | 🟡 .env only | N/D | Regenerar chave anon no Supabase e atualizar frontend/backend |
| `MCP_AUTH_GOOGLE_CLIENT_ID` | `.env` (tool_pool_api) | 🟡 .env only | N/D | Atualizar credencial OAuth de app e alinhar com Vault/config central |
| `MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV` | `.env` (fallback de dev) | 🟡 .env only | N/D | Substituir fallback por fonte segura e remover dependência de `.env` |
| Tokens LLM (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `HF_TOKEN`, `CO_API_KEY`, `OLLAMA_CLOUD_API_KEY`) | `.env` | 🟡 .env only | N/D | Rotacionar por provedor e atualizar apenas runtime seguro |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | `.env` (lido via env vars; hardcodes removidos em 2026-05-25) | 🟡 .env only | N/D | Rotacionar chaves expostas no histórico do git e migrar para Vault/secret manager |
| `POLP_API_SECRET` | `.env` + Edge Functions | 🟡 .env only | N/D | Rotacionar no provedor Polp e atualizar runtime |
| `POLP_WEBHOOK_SECRET` / `PLUGGY_WEBHOOK_SECRET` | Esperado em runtime (não apareceu no `.env` local) | ⚪ external | N/D | Validar onde está hoje, rotacionar no provedor e sincronizar runtime |

## Evidências objetivas coletadas

1. `.env` (nomes apenas): 56 variáveis detectadas.
2. `vault.secrets`: 188 registros (metadados), incluindo:
   - `google_oauth_config` (com secret_id conhecido no handoff)
   - 6 entradas `oauth_google_*`
   - `rfq_follow_ups_token`
3. `.gitignore`: cobre `.env`, `*.env.local`, `.env.production`, `.env.prod`, `.env.cloudrun` e padrões de `.json` sensíveis.
4. `git log --all --diff-filter=A --name-only -- '.env*' | head -10`:
   - evidência rápida de versionamento de `.env.cloudrun.example` (arquivo de exemplo).

## Inventário por secret (propósito, leitura no código, rotação, blast radius)

### 1) `CREDENTIALS_ENCRYPTION_KEY` (FERNET_KEY operacional)
- Propósito:
  - Criptografia/descriptografia de tokens de integração (Google/Monday/etc.) em Edge Functions.
- Onde é lido no código (aprox):
  - `supabase/functions/get-agenda-events/index.ts:22`
  - `supabase/functions/google-oauth-callback/index.ts:15`
  - `supabase/functions/onboarding-capture-drive-token/index.ts:24`
  - `supabase/functions/save-api-token/index.ts:20`
- Rotação (passo-a-passo):
  1) Gerar nova chave Fernet.
  2) Implementar rotina de re-encrypt para tokens já persistidos.
  3) Atualizar runtime das Edge Functions.
  4) Validar OAuth refresh e leitura de agenda/conectores.
- Blast radius se vazar:
  - Alto: potencial de decriptar tokens de integrações armazenados com essa chave.

### 2) `ROUTINE_DISPATCH_TOKEN`
- Propósito:
  - Proteger endpoint interno de disparo de rotinas.
- Onde é lido no código:
  - `services/agent_api/src/agent_api/config.py:38`
  - `services/agent_api/src/agent_api/api/routines_router.py:35`
- Rotação:
  1) Gerar novo token aleatório.
  2) Atualizar env do `agent_api` e caller(es) internos.
  3) Reiniciar serviço e testar endpoint `/internal/routines/run-dispatched`.
- Blast radius:
  - Médio/alto: execução indevida de rotinas internas e consumo de recursos.

### 3) `SUPABASE_SERVICE_KEY` (service_role)
- Propósito:
  - Acesso privilegiado (bypass de RLS) para backend e Edge Functions.
- Onde é lido no código:
  - `libs/blu_supabase_client/src/blu_supabase_client/client.py:33`
  - `services/tool_pool_api/src/tool_pool_api/server/resources.py:186`
  - `services/agent_api/src/agent_api/core/routine_artifacts.py:483`
- Rotação:
  1) Regenerar service_role no Supabase.
  2) Atualizar runtime de todos os serviços/EFs consumidores.
  3) Revalidar RPCs, jobs e fluxos com privilégio.
- Blast radius:
  - Crítico: acesso amplo a dados de tenants e operações administrativas.

### 4) `SUPABASE_DB_URL`
- Propósito:
  - Conexão direta PostgreSQL (migrations/testes/EFs específicas).
- Onde é lido no código:
  - `supabase/functions/process-document/index.ts:21`
  - `supabase/functions/search-documents/index.ts:21`
  - `tests/test_rls_regression.py:73`
- Rotação:
  1) Rotacionar credencial/senha associada ao DSN.
  2) Atualizar runtime e pipelines que dependem da URL.
  3) Executar smoke de funções SQL dependentes.
- Blast radius:
  - Crítico: acesso direto ao banco com superfície ampla.

### 5) `SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY`
- Propósito:
  - Chave pública para operações client-side / RLS-aware.
- Onde é lido no código:
  - `services/agent_api/src/agent_api/core/routine_artifacts.py:482`
  - `libs/blu_supabase_client/src/blu_supabase_client/client.py:34`
  - `supabase/functions/google-oauth-start/index.ts:16`
- Rotação:
  1) Regenerar anon key no Supabase.
  2) Atualizar frontend e backends que fazem fallback.
  3) Validar autenticação e chamadas `functions.invoke`.
- Blast radius:
  - Médio: não é chave privilegiada, mas impacta autenticação/integração entre app e Supabase.

### 6) `MCP_AUTH_GOOGLE_CLIENT_ID` + `MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV` + `google_oauth_config`
- Propósito:
  - Credenciais OAuth Google usadas em fluxos de autenticação/integração.
- Onde é lido no código:
  - `services/tool_pool_api/src/tool_pool_api/server/dependencies.py:133-175`
  - `services/tool_pool_api/src/tool_pool_api/core/config.py:31-33`
  - `supabase/functions/google-oauth-start/index.ts:59` (RPC `get_platform_google_oauth_config`)
- Estado atual relevante:
  - `google_oauth_config` está no Vault (secret_id já conhecido no handoff).
  - Ainda existe fallback `.env` para segredo dev (`MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV`).
- Rotação:
  1) Rotacionar secret no Google Cloud Console.
  2) Atualizar `google_oauth_config` no Vault (`vault.update_secret` no DB).
  3) Eliminar fallback `.env` no `tool_pool_api` (migrar para Vault/Secret Manager).
  4) Redeploy e smoke do fluxo OAuth.
- Blast radius:
  - Alto: comprometimento do OAuth app e abuso de fluxo de autenticação.

### 7) Tokens LLM
- Segredos cobertos:
  - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `HF_TOKEN`, `CO_API_KEY`, `OLLAMA_CLOUD_API_KEY`.
- Onde são lidos:
  - `libs/blu_llm_service/src/blu_llm_service/config.py:31-65`
  - `libs/blu_llm_service/src/blu_llm_service/client.py:245,268,291,332`
  - `supabase/functions/process-document/index.ts:72,78`
- Rotação:
  1) Rotacionar por provedor (OpenAI/Anthropic/Google/HF/Cohere/Ollama).
  2) Atualizar runtime centralizado.
  3) Rodar smoke de geração/embedding/reranker.
- Blast radius:
  - Médio/alto: custo indevido, exfiltração indireta em prompts e indisponibilidade por bloqueio de conta.

### 8) `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (achado anterior 🔴 → mitigado 🟡 em 2026-05-25)
- Propósito:
  - Telemetria/tracing de prompts e execuções.
- Onde é lido:
  - `libs/blu_observability_bootstrap/src/blu_observability_bootstrap/langfuse.py:84-85`
  - `services/agent_api/src/agent_api/config.py:28-29`
- Ação executada (2026-05-25):
  - `scripts/create_analytics_prompts.py`: fallbacks hardcoded removidos; agora exige `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` do ambiente (fail fast).
  - `libs/__init__.py`: chaves comentadas removidas; arquivo passa a documentar apenas as env vars esperadas.
- Pendências de rotação (manuais, executor: Lucas no Langfuse UI):
  1) Rotacionar `LANGFUSE_SECRET_KEY` (a chave completa `sk-lf-734d84c8-…-07396d0d7ee4` foi exposta em `scripts/create_analytics_prompts.py` no histórico do git).
  2) Rotacionar também `LANGFUSE_PUBLIC_KEY` `pk-lf-461b0371-b3d8-4dd1-a043-132366f9cc64` (exposto no mesmo arquivo) e o public key `pk-lf-c64e4914-b8ab-426d-a5ea-14989b564e13` (comentado em `libs/__init__.py`).
  3) Após rotação, atualizar `.env` local e ambientes de runtime; idealmente migrar para Vault/secret manager.
- Blast radius:
  - Alto: escrita/leitura não autorizada de traces, metadados de prompts e observabilidade.

### 9) `POLP_API_SECRET`, `POLP_WEBHOOK_SECRET` e `PLUGGY_WEBHOOK_SECRET`
- Propósito:
  - Autenticação com API Polp e validação de webhook HMAC.
- Onde é lido:
  - `supabase/functions/polp-sync/index.ts:18-19`
  - `supabase/functions/polp-webhook/index.ts:24-26`
  - `services/tool_pool_api/src/tool_pool_api/api/polp_webhook_router.py:43`
- Observação:
  - `POLP_API_SECRET` aparece no `.env`.
  - `POLP_WEBHOOK_SECRET`/`PLUGGY_WEBHOOK_SECRET` não apareceram no `.env` local (provável segredo externo/runtime).
- Rotação:
  1) Rotacionar segredo no painel do provedor Polp/Pluggy.
  2) Atualizar runtime de todos os webhooks/consumidores.
  3) Validar assinatura HMAC recebida após troca.
- Blast radius:
  - Alto: ingestão fraudulenta de eventos financeiros ou abuso de API parceira.

## Outros nomes sensíveis detectados no `.env` (triagem inicial)

Sem leitura de valores; apenas nomes:
- `CONTA_AZUL_CLIENT_SECRET`
- `GRAFANA_API_KEY`
- `LANGCHAIN_API_KEY`
- `QDRANT_API_KEY`
- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_DB_PASSWORD`
- `SUPABASE_JWT_SECRET`
- `TWILIO_AUTH_TOKEN`

Status inicial sugerido: 🟡 (.env only) até migração para Vault/secret manager.

## Próximas ações priorizadas

1. ✅ (2026-05-25) Hardcoded de Langfuse removido de `scripts/create_analytics_prompts.py` e `libs/__init__.py`; rotação das chaves expostas continua pendente no Langfuse UI.
2. 🔴 Finalizar rotação do Google OAuth (`google_oauth_config` no Vault, secret_id conhecido no handoff) e eliminar fallback `MCP_AUTH_GOOGLE_CLIENT_SECRET_DEV` em `.env`.
3. 🟠 Migrar `SUPABASE_SERVICE_KEY`, `SUPABASE_DB_URL`, `CREDENTIALS_ENCRYPTION_KEY` para gestão central segura (Vault/secret manager) com runbook de rotação.
4. 🟠 Consolidar segredos de Polp webhook (`POLP_WEBHOOK_SECRET`/`PLUGGY_WEBHOOK_SECRET`) em fonte única e validar assinatura obrigatória em todos os ingressos.
5. 🟡 Planejar lote 2 de migração para tokens LLM e observabilidade (OpenAI/Anthropic/Google/HF/Cohere/Ollama + Langfuse), com smoke tests por serviço.
