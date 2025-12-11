# Vizu Atendente Core

Orquestrador principal de IA conversacional da plataforma Vizu.

## Overview

O Atendente Core é uma aplicação FastAPI que orquestra a lógica conversacional usando LangGraph. Ele integra com o `tool_pool_api` via MCP para acessar ferramentas de RAG e SQL.

### Arquitetura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Cliente API   │────▶│  Atendente Core  │────▶│  Tool Pool API  │
│   (X-API-KEY)   │     │   (LangGraph)    │     │     (MCP)       │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
               ┌────────┐  ┌──────────┐  ┌──────────┐
               │ Redis  │  │ Postgres │  │ Langfuse │
               │(memory)│  │ (auth)   │  │ (traces) │
               └────────┘  └──────────┘  └──────────┘
```

### Key Technologies

- **Framework:** FastAPI
- **Conversational AI:** LangChain, LangGraph
- **LLM:** Multi-provider via `vizu_llm_service` (Ollama, OpenAI, Anthropic)
- **Tools:** FastMCP client conectando ao `tool_pool_api`
- **Memory:** Redis (RedisSaver para checkpoints do LangGraph)
- **Database:** PostgreSQL (autenticação de clientes)
- **Observability:** Langfuse (traces de LLM)
- **Package Manager:** Poetry

## Configuração

### Variáveis de Ambiente

```bash
# Banco de dados
DATABASE_URL=postgresql://user:password@postgres:5432/vizu_db

# Redis (memória de sessão)
REDIS_URL=redis://redis:6379/0

# LLM Provider
LLM_PROVIDER=ollama_cloud  # ou: ollama, openai, anthropic
OLLAMA_CLOUD_API_KEY=sua-chave

# MCP (Tool Pool)
MCP_SERVER_URL=http://tool_pool_api:9000/mcp/

# Langfuse (observabilidade)
LANGFUSE_HOST=http://host.docker.internal:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

## Desenvolvimento

### Rodar Localmente (via Docker Compose)

```bash
# Da raiz do monorepo
make up
make logs s=atendente_core
```

### Testar Endpoint

```bash
# Teste rápido
make chat

# Batch de mensagens (gera traces Langfuse)
make batch-run
```

### Estrutura do Código

```
src/atendente_core/
├── main.py           # FastAPI app e endpoints
├── core/
│   ├── graph.py      # LangGraph workflow
│   ├── state.py      # AgentState (TypedDict)
│   └── nodes.py      # Nós do grafo (agent, tools)
├── auth/             # Autenticação via X-API-KEY
└── mcp/              # Cliente MCP para tool_pool_api
```

## Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/chat` | Enviar mensagem (requer X-API-KEY) |
| GET | `/health` | Health check |

### Exemplo de Request

```bash
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: sua-api-key" \
  -d '{"message": "Olá!", "session_id": "test-123"}'
```