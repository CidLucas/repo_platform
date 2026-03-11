# Vizu LLM Service Client

Biblioteca centralizada para roteamento e instanciação de LLMs com suporte a múltiplos providers.

## Providers Suportados

| Provider | Tipo | Configuração |
|----------|------|--------------|
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
# Provider padrão: ollama_cloud, openai, anthropic, google
LLM_PROVIDER=ollama_cloud

# Ollama Cloud (https://ollama.com/settings/keys)
OLLAMA_CLOUD_API_KEY=your-api-key
OLLAMA_CLOUD_BASE_URL=https://ollama.com

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
GOOGLE_API_KEY=AIza...
```

## Model Tiers

| Tier | Ollama Cloud | OpenAI | Anthropic | Google |
|------|--------------|--------|-----------|--------|
| `FAST` | gpt-oss:20b | gpt-4o-mini | claude-3-5-haiku | gemini-1.5-flash |
| `DEFAULT` | gpt-oss:20b | gpt-4o-mini | claude-3-5-sonnet | gemini-1.5-flash |
| `POWERFUL` | deepseek-v3.1:671b | gpt-4o | claude-3-5-sonnet | gemini-1.5-pro |

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
