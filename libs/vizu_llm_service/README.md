# Vizu LLM Service Client

Biblioteca centralizada para roteamento e instanciação de LLMs com suporte a múltiplos providers.

## Providers Suportados

| Provider | Tipo | Configuração |
|----------|------|--------------|
| `ollama` | Local | `OLLAMA_BASE_URL` (container) |
| `ollama_cloud` | Cloud | `OLLAMA_CLOUD_API_KEY` |
| `openai` | Cloud | `OPENAI_API_KEY` |
| `anthropic` | Cloud | `ANTHROPIC_API_KEY` |
| `google` | Cloud | `GOOGLE_API_KEY` |

## Uso Rápido

```python
from vizu_llm_service import get_model, LLMProvider, ModelTier

# Usar provider padrão (definido em LLM_PROVIDER)
model = get_model()

# Usar Ollama Cloud explicitamente
model = get_model(provider=LLMProvider.OLLAMA_CLOUD)

# Usar modelo mais poderoso
model = get_model(tier=ModelTier.POWERFUL)

# Usar modelo específico
model = get_model(provider=LLMProvider.OPENAI, model_name="gpt-4-turbo")
```

## Configuração via .env

```bash
# Provider padrão: ollama, ollama_cloud, openai, anthropic, google
LLM_PROVIDER=ollama

# Ollama Local (container)
OLLAMA_BASE_URL=http://ollama_service:11434

# Ollama Cloud (https://ollama.com/account)
OLLAMA_CLOUD_API_KEY=sua-api-key
OLLAMA_CLOUD_BASE_URL=https://api.ollama.com/v1
OLLAMA_CLOUD_DEFAULT_MODEL=llama3.2

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
GOOGLE_API_KEY=AIza...
```

## Model Tiers

| Tier | Ollama Local | Ollama Cloud | OpenAI | Anthropic |
|------|--------------|--------------|--------|-----------|
| `FAST` | phi3:mini | llama3.2 | gpt-4o-mini | claude-3-5-haiku |
| `DEFAULT` | llama3.2:latest | llama3.2 | gpt-4o-mini | claude-3-5-sonnet |
| `POWERFUL` | llama3.1:70b | llama3.3 | gpt-4o | claude-3-5-sonnet |

## Langfuse (Observabilidade)

```python
from vizu_llm_service import get_model

# Langfuse é ativado automaticamente se as variáveis estiverem configuradas
# LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

model = get_model(
    user_id="user-123",
    session_id="session-456",
    tags=["atendente", "rag"]
)
```

## Embeddings

```python
from vizu_llm_service import get_embedding_model

embeddings = get_embedding_model()
vectors = embeddings.embed_documents(["texto 1", "texto 2"])
query_vector = embeddings.embed_query("pergunta do usuário")
```

## Desenvolvimento

### Key Technologies

*   **LLM Interaction:** LangChain
*   **HTTP Client:** requests
*   **Package Manager:** Poetry
