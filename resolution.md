# Resolution Document — Issue #32: Política de Retenção e Prune

> Design decisions, answered questions, and implementation strategy.
> Author: factory-planner | Date: 2026-06-19

## Decision Resolution

### D1 — Hard-delete vs Soft-delete (archival)
**Decisão: Soft-delete com archival de 90 dias, depois hard-delete em segundo estágio.**

Racional:
- Curated=true records representam conhecimento validado pelo usuário — deletar sem rastro é arriscado (R4).
- Curated=false records podem ser hard-deleted imediatamente ao expirar — são não confirmados, TTL é o contrato.
- Dois estágios: (1) prune diário → archived_at em curated=true expirados, hard-delete em curated=false; (2) prune mensal → hard-delete de registros com archived_at > 90 dias.
- Ferramentas de restore/list_archived permitem recuperação.

### D2 — TTL tiers fixos vs configuráveis
**Decisão: Fixos para MVP, configuráveis por client_config no futuro.**

Tiers definidos:
| # | Condição | TTL | Justificativa |
|---|----------|-----|---------------|
| 1 | curated=true | ∞ (permanente) | Confirmado pelo usuário — conhecimento validado |
| 2 | source=manual/migration/system | 90 dias | Dados de onboarding, migração, sistema — estáveis |
| 3 | source=specialist | 30 dias | Inferências de specialist — revisão mensal |
| 4 | source=memory_agent + confidence≥0.7 | 14 dias | Agente com alta confiança — revisão quinzenal |
| 5 | source=memory_agent + confidence<0.7 | 7 dias | Agente com baixa confiança — revisão semanal |

### D3 — Limite de 50 registros por entidade
**Decisão: 50 registros por (client_id, entity_type, entity_name). Trigger BEFORE INSERT.**

Racional:
- Cada fact é um par (key, value). Entidade típica: 5-15 facts. 50 é ~3-10x margem.
- Trigger SQL é mais seguro que tool layer — independe de qual caminho insere (R2 mitigado com subquery atômica).
- Política de descarte: quando limite é atingido, arquivar (archived_at=now()) o registro mais antigo (created_at ASC) com curated=false. Se todos forem curated=true, rejeitar insert com erro.

### D4 — Prune via Routine Engine vs pg_cron
**Decisão: Routine Engine (system routine com cron trigger).**

Racional:
- Routine Engine já tem: registry de funções, logging, monitoramento, cron trigger.
- `memory.write_dimension_state` já existe como função registrada no namespace `memory.*`.
- pg_cron exigiria security definer function separada + configuração externa.
- Consistência: todo job batch no Blu usa Routine Engine.

### D5 — Notificação ao cliente sobre prune
**Decisão: Operação silenciosa. Apenas log interno + alerta se >100 registros afetados.**

Racional:
- Prune de 1-5 registros por dia é rotina normal — não justifica notificação.
- Alerta only se volume anômalo (>100) indicar possível bug ou expurgo em massa.
- Log via `logger.info` com métricas (deleted_count, archived_count).

### D6 — Trigger SQL vs verificação na tool layer
**Decisão: Trigger BEFORE INSERT no SQL para volume limit. Tool layer não precisa verificar.**

Racional:
- Trigger SQL é atômico e independe do caminho de insert (tool, routine, migration, SQL direto).
- Subquery com `SELECT COUNT(*)` dentro do trigger garante atomicidade (R2).
- Tool layer não precisa de lógica duplicada.

### D7 — Onboarding snapshots e TTL
**Decisão: Snapshots de onboarding usam source=migration → TTL 90 dias, curated=false.**

Racional:
- Dados de onboarding são estáveis (nome, endereço, segmento).
- curated=false até confirmação no morning_plan (Fase 2.4 do roadmap).
- TTL 90 dias dá tempo suficiente para o ciclo de confirmação.

## Conflict Detection

### Conflict 1 — Migration timing
**Situação:** A migration base 20260619000000 está em proposed/, NÃO aplicada.
**Resolução:** Incorporar colunas lifecycle (expires_at, curated, archived_at) DIRETAMENTE na migration base em vez de criar ALTER TABLE separado. A migration 20260620000000 deve ser um ALTER TABLE apenas se a base já tiver sido aplicada. Verificar com o humano.

### Conflict 2 — shared_memory_read ausente
**Situação:** TOOL_INVENTORY lista shared_memory_list/link/unlink/get_links mas NÃO shared_memory_read/write. Issues anteriores (#11, #15) referenciam-nas.
**Resolução:** As tools de archival (restore_archived, list_archived) dependem de shared_memory_read existir. Verificar status antes de implementar.

### Conflict 3 — Prune vs Backup schedule
**Situação:** Backup (#37) deve rodar 02:00. Prune roda 03:00.
**Resolução:** Schedule do prune deve verificar se backup da noite foi concluído (query last_backup_at). Se backup falhou, skip prune e alertar.

### Conflict 4 — Volume limit race condition
**Situação:** Trigger BEFORE INSERT com COUNT(*) pode ter race condition em inserts concorrentes (R2).
**Resolução:** Usar `SELECT COUNT(*) FROM shared_business_memory WHERE ... FOR UPDATE` dentro do trigger para lock de linha. Alternativa: advisory lock pg_try_advisory_lock().

## Implementation Pipeline (6 steps → 3 delivery units)

### Delivery Unit 1: Design Doc + Migration (factory-coder)
- **Step 1:** Seção T4.4 no SHARED_MEMORY_DESIGN.md (criar arquivo + seção completa)
- **Step 2:** Migration SQL com colunas lifecycle + índices + trigger volume limit

### Delivery Unit 2: Prune Job + Routine (factory-coder)
- **Step 3:** Função memory.prune_expired_shared_memory em routine_functions.py
- **Step 4:** Rotina system shared_memory_prune (cron 03:00) + TOOL_INVENTORY update

### Delivery Unit 3: Archival Tools + Integration (factory-coder)
- **Step 5:** Tools shared_memory_restore_archived + shared_memory_list_archived
- **Step 6:** Integração com T5.3 (versionamento) + T5.5 (backup)

## Open Questions for Human Review

1. A migration base 20260619000000 ainda não foi aplicada. Incorporar as colunas lifecycle diretamente nela, ou criar migration incremental separada?
2. shared_memory_read e shared_memory_write existem ou precisam ser criadas primeiro?
3. Limite de 50 registros por entidade: adequado ou ajustar?
4. Alerta de prune anômalo (>100 registros): para onde? Slack? Telegram? Apenas log?
