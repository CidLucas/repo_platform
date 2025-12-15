# a partir da raiz do repo
python -m pip install --user --upgrade pip
python -m pip install --user poetry
projects=$(git ls-files -- '**/pyproject.toml' | sed 's|/pyproject.toml||' | sort -u)
for p in $projects; do
  echo "Checking $p"
  pushd "$p"
  poetry config virtualenvs.in-project true
  poetry install --no-interaction --no-ansi --no-dev
  poetry lock --no-update || true
  if git status --porcelain -- poetry.lock | grep -q .; then
    echo "poetry.lock inconsistent in $p"
  else
    echo "OK $p"
  fi
  popd
done# a partir da raiz do repo
python -m pip install --user --upgrade pip
python -m pip install --user poetry
projects=$(git ls-files -- '**/pyproject.toml' | sed 's|/pyproject.toml||' | sort -u)
for p in $projects; do
  echo "Checking $p"
  pushd "$p"
  poetry config virtualenvs.in-project true
  poetry install --no-interaction --no-ansi --no-dev
  poetry lock --no-update || true
  if git status --porcelain -- poetry.lock | grep -q .; then
    echo "poetry.lock inconsistent in $p"
  else
    echo "OK $p"
  fi
  popd
done# Tool Pool API - MCP Interface Documentation

> **Versão:** 1.0.0
> **Endpoint SSE:** `http://tool_pool_api:9000/mcp/sse`
> **Protocolo:** Model Context Protocol (MCP) via Server-Sent Events

---

## Visão Geral

O Tool Pool API expõe capacidades de IA através do protocolo MCP, permitindo que agentes (como o `atendente_core`) descubram e utilizem:

- **Tools**: Ações executáveis (busca RAG, consultas SQL)
- **Resources**: Dados read-only (knowledge base, configurações)
- **Prompts**: Templates de prompt versionados e parametrizados

---

## Tools

### `executar_rag_cliente`

Busca informações na base de conhecimento do cliente usando RAG (Retrieval Augmented Generation).

**Quando usar:**
- Perguntas sobre produtos, serviços e preços
- FAQ e dúvidas frequentes
- Políticas e procedimentos da empresa
- Qualquer informação do negócio

**Parâmetros:**
| Nome | Tipo | Obrigatório | Descrição |
|------|------|-------------|-----------|
| `query` | string | ✅ | Pergunta do cliente |
| `cliente_id` | string | ⚠️ | ID do cliente (injetado automaticamente pelo agente) |

**Retorno:** String com a resposta gerada pelo LLM baseada no contexto recuperado.

**Exemplo:**
```json
{
  "name": "executar_rag_cliente",
  "arguments": {
    "query": "Quais serviços de coloração vocês oferecem?"
  }
}
```

---

### `executar_sql_agent`

Consulta dados estruturados do banco de dados do cliente.

**Quando usar:**
- Consulta de pedidos e histórico
- Verificação de estoque
- Dados transacionais

**Parâmetros:**
| Nome | Tipo | Obrigatório | Descrição |
|------|------|-------------|-----------|
| `query` | string | ✅ | Consulta em linguagem natural |
| `cliente_id` | string | ⚠️ | ID do cliente (injetado automaticamente) |

**Retorno:** Dict com resultado da consulta SQL.

---

### `ferramenta_publica_de_teste`

[USO INTERNO] Ferramenta de diagnóstico para testes.

**Parâmetros:**
| Nome | Tipo | Obrigatório | Descrição |
|------|------|-------------|-----------|
| `nome` | string | ✅ | Nome para teste |

---

## Resources

Resources são endpoints read-only que expõem dados sem executar ações.

### Knowledge Base

#### `knowledge://summary`
Resumo da base de conhecimento do cliente autenticado.

**Retorno:** Markdown com informações da coleção (nome, quantidade de documentos, status).

---

#### `knowledge://{cliente_id}/summary`
Resumo da base de conhecimento de um cliente específico.

**Parâmetros:**
| Nome | Tipo | Descrição |
|------|------|-----------|
| `cliente_id` | UUID | ID do cliente Vizu |

**Retorno:** Markdown com informações da coleção.

---

#### `knowledge://{cliente_id}/search/{query}`
Busca documentos na base de conhecimento (retorna documentos brutos, sem LLM).

**Parâmetros:**
| Nome | Tipo | Descrição |
|------|------|-----------|
| `cliente_id` | UUID | ID do cliente |
| `query` | string | Texto de busca |

**Retorno:** Markdown com os documentos encontrados.

**Diferença do Tool `executar_rag_cliente`:**
- Resource: Retorna documentos brutos (sem processamento LLM)
- Tool: Processa com LLM e retorna resposta elaborada

---

### Client Configuration

