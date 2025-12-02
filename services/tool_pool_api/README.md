# Vizu Tool Pool API

Servidor MCP que expõe ferramentas de RAG e SQL para o `atendente_core`.

## Overview

O Tool Pool API é um servidor FastMCP que atua como repositório central de ferramentas. O `atendente_core` conecta via protocolo MCP e acessa ferramentas como RAG (busca semântica) e SQL Agent.

### Arquitetura

```
┌──────────────────┐          ┌─────────────────┐
│  Atendente Core  │──MCP────▶│  Tool Pool API  │
│  (MCP Client)    │          │  (FastMCP)      │
└──────────────────┘          └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              ┌──────────┐      ┌──────────┐      ┌──────────┐
              │  Qdrant  │      │ Postgres │      │   LLM    │
              │  (RAG)   │      │  (SQL)   │      │ Service  │
              └──────────┘      └──────────┘      └──────────┘
```

### Key Technologies

- **Framework:** FastAPI + FastMCP
- **RAG:** `vizu_rag_factory` + Qdrant
- **SQL:** `vizu_sql_factory` + PostgreSQL
- **LLM:** `vizu_llm_service` (multi-provider)
- **Package Manager:** Poetry

## Ferramentas Expostas

| Tool | Descrição |
|------|-----------|
| `executar_rag_cliente` | Busca semântica na base de conhecimento do cliente |
| `executar_sql_agent` | Executa queries SQL via agente LLM |
| `ferramenta_publica_de_teste` | Tool de teste/exemplo |

## Configuração

### Variáveis de Ambiente

```bash
# Banco de dados
DATABASE_URL=postgresql://user:password@postgres:5432/vizu_db

# Qdrant (RAG)
QDRANT_URL=http://qdrant_db:6333

# Embedding Service
EMBEDDING_SERVICE_URL=http://embedding_service:11435

# LLM Provider
LLM_PROVIDER=ollama_cloud
OLLAMA_CLOUD_API_KEY=sua-chave
OLLAMA_CLOUD_BASE_URL=https://api.ollama.com/v1
OLLAMA_CLOUD_DEFAULT_MODEL=gpt-oss:20b
```

## Desenvolvimento

### Rodar Localmente (via Docker Compose)

```bash
# Da raiz do monorepo
make up
make logs s=tool_pool_api
```

### Verificar MCP

```bash
# Ver logs de conexão MCP
docker compose logs atendente_core | grep -i mcp
```

### Estrutura do Código

```
src/tool_pool_api/
├── main.py           # FastAPI + FastMCP server
├── tools/
│   ├── rag_tool.py   # Implementação da tool RAG
│   ├── sql_tool.py   # Implementação do SQL Agent
│   └── test_tool.py  # Tool de teste
└── config.py         # Configurações
```

## Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| * | `/mcp/` | Endpoint MCP (SSE transport) |
| GET | `/health` | Health check |

### Porta

- Container interno: `9000`
- Host mapeado: `8006`
