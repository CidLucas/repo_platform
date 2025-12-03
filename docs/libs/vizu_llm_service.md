Lib: `vizu_llm_service`

O que a lib faz
- Fornece abstração para provedores de LLM (Ollama local/cloud, OpenAI, Anthropic, Google) e configura clientes usados por serviços.
- Centraliza configuração de providers, parâmetros de tempo limite, e integração com Langfuse.

Observações técnicas
- Exporta classes/constructors para criar clientes LangChain e wrappers internos.
- Permite selecionar provider via `LLM_PROVIDER` env var ou config.
- Deve padronizar timeouts e retry policy para reduzir latência.

Dependências
- langchain-core (versão compatível usada no repo)
- langchain-ollama (necessário para suporte Ollama)
- requests / httpx (dependendo do adapter usado)

Stack e versões recomendadas
- Python 3.11+
- langchain-core: compatível com projeto (ver `pyproject.toml`) — sugerir 0.0x (ver lockfile do repo)
- ollama client: versão compatível com `langchain-ollama`

Riscos / recomendações
- Risco: incompatibilidades entre versões de langchain e langchain-ollama.
- Recomendações:
  - Lockar versões no `pyproject.toml` e validar via CI.
  - Testar provider alternativos (Cloud vs local) com integrações de fallback e métricas de latência.
  - Centralizar e padronizar instrumentation (Langfuse spans) dentro desta lib para garantir consistência.
