CHANGELOG — sessão: 2025-12-02

Resumo das mudanças aplicadas nesta sessão

- Segurança e tool schema
  - RAG tool: adicionado `_rag_tool_wrapper` em `services/tool_pool_api` para expor apenas `query` ao LLM e aceitar `cliente_id` somente internamente.
  - `execute_tools_node` (em `services/atendente_core`) modificado para nunca confiar em `cliente_id` vindo do LLM; o `cliente_id` agora é injetado pelo servidor a partir de `_internal_context`.

- Paralelização e performance
  - `execute_tools_node` refatorado para executar múltiplas chamadas de ferramenta em paralelo usando `asyncio.gather` (reduz latência de fluxo quando múltiplas ferramentas são chamadas).

- Dependências e ambiente
  - Corrigida dependência `langchain-ollama` no `tool_pool_api` (Poetry/pyproject). Conteinerizado reconstruído.
  - Variáveis de LLM adicionadas ao `docker-compose.yml` (ex.: `LLM_PROVIDER`, `OLLAMA_CLOUD_*`).

- Persistência de estado
  - `add_messages` usado como reducer de sessão em vez de nome de string, corrigindo perda de mensagens no state/graph (LangGraph + RedisSaver).

- Automação e testes
  - `Makefile`: novo target `batch-run` criado e documentado; apontado para executar `scripts/batch_run.py` dentro do container `vizu_atendente_core` para evitar erro PEP-668 no macOS.
  - `scripts/batch_run.py` tornado container-aware (seleciona endpoint interno `http://localhost:8000/chat` quando executado dentro do container; host usa `http://localhost:8003/chat`).
  - Batch-run executado com sucesso (10/10 mensagens), traços enviados ao Langfuse local.

- Observability
  - Langfuse host configurado para local (`http://host.docker.internal:3000`) para rastreamento em dev.

- Documentação
  - Atualizados: `README.md` (root), `services/atendente_core/README.md`, `services/tool_pool_api/README.md`, e `.github/copilot-instructions.md` com notas e recomendações.

Notas adicionais
- Pydantic deprecations: há aviso relacionado a uso de classe `Config` — recomenda-se migrar para `ConfigDict` (vizu_auth) para evitar warnings futuros.
- Próximas ações recomendadas: auditoria de dependências entre `libs/`, adicionar CI para verificar `poetry.lock`/paridade entre serviços, testes unitários para `execute_tools_node` e wrapper RAG.
