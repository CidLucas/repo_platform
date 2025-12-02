# Sessão de Troubleshooting - Sistema Vizu RAG + MCP
**Data:** 02/12/2025
**Objetivo:** Fazer o sistema completo funcionar (prompts, RAG, LLM) e rodar batch de testes para gerar traces no Langfuse

---

## 1. CONTEXTO GERAL

### O que é o sistema
O **vizu-mono** é um monorepo com múltiplos serviços:
- **atendente_core** (porta 8003): Orquestra conversas, conecta-se ao MCP para tools
- **tool_pool_api** (porta 8006→9000 interno): Servidor MCP que expõe ferramentas (RAG, SQL, etc)
- **ollama_service** (porta 11434): LLM local ou proxy para Ollama Cloud
- **postgres** (porta 5432): Banco de dados principal
- **qdrant** (porta 6333): Vector database para RAG
- **redis** (porta 6379): Cache e estado

### Arquitetura MCP implementada
```
┌─────────────────────────────────────────────────────────────────────┐
│                         LANGFUSE CLOUD                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐   │
│  │   Prompts   │  │  Datasets   │  │ Experiments │  │  Scores  │   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      atendente_core:8003                             │
│  - Recebe mensagens do usuário via /chat                            │
│  - Conecta ao tool_pool_api via MCP (HTTP Streamable)               │
│  - Usa LLM (Ollama) para decidir quando chamar tools                │
│  - Orquestra fluxo de conversa                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      tool_pool_api:9000                              │
│  - Servidor MCP com ferramentas:                                    │
│    • executar_rag_cliente: Busca knowledge base no Qdrant          │
│    • executar_sql_agent: Queries no banco                           │
│    • ferramenta_publica_de_teste: Tool de teste                     │
│  - Filtra tools por cliente (via config no banco)                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. O QUE JÁ FOI FEITO NESTA SESSÃO

### 2.1 Arquitetura Langfuse-First (COMPLETO ✅)

Implementamos uma arquitetura onde o Langfuse é a fonte de verdade:

1. **PromptService** (`libs/vizu_llm_service/src/vizu_llm_service/prompt_service.py`)
   - Busca prompts do Langfuse primeiro
   - Cache em memória (TTL 5 min)
   - Fallback para banco de dados local
   - Classes: `PromptService`, `LangfusePromptClient`, `PromptCacheDB`, `FetchedPrompt`

2. **LangfuseExperimentRunner** (`libs/vizu_experiment_service/src/vizu_experiment_service/langfuse_runner.py`)
   - Usa SDK nativo `langfuse.run_experiment()`
   - `ManifestSyncer`: Sincroniza YAML → Langfuse Datasets
   - `AtendenteEvaluators`: Avaliadores customizados (tool_assertion, contains_assertion)

3. **HITL Langfuse Integration** (`libs/vizu_hitl_service/src/vizu_hitl_service/langfuse_integration.py`)
   - `score_trace()`: Adiciona scores aos traces quando review aprovado
   - `sync_pending_to_langfuse()`: Sync em batch de reviews pendentes
   - `create_evaluation_dataset()`: Cria dataset de avaliação por sampling

4. **CLI atualizado** (`libs/vizu_experiment_service/src/vizu_experiment_service/cli.py`)
   - Comando `sync`: Sincroniza manifests YAML → Langfuse
   - Flag `--legacy`: Usa runner httpx antigo

### 2.2 Fix da dependência langchain-ollama (COMPLETO ✅)

**Problema encontrado:**
```
ERROR: No module named 'langchain_ollama'
```

**Causa:** O `tool_pool_api` não tinha `langchain-ollama` no `poetry.lock`, apesar do `vizu_llm_service` ter essa dependência.

**Solução aplicada:**
```bash
cd services/tool_pool_api && poetry lock
docker compose build tool_pool_api
docker compose up tool_pool_api -d
```

**Status:** Container reconstruído e rodando, dependência instalada.

---

## 3. O QUE ESTÁ BLOQUEANDO AGORA

### 3.1 Autenticação no atendente_core

Ao tentar testar o endpoint `/chat`:
```bash
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-api-key-12345" \
  -d '{"client_id":"studio_j","thread_id":"test-123","message":"Quais servicos?"}'
