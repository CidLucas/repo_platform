Resumo executivo

Este documento descreve, de forma concisa, o fluxo de definição, inscrição, disparo, execução e persistência de artefatos das rotinas (routines) no repo_platform, além das dependências técnicas relevantes. Em seguida aprofunda-se em telemetria, políticas RLS e proveniência (provenance) de artefatos, com recomendações práticas. Referências a arquivos de código foram incluídas para auditoria rápida.

1) Visão geral do fluxo

- Definição
  - Catalog (cross_agent_routines): rotinas globais definidas como catálogo, com steps, trigger_type, trigger_config, room, config_schema.
    - Código: services/agent_api/src/agent_api/core/routines.py (fetch_triggered_routines, _fetch_routine_sync)
  - Custom (client_routines): inscrições/overrides por cliente (config, trigger_config, notify_channel, active, last_run_at).
    - Endpoints: services/tool_pool_api/src/.../routines_module.py
    - UI: apps/blu_v3/src/components/shared/RoutineConfigSection.tsx

- Disparo / Agendamento
  - Triggers suportados: cron, numeric, event, manual.
  - Pollers:
    - _check_cron_routines() (croniter) → cria execuções dispatched via _dispatch_execution_sync
    - _check_numeric_triggers() → avalia métricas por cliente e dispara quando necessário
  - DB bridge / filas:
    - Tabela: client_routine_executions (status: pending, dispatched, executing, completed, failed)
    - Funções SQL: claim_routine_executions (batch claim SKIP LOCKED), process_pending_routine_executions, dispatch_routine_executions (migrations/*.sql)

- Execução
  - Workers claim executions via RPC claim_routine_executions e processam steps.
  - Tipos de step:
    - function → chamadas determinísticas (agent_api.core.routine_functions)
    - skill → LangGraph specialist graph via _execute_skill_step (usa MCP manager)
    - artifact → side-effects (email, alert, document, whatsapp) via routine_artifacts
    - legacy (none) → _invoke_worker
  - Estado compartilhado: dict "state" preservado entre steps; checkpoint em client_routine_executions.result_metadata após cada step.
  - Runner manual para debug: services/agent_api/run_routine.py (cria execução 'executing' e imprime trace detalhado).

- Templates e I/O
  - _resolve_templates: suporta pure placeholders ({{key}} → preserva tipo) e mixed strings (interpolação com JSON para dict/list).
  - Saída de LLM/skill: _extract_json_from_text tenta extrair JSON; quando schema unívoco, arrays são embrulhados.
  - _serialisable: filtra/serializa estado antes de gravar.

- Artefatos
  - Artefatos persistidos (documentos/chunks) via storage.save_context_document e rotina em agent_api.core.routine_artifacts
  - process-document Edge Function (supabase/functions/process-document) → chunk + embed + enrich (chamada opcional ao enrich-metadata)
  - enrich-metadata (supabase/functions/enrich-metadata/index.ts) — worker que processa jobs de pgmq e funde metadata extraída (LLM) em vector_db.document_chunks.metadata (SQL UPDATE usando jsonb merge).

2) Dependências técnicas (mais relevantes)

- Banco: Supabase/Postgres
  - Tabelas-chave: cross_agent_routines, client_routines, client_routine_executions, document_chunks (vector_db.document_chunks)
  - Funções/Fila: pgmq queues (metadata_jobs), claim_routine_executions, process_pending_routine_executions
- Serviços/Edge Functions:
  - enrich-metadata (supabase functions) — chama OpenAI, atualiza metadata JSONB
  - process-document — orquestra chunk/embed/enrich
- Agent framework: libs/blu_agent_framework (context_enrichment_node, orchestrator nodes)
- Observability: Langfuse ingestion worker, local logs in EF, and worker logs (enrich-metadata logs com console.log/warn/error)
- Frontend: apps/blu_v3 components + API client (apps/blu_v3/src/api/routines.ts)

3) Telemetria — estado atual e recomendações

Estado atual observado
- enrich-metadata registra progresso via console.log/console.warn/console.error e retorna contadores processed/failed/deadLettered.
  - Arquivo: supabase/functions/enrich-metadata/index.ts (usa OpenAI, valida theme, atualiza vector_db.document_chunks.metadata)
- Langfuse worker (langfuse/worker) enriquece spans/observations com model data; há repositórios para enrichObservationsWithModelData.
- Não vi instrumentação OpenTelemetry explícita nas Edge Functions (enrich-metadata usa console + retries + DLQ).

Recomendações práticas (prioritárias)
- Add structured traces/spans for routine executions and per-step spans
  - Instrumentar engine (services/agent_api/src/agent_api/core/routines.py) com OpenTelemetry spans:
    - root span por execution_id
    - child spans por step (function/skill/artifact)
    - include attributes: client_id, routine_id, step_id, step_type, step_elapsed_ms, step_status
- Correlate LLM calls and model usage to billing telemetry (Langfuse already does some enrichment). Emit observation/span with model_name, prompt_hash, input_tokens, output_tokens, latency, cost_estimate.
- Edge Functions (enrich-metadata & process-document): emit structured logs and spans instead of only console; include jobId, chunk_id, document_id, retryCount, enriched.theme, llm_model
- Capture failure classification: transient vs fatal, and emit metrics for retries and DLQ rates (counter metrics + alerts)
- Persist minimal provenance snapshot with artefatos (ver next section) to allow replay and audit.

4) RLS & segurança — estado e recomendações

Estado atual observado
- RLS nas migrations adiciona política "own client" em client_routine_executions e GRANTs de funções a service_role (migrations/*.sql).
- Supabase functions config (supabase/config.toml) anota enrich-metadata as function; Edge Function usa DB_URL (provavelmente service role) — confirme.

Recomendações
- Verificar quem chama enrich-metadata e process-document: somente service_role / internal jobs devem poder atualizar document_chunks.metadata. Se Edge Function roda com DB_URL de service role, garanta que a função não seja exposta a JWT-anon callers.
- Policies recomendadas (document_chunks):
  - SELECT/UPDATE: permitir apenas rows onde document.client_id = get_my_client_id() para usuários JWT
  - Permitir updates por service_role (roles internas) sem restrição
  - Se artefatos são multi-tenant, validar client_id ao gravar (no código) e aplicar checagem adicional na DB (CHECK client_id matches)
- Harden the pgmq queue triggers: only service_role can enqueue/dequeue certain queues (metadata_jobs), ou filtrar em process-function os jobs sem client_id ou com client mismatch.

5) Proveniência de artefatos (provenance)

Objetivo: para cada artefato (document chunk, email, alert), registrar metadados que permitam auditar quem/como/quando foi gerado e possibilitar replay.

Campos recomendados (document_chunks.metadata top-level + first-class columns quando relevante):
- provenance: {
    routine_id: string | null,
    exec_id: string | null,
    step_id: string | null,
    step_type: "artifact"|"skill"|"function",
    created_by: "routine"|"user"|"manual",
    created_at: ISO8601,
    agent_version: string (git sha / release),
    llm: { model: string, model_version?: string, prompt_hash?: string, prompt_template?: string },
}

Integração com enrich-metadata
- enrich-metadata mescla apenas campos extraídos do conteúdo (theme, word_cloud, usage_context) em document_chunks.metadata.
- Recomendação: garantir que o momento de criação de chunks (process-document / storage.save_context_document) já insira provenance minimal (routine_id, exec_id, step_id, created_at).
  - Rationale: enrich-metadata faz merge posterior; se provenance não existir nos chunks, perda de correlação entre metadata e origem da rotina.
- Implementação: ao salvar documento via routine_artifacts → storage.save_context_document, garantir chamada que cria document_chunks rows com metadata contendo provenance.
- Confirmar pipeline pgmq: process-document → enfileira jobs metadata_jobs para enrich-metadata; enrich-metadata atualiza metadata. Certificar que enrich-metadata NÃO remova campos provenance (o SQL usa jsonb || enriched, que sobrescreve chaves iguais). Evitar colisão de chaves: colocar enriched fields em sub-object (e.g. enriched_metadata) ou garantir merged keys não sobrescrevam provenance.

6) Checklist de ações imediatas (implementáveis)

- [ ] Instrumentar core/routines.py com spans OpenTelemetry (execution + steps) e eventos para LLM calls.
- [ ] Alterar storage.save_context_document (ou lugar onde chunks são criados) para incluir provenance minimal em document_chunks.metadata.
- [ ] Atualizar enrich-metadata para MERGE em campo separado (e.g. metadata->'enrichment') ou document_chunks.metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object('enrichment', enriched)::jsonb — para evitar sobrescrever provenance.
- [ ] Verificar roles: confirmar que enrich-metadata Edge Function usa service_role DB URL; garantir que apenas service_role tem GRANTs para UPDATE em document_chunks
- [ ] Exportar métricas e contadores (DLQ rate, enrichment success per minute, LLM latency) para PostHog / Prometheus / Datadog; ligar alertas em thresholds.

7) Próximos passos sugeridos (escolha)
- A) Eu crio PR com: (1) alteração em process-document/enrich-metadata para gravar enriched under metadata.enrichment, (2) exemplo de provenance payload quando salvar chunks. (Preciso confirmar onde chunks são gerados — indique se quer que eu edite storage/save_context_document ou process-document.)
- B) Eu instrumento routines.py com OpenTelemetry spans e crio teste de integração/local trace.
- C) Fazer uma revisão de RLS policies e gerar SQL patch sugerido para document_chunks e queues (claim/enqueue). 

Referências (arquivos lidos)
- services/agent_api/src/agent_api/core/routines.py
- services/agent_api/run_routine.py
- services/agent_api/src/agent_api/core/routine_artifacts.py
- services/tool_pool_api/src/tool_pool_api/server/tool_modules/routines_module.py
- supabase/functions/enrich-metadata/index.ts
- supabase/functions/process-document/index.ts
- supabase/migrations/* (claim_routine_executions, process_pending_routine_executions, client_routine_executions table)
- libs/blu_agent_framework/src/blu_agent_framework/nodes.py (context_enrichment_node)



