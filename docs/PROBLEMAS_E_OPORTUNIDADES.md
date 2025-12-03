Problemas encontrados e oportunidades de melhoria

Resumo rápido
- Muitos problemas foram resolvidos no fluxo de execução de ferramentas e em automação, porém o repositório ainda tem pontos de fragilidade que merecem atenção e priorização.

Problemas (priorizados)

1) Confiança em dados fornecidos pelo LLM
- Problema: Antes, `execute_tools_node` aceitava `cliente_id` vinda do LLM, criando risco de injeção e autorização incorreta.
- Risco: Exposição de dados sensíveis, execução de ações em nome de clientes errados.
- Mitigação aplicada: servidor agora injeta `cliente_id` a partir de `_internal_context`.
- Recomendação: Adicionar testes de integração que validem que ferramentas rejeitam `cliente_id` não autenticado.

2) Dependências inconsistentes e falta de checagem automática
- Problema: Biblioteca `tool_pool_api` faltava `langchain-ollama` no ambiente, causando falha em runtime até correção manual.
- Risco: Builds quebrados em CI; divergências entre ambientes locais e container.
- Recomendação: Criar pipeline CI que valide `poetry.lock` e rode `poetry install --no-dev` em cada serviço; executar auditoria de versões entre `libs/` e serviços.

3) Execução de scripts no host macOS (PEP-668)
- Problema: `scripts/batch_run.py` quando executado no host tentou instalar pacotes no Python do sistema (PEP-668).
- Mitigação aplicada: `Makefile` ajustado para executar o script dentro do container.
- Recomendação: Documentar claramente qual targets devem rodar in-container; adicionar `make` targets que encapsulam docker exec.

4) Observabilidade / correlação de traces
- Problema: Traços do Langfuse não estavam totalmente correlacionados entre tool_call_id e session_id em todos os paths.
- Recomendação: Garantir spans que incluem `tool_call_id` e `session_id`; instrumentar `execute_tools_node` e o wrapper RAG para propagar identificadores.

5) Avisos de Pydantic e compatibilidade
- Problema: Uso de classe `Config` em alguns módulos (ex.: `vizu_auth`) gera aviso de depreciação.
- Recomendação: Migrar para `ConfigDict` e rodar testes; atualizar documentações e exemplos.

Oportunidades (alto impacto)

- CI de dependências e lockfile: adicionar workflow que verifica paridade de `poetry.lock` e que builds do Docker não falhem por dependência faltante.
- Testes para fluxo de ferramentas: unit + integração cobrindo injeção de `cliente_id`, wrapper RAG e execução paralela com `asyncio.gather`.
- Hardening das ferramentas públicas: criar um lint de schema para ferramentas expostas via MCP (assegurar que parâmetros sensíveis nunca sejam públicos).
- Performance: rastrear latências observadas no batch-run e analisar quais chamadas (LLM vs RAG vs DB) dominam o tempo; considerar paralelismo adicional ou caching.
- Docs e onboarding: consolidar um "Developer Quick Start" (Makefile-first) — já parcialmente implementado.

Plano de mitigação imediato (sugestão)
1. Implementar CI de verificação de dependências (1 week effort).
2. Adicionar testes unitários para `execute_tools_node` e wrapper RAG (1-2 weeks).
3. Instrumentar spans adicionais e garantir correlacionamento em Langfuse (3 days).
4. Migrar Pydantic Configs mais críticos (vizu_auth) (2-3 days).