```

**Resposta:**
```json
{"detail":"Invalid or expired API key"}
```

**Tentativas de descobrir o usuário do banco:**
```bash
docker compose exec postgres psql -U postgres -d vizudb  # FATAL: role "postgres" does not exist
docker compose exec postgres psql -U vizu -d vizudb     # FATAL: role "vizu" does not exist
docker compose exec postgres psql -U devuser -d vizudb  # FATAL: role "devuser" does not exist
```

**Próximo passo necessário:**
1. Descobrir o usuário correto do Postgres (olhar docker-compose.yml ou .env)
2. Buscar API keys válidas na tabela `api_keys`
3. Ou criar uma nova API key de teste

---

## 4. VERIFICAÇÕES PENDENTES

### 4.1 Verificar credenciais do Postgres
```bash
# Opção 1: Verificar docker-compose.yml
grep -A5 "postgres:" docker-compose.yml

# Opção 2: Verificar variáveis de ambiente
docker compose exec postgres env | grep POSTGRES

# Opção 3: Entrar no container e verificar
docker compose exec postgres cat /etc/passwd | grep postgres
```

### 4.2 Buscar/Criar API Key
```bash
# Depois de descobrir o usuário correto:
docker compose exec postgres psql -U <USER> -d vizudb -c "SELECT * FROM api_keys;"

# Ou criar uma nova:
docker compose exec postgres psql -U <USER> -d vizudb -c "
INSERT INTO api_keys (key, client_id, is_active, created_at)
VALUES ('test-key-2024', 'studio_j', true, NOW())
RETURNING *;
"
```

### 4.3 Testar endpoint com key válida
```bash
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: <KEY_VALIDA>" \
  -d '{"client_id":"studio_j","thread_id":"test-123","message":"Quais servicos voces oferecem?"}'
```

### 4.4 Verificar logs após teste
```bash
docker compose logs atendente_core --tail=50
docker compose logs tool_pool_api --tail=50
```

---

## 5. VALIDAÇÕES NECESSÁRIAS (CHECKLIST)

Uma vez que a autenticação funcione, validar:

- [ ] **Prompt retrieval**: Verificar nos logs se prompt está sendo buscado do banco/Langfuse
  - Log esperado: `"Usando prompt do banco de dados para Studio J"`

- [ ] **Tool selection**: Verificar se LLM está escolhendo ferramentas corretas
  - Log esperado: `"LLM escolheu chamar tools: ['executar_rag_cliente']"`

- [ ] **RAG execution**: Verificar se RAG executa sem erros
  - Log esperado: `"[RAG] Query executada com sucesso"`
  - Sem erro: `"No module named 'langchain_ollama'"` (já corrigido)

- [ ] **Context usage**: Verificar se resposta usa contexto do RAG
  - A resposta deve conter informações específicas do knowledge base do cliente

- [ ] **Langfuse traces**: Verificar se traces aparecem no Langfuse
  - Acesse: https://cloud.langfuse.com
  - Verifique se há traces com tool calls

---

## 6. APÓS SISTEMA FUNCIONANDO: BATCH RUN

Quando todas as validações passarem, executar batch run para gerar traces:

### 6.1 Opção A: Usando script batch_run.py existente
```bash
cd ferramentas/evaluation_suite
poetry run python batch_run.py \
  --manifest workflows/atendente/manifest.yaml \
  --output results/batch_2024_12_02.json