#### `config://client`
Configuração do cliente autenticado via JWT.

**Retorno:** Markdown com nome, horários, ferramentas habilitada

---

#### `config://{cliente_id}/settings`
Configuração de um cliente específico.

**Parâmetros:**
| Nome | Tipo | Descrição |
|------|------|-----------|
| `cliente_id` | UUID | ID do cliente |

**Retorno:** Markdown com todas as configurações do cliente.

---

#### `config://{cliente_id}/prompt`
Prompt personalizado do cliente.

**Parâmetros:**
| Nome | Tipo | Descrição |
|------|------|-----------|
| `cliente_id` | UUID | ID do cliente |

**Retorno:** Prompt base configurado (ou mensagem indicando que não há prompt personalizado).

---

## Prompts

Prompts são templates versionados que podem ser solicitados e usados pelo agente.

### System Prompts

#### `atendente/system/v1`
System prompt básico do atendente.

**Parâmetros:**
| Nome | Tipo | Default | Descrição |
|------|------|---------|-----------|
| `nome_empresa` | string | "Vizu" | Nome da empresa |

**Retorno:** Lista de `Message` com role="system".

---

#### `atendente/system/v2`
System prompt completo com contexto do cliente.

**Parâmetros:**
| Nome | Tipo | Descrição |
|------|------|-----------|
| `cliente_id` | UUID | ID do cliente Vizu |

**Retorno:** Lista de `Message` incluindo:
- Nome da empresa
- Prompt personalizado (se configurado)
- Horários de funcionamento

---

### Action Prompts

#### `atendente/confirmacao-agendamento`
Prompt para confirmar dados de agendamento.

**Parâmetros:**
| Nome | Tipo | Descrição |
|------|------|-----------|
| `data` | string | Data do agendamento (ex: "15/01/2025") |
| `horario` | string | Horário (ex: "14:30") |
| `servico` | string | Nome do serviço |

---

#### `atendente/esclarecimento`
Prompt para solicitar esclarecimento ao cliente.

**Parâmetros:**
| Nome | Tipo | Descrição |
|------|------|-----------|
| `pergunta` | string | Pergunta original do cliente |
| `opcoes` | string | Opções possíveis (uma por linha) |

---

### RAG Prompts

#### `rag/query`
Prompt para responder baseado em contexto RAG.

**Parâmetros:**
| Nome | Tipo | Descrição |
|------|------|-----------|
| `context` | string | Documentos recuperados |
| `question` | string | Pergunta do usuário |

---

## Autenticação

### Via JWT (Chamada Direta)
O cliente MCP deve enviar um token JWT válido. O `sub` claim é usado para identificar o usuário externo e mapear para o `cliente_id` interno.

### Via cliente_id (Túnel Persistente)
Quando o `atendente_core` chama as tools, ele injeta o `cliente_id` nos argumentos. Isso é feito de forma segura usando o `_internal_context` que não é exposto ao LLM.

---

## Exemplos de Uso

### Python (langchain-mcp-adapters)

```python
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools

async def main():
    async with sse_client("http://localhost:8006/mcp/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Carregar tools
            tools = await load_mcp_tools(session)

            # Listar resources
            resources = await session.list_resources()

            # Ler um resource
            content = await session.read_resource("config://client")

            # Obter um prompt
            prompt = await session.get_prompt(
                "atendente/system/v2",
                arguments={"cliente_id": "uuid-do-cliente"}
            )
```

### Curl (Debug)

```bash
# Conectar ao SSE
curl -N http://localhost:8006/mcp/sse

# Os comandos MCP são enviados via o protocolo SSE
```

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        tool_pool_api                             │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐    │
│   │                     FastMCP Server                      │    │
│   │                                                          │    │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │    │
│   │  │  Tools   │  │ Resources│  │  Prompts │              │    │
│   │  │          │  │          │  │          │              │    │
│   │  │ • RAG    │  │ • KB     │  │ • System │              │    │
│   │  │ • SQL    │  │ • Config │  │ • Action │              │    │
│   │  │ • Test   │  │ • Prompt │  │ • RAG    │              │    │
│   │  └──────────┘  └──────────┘  └──────────┘              │    │
│   │                                                          │    │
│   └────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼ SSE (/mcp/sse)                   │
│   ┌────────────────────────────────────────────────────────┐    │
│   │                    FastAPI Server                       │    │
│   │                     :8006 (ext)                         │    │
│   │                     :8000 (int)                         │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Changelog

### v1.0.0 (2025-12-01)
- ✅ 3 Tools registradas (RAG, SQL, Test)
- ✅ 6 Resources (knowledge x3, config x3)
- ✅ 5 Prompts (system x2, action x2, rag x1)
- ✅ Autenticação via JWT e cliente_id injection