```

### 6.2 Opção B: Usando CLI do experiment_service (novo)
```bash
# Primeiro sincronizar manifest para Langfuse
cd libs/vizu_experiment_service
poetry run python -m vizu_experiment_service.cli sync \
  --manifest ../ferramentas/evaluation_suite/workflows/atendente/manifest.yaml

# Depois rodar experimento via Langfuse SDK
poetry run python -m vizu_experiment_service.cli run \
  --dataset atendente-manifest \
  --experiment-name "baseline-2024-12-02"
```

### 6.3 Opção C: Chamadas manuais para gerar traces
```bash
# Loop simples com diferentes perguntas
for msg in \
  "Quais servicos voces oferecem?" \
  "Quanto custa um corte de cabelo?" \
  "Qual o horario de funcionamento?" \
  "Quero agendar um horario para amanha"; do

  curl -X POST http://localhost:8003/chat \
    -H "Content-Type: application/json" \
    -H "X-API-KEY: <KEY_VALIDA>" \
    -d "{\"client_id\":\"studio_j\",\"thread_id\":\"batch-$(date +%s)\",\"message\":\"$msg\"}"

  sleep 2
done
```

---

## 7. ARQUIVOS IMPORTANTES PARA REFERÊNCIA

### Configuração
- `docker-compose.yml` - Definição de todos os serviços
- `services/atendente_core/.env` ou `.env.example` - Variáveis de ambiente
- `services/tool_pool_api/.env` - Variáveis do MCP server

### Código principal
- `services/atendente_core/src/atendente_core/main.py` - Entrypoint do atendente
- `services/atendente_core/src/atendente_core/agent/` - Lógica do agente LLM
- `services/tool_pool_api/src/tool_pool_api/server/tool_modules/rag_module.py` - Implementação RAG

### Libs criadas/modificadas nesta sessão
- `libs/vizu_llm_service/src/vizu_llm_service/prompt_service.py` - **NOVO**
- `libs/vizu_experiment_service/src/vizu_experiment_service/langfuse_runner.py` - **NOVO**
- `libs/vizu_hitl_service/src/vizu_hitl_service/langfuse_integration.py` - **MODIFICADO**

### Documentação
- `Fast_MCP.md` - Documento principal do projeto MCP (atualizado com arquitetura Langfuse-First)

---

## 8. ESTADO DOS CONTAINERS (última verificação)

```
NAME                          STATUS              PORTS
vizu_atendente_core           Up 47 minutes       8003->8000
vizu_tool_pool_api            Up 2 minutes        8006->9000
vizu_ollama_dev               Up 5 hours          11434->11434
vizu_postgres                 Up 2 days           5432->5432
vizu_qdrant_dev               Up 2 days           6333-6334
vizu_redis_dev                Up 2 days           6379->6379
analytics_api                 Up 2 days           8004->8000
vizu_embedding_service        Up 12 hours         11435->11435
```

Todos os containers principais estão **rodando**.

---

## 9. RESUMO EXECUTIVO

### ✅ Concluído
1. Arquitetura Langfuse-First implementada (PromptService, LangfuseExperimentRunner)
2. Fix do `langchain-ollama` no tool_pool_api
3. Containers reconstruídos e rodando

### 🔄 Em progresso
1. **BLOQUEADOR**: Descobrir credenciais do Postgres para buscar API keys

### ⏳ Pendente
1. Testar endpoint /chat com autenticação válida
2. Validar fluxo completo (prompt → tool selection → RAG → response)
3. Verificar traces no Langfuse
4. Rodar batch run para gerar traces de baseline

---

## 10. PRÓXIMA AÇÃO IMEDIATA

```bash
# 1. Descobrir variáveis do Postgres
cat docker-compose.yml | grep -A10 "postgres:"

# 2. Ou verificar .env do projeto
cat .env 2>/dev/null || cat .env.example 2>/dev/null

# 3. Com as credenciais, acessar o banco
docker compose exec postgres psql -U <DESCOBRIR> -d <DESCOBRIR> -c "SELECT * FROM api_keys;"
```
