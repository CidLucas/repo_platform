# Shared Memory Design — Fase 0 / T2.2

Documento de design do subsistema de memória compartilhada da plataforma BLU.

---

## T2.2 — Templates de Snapshot por Dimensão

### 1. Conceito de Snapshot por Dimensão

Um **snapshot** é um registro estruturado que captura o estado de uma dimensão
de negócio em um momento específico. Diferente de fatos simples (facts), snapshots
são documentos compostos com múltiplos indicadores, alertas e resumo executivo.

Quatro dimensões são suportadas:

| Dimensão     | entity_name         | Descrição                           |
|-------------|---------------------|--------------------------------------|
| financeiro  | `financeiro:{periodo}` | Indicadores financeiros e fluxo de caixa |
| clientes    | `clientes:{periodo}`   | Métricas de base de clientes e CRM |
| agenda      | `agenda:{periodo}`     | Compromissos e follow-ups |
| compras     | `compras:{periodo}`    | Pedidos de compra e inventário |

Períodos válidos: `diario`, `semanal`, `mensal`.

### 2. Schema entity_type / entity_name / key

Para snapshots no `shared_business_memory`:

| Campo        | Valor                              |
|-------------|------------------------------------|
| entity_type | `"snapshot"`                       |
| entity_name | `"{dimensao}:{periodo}"`           |
| key         | timestamp ISO do momento de geração |

Exemplo: `entity_type="snapshot"`, `entity_name="financeiro:semanal"`,
`key="2025-06-19T10:00:00Z"`.

### 3. Templates de Body por Dimensão

Os templates são definidos como constantes em
[`libs/blu_context_service/src/blu_context_service/context_schemas.py`](../../libs/blu_context_service/src/blu_context_service/context_schemas.py)
no dicionário `_SNAPSHOT_DIMENSION_FIELDS`.

#### Body universal (campos base)

Todo snapshot, independente da dimensão, DEVE conter os campos definidos em
`_SNAPSHOT_BASE_FIELDS`:

```python
_SNAPSHOT_BASE_FIELDS = frozenset({
    "snapshot_id",      # UUID único do snapshot
    "dimensao",         # "financeiro" | "clientes" | "agenda" | "compras"
    "periodo",          # "diario" | "semanal" | "mensal"
    "gerado_em",        # Timestamp ISO de geração
    "vigencia_inicio",  # Início do período coberto
    "vigencia_fim",     # Fim do período coberto
    "indicadores",      # Lista de {nome, valor, unidade, tendencia}
    "alertas",          # Lista de strings de alerta
    "resumo_executivo", # Markdown string
})
```

#### Financeiro (`_SNAPSHOT_DIMENSION_FIELDS["financeiro"]`)

Indicadores requeridos (required=True):

- `saldo_atual` (BRL) — Saldo atual em caixa
- `receita_periodo` (BRL) — Receita total no período
- `despesa_periodo` (BRL) — Despesa total no período
- `fluxo_liquido` (BRL) — Fluxo líquido (receita - despesa)

Indicadores opcionais: `contas_a_pagar`, `contas_a_receber`, `inadimplencia_percentual`.

Tendências monitoradas: `receita_tendencia`, `despesa_tendencia`.

Alertas: `estoque_caixa_baixo`, `contas_vencendo_proximos_7d`.

#### Clientes (`_SNAPSHOT_DIMENSION_FIELDS["clientes"]`)

Indicadores requeridos:

- `total_clientes_ativos` (count)
- `novos_clientes_periodo` (count)

Indicadores opcionais: `churn_periodo`, `nps_medio`, `ltv_medio`, `ticket_medio`.

Alertas: `churn_acelerado`, `nps_critico`.

Agrupamentos: `segmentacao`, `status`.

#### Agenda (`_SNAPSHOT_DIMENSION_FIELDS["agenda"]`)

Indicadores requeridos:

- `reunioes_hoje` (count)
- `reunioes_semana` (count)

Indicadores opcionais: `followups_pendentes`, `contatos_a_cobrar`.

#### Compras (`_SNAPSHOT_DIMENSION_FIELDS["compras"]`)

Indicadores requeridos:

- `total_pos_abertas` (count)

Indicadores opcionais: `estoque_critico`, `fornecedores_com_pendencia`, `pedidos_em_analise`.

### 4. Frontmatter Obrigatório

Todo upsert de `entity_type="snapshot"` DEVE incluir frontmatter com os campos
definidos em `_SNAPSHOT_FRONTMATTER_REQUIRED`:

| Campo              | Tipo     | Descrição                                   |
|-------------------|----------|----------------------------------------------|
| tipo              | string   | Sempre `"snapshot"`                          |
| dimensao          | string   | `"financeiro"` / `"clientes"` / `"agenda"` / `"compras"` |
| periodo           | string   | `"diario"` / `"semanal"` / `"mensal"`       |
| gerado_em         | string   | Timestamp ISO de geração                     |
| gerado_por        | string   | Nome do agente ou rotina que gerou           |
| versao            | int      | Número da versão (≥ 1)                      |
| template_version  | int      | Versão do template (≥ 1)                    |
| fontes            | list[str]| Queries/data sources usadas na geração      |

Campos opcionais no frontmatter:

| Campo       | Tipo     | Descrição                                    |
|------------|----------|-----------------------------------------------|
| confianca   | float    | Confiança (0.0–1.0, default 1.0)             |
| ultimo_update | string | Última atualização (ISO timestamp)            |

Validação (T2.2b):
- `_validate_snapshot_frontmatter()` em `memory_module.py` verifica todos os
  campos obrigatórios, cross-valida dimensão e período com `entity_name`.
- Upsert de snapshot sem frontmatter completo é REJEITADO com `ValueError`.

Validação do body (T2.2f):
- `_validate_snapshot_body()` extrai a dimensão do `entity_name`, valida campos
  base, e verifica os indicadores contra o spec da dimensão
  (`_SNAPSHOT_DIMENSION_FIELDS`).
- Indicadores desconhecidos geram WARNING (não erro).
- Indicadores requeridos faltantes geram `ValueError`.

### 5. Exemplos de Uso

#### Upsert via shared_memory_upsert

```json
{
  "entity_type": "snapshot",
  "entity_name": "financeiro:semanal",
  "key": "2025-06-19T10:00:00Z",
  "body": {
    "snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
    "dimensao": "financeiro",
    "periodo": "semanal",
    "gerado_em": "2025-06-19T10:00:00Z",
    "vigencia_inicio": "2025-06-12T00:00:00Z",
    "vigencia_fim": "2025-06-19T00:00:00Z",
    "indicadores": [
      {"nome": "saldo_atual", "valor": 152000, "unidade": "BRL", "tendencia": "estavel"},
      {"nome": "receita_periodo", "valor": 48700, "unidade": "BRL", "tendencia": "alta"},
      {"nome": "despesa_periodo", "valor": 35200, "unidade": "BRL", "tendencia": "baixa"},
      {"nome": "fluxo_liquido", "valor": 13500, "unidade": "BRL", "tendencia": "alta"}
    ],
    "alertas": [],
    "resumo_executivo": "Semana positiva com fluxo líquido de BRL 13.500."
  },
  "frontmatter": {
    "tipo": "snapshot",
    "dimensao": "financeiro",
    "periodo": "semanal",
    "gerado_em": "2025-06-19T10:00:00Z",
    "gerado_por": "financeiro_agent",
    "versao": 1,
    "template_version": 1,
    "ultimo_update": "2025-06-19T10:00:00Z",
    "fontes": ["get_cash_position v2", "get_recent_transactions v1"],
    "confianca": 0.95
  },
  "source": "specialist",
  "confidence": 0.95
}
```

#### Leitura

```
shared_memory_read(entity_type="snapshot", entity_name="financeiro:semanal", key="2025-06-19T10:00:00Z")
```

#### Seed (popula exemplos)

```bash
python scripts/seed_snapshots.py --client-id <UUID>
```

### 6. Queries de Referência por Dimensão

As queries SQL de referência estão documentadas nos specs de dimensão
(`_SNAPSHOT_DIMENSION_FIELDS[dimensao]["queries_referencia"]`).
São strings nomeando as funções/endpoints que geram os dados para cada
indicador. **Não são código executável** — são referências para o agente
que popula o snapshot saber quais fontes consultar.

| Dimensão    | Queries de Referência                                  |
|------------|-------------------------------------------------------|
| financeiro | get_cash_position, get_recent_transactions, get_aging_accounts |
| clientes   | get_active_clients, get_churn_metrics, get_nps_scores, get_client_ltv |
| agenda     | get_today_meetings, get_weekly_meetings, get_pending_followups, get_collection_contacts |
| compras    | get_open_purchase_orders, get_critical_stock, get_pending_suppliers, get_pending_approval_orders |

---

## Design Decisions

| ID  | Decisão |
|-----|---------|
| DD1 | `entity_type='snapshot'`, `entity_name='{dimensao}:{periodo}'`, key=ISO timestamp |
| DD2 | Body em JSON estruturado (não markdown). Só `resumo_executivo` é markdown. |
| DD3 | Queries SQL no frontmatter como REFERÊNCIA, não código executável. Versionadas. |
| DD4 | Frontmatter no JSONB da `shared_business_memory` (schema Fase 0). |
| DQ4 | Template base (`_SNAPSHOT_BASE_FIELDS`) + extensão por dimensão (`_SNAPSHOT_DIMENSION_FIELDS`). |

---

## T5.2 — Modelo de Permissões de Escrita

### 7. Write Path — Fluxo de Escrita

[ ] TODO: verificar

O fluxo de escrita na shared memory segue o princípio **Single Writer**:
cada `source` só pode escrever nos `entity_type` para os quais foi autorizada.
A verificação ocorre antes de qualquer operação no banco.

```
Entrada: entity_type, entity_name, key, value, source, confidence, supersede
    │
    ├─ 1. _validate_entity_type(entity_type)
    │     └─ entity_type ∉ _VALID_ENTITY_TYPES → ValueError
    │
    ├─ 2. _normalize_entity_name(entity_name) → lowercase, trimmed
    │     key = key.strip().lower()
    │
    ├─ 3. entity_name ou key vazios → ValueError
    │     value não-dict → ValueError
    │
    ├─ 4. _check_write_permission(source, entity_type, entity_name)
    │     └─ source ∉ _WRITE_PERMISSIONS ou entity_type não permitido → ValueError
    │
    ├─ 5. snapshot? → valida frontmatter (_validate_snapshot_frontmatter)
    │                 valida body (_validate_snapshot_body)
    │
    ├─ 6. Monta payload: client_id, entity_type, entity_name, key,
    │     value, category, source, confidence, metadata
    │
    ├─ 7. supersede=True?
    │     ├─ Sim → UPSERT ON CONFLICT (client_id,entity_type,entity_name,key)
    │     └─ Não  → INSERT (falha se duplicado → ValueError)
    │
    └─ 8. Retorna registro completo (id, version, created_at, updated_at)
```

A função principal é `_shared_memory_write_logic()` em
[`services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py`](../../services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py).

**Entrada externa (tool MCP):** `shared_memory_write` é a tool registrada no
MCP server que invoca `_shared_memory_write_logic()`. Ela valida campos
obrigatórios, normaliza `source` (default `"manual"` se inválido) e
valida `category` contra `_VALID_CATEGORIES`.

**Diferença `shared_memory_write` × `shared_memory_upsert`:**
- `shared_memory_write` (T5.2): strict INSERT por default, `supersede=True`
  para upsert. **Faz verificação de permissão de escrita.**
- `shared_memory_upsert` (T0.5, legada): sempre upsert, **não** faz
  verificação de permissão. Mantida por compatibilidade. Não documentada
  como parte do modelo T5.2.

### 8. Entity Type Access — Tipos de Entidade

[ ] TODO: verificar

Os `entity_type` válidos para escrita são definidos em `_VALID_ENTITY_TYPES`:

| entity_type      | Descrição                                      | Quem escreve                         |
|------------------|------------------------------------------------|--------------------------------------|
| `skill`          | Fatos derivados de skills/ferramentas          | system, memory_agent, specialist, manual, migration |
| `client`         | Dados de clientes (CRM)                        | system, memory_agent, specialist, manual, migration |
| `contact`        | Contatos individuais                           | system, memory_agent, specialist, manual, migration |
| `supplier`       | Fornecedores                                   | system, memory_agent, specialist, manual, migration |
| `user`           | Usuários da plataforma                         | system, memory_agent, specialist, manual, migration |
| `snapshot`       | Snapshots por dimensão (T2.2)                  | system, memory_agent, specialist, migration |
| `routine`        | Rotinas automatizadas (Routine Engine)         | system, memory_agent, migration     |
| `agent_result`   | Resultados de execução de agentes              | system, memory_agent, specialist, migration |
| `agent_metadata` | Metadados operacionais de agentes              | system, memory_agent, specialist, migration |

**Restrições por fonte:**
- `manual` (humano) só escreve entidades de negócio: `skill`, `client`, `contact`, `supplier`, `user`.
- `specialist` (agente especialista) escreve tudo **exceto** `routine`.
- `routine` é reservado para `system`, `memory_agent` e `migration`.

### 9. Authorization Rules by entity_type — Matriz de Permissões

[ ] TODO: verificar

A matriz de permissões é definida em `_WRITE_PERMISSIONS` (dict `source → frozenset[entity_type]`):

| source         | skill | client | contact | supplier | user | snapshot | routine | agent_result | agent_metadata |
|----------------|:-----:|:------:|:-------:|:--------:|:----:|:--------:|:-------:|:------------:|:--------------:|
| `system`       |   ✓   |   ✓    |    ✓    |    ✓     |  ✓   |    ✓     |    ✓    |      ✓       |       ✓        |
| `memory_agent` |   ✓   |   ✓    |    ✓    |    ✓     |  ✓   |    ✓     |    ✓    |      ✓       |       ✓        |
| `specialist`   |   ✓   |   ✓    |    ✓    |    ✓     |  ✓   |    ✓     |    ✗    |      ✓       |       ✓        |
| `manual`       |   ✓   |   ✓    |    ✓    |    ✓     |  ✓   |    ✗     |    ✗    |      ✗       |       ✗        |
| `migration`    |   ✓   |   ✓    |    ✓    |    ✓     |  ✓   |    ✓     |    ✓    |      ✓       |       ✓        |

**Regras de autorização:**

1. **`system`** — acesso total. Usado pelo próprio sistema e rotinas internas
   (ex: `prune_shared_memory`, `sbm_lightrag_weekly_synthesis`).

2. **`memory_agent`** — acesso total. Usado pelo agente de memória
   (DomainProjectionMemoryAgent) que consolida e projeta fatos entre dimensões.

3. **`specialist`** — acesso a entidades de domínio + snapshots + resultados.
   **Não pode escrever `routine`.** Usado por agentes especialistas
   (financeiro, clientes, agenda, compras).

4. **`manual`** — acesso apenas a entidades de negócio (`skill`, `client`,
   `contact`, `supplier`, `user`). Usado por intervenção humana ou API externa.
   **Não pode escrever `snapshot`, `routine`, `agent_result`, `agent_metadata`.**

5. **`migration`** — acesso total, idêntico a `system`. Usado exclusivamente
   durante migrações e importação de dados.

**Mensagens de erro:**

- Source desconhecida: `"Unknown source 'X'. Must be one of: ['manual', 'memory_agent', 'migration', 'specialist', 'system']"`
- Permissão negada: `"Write permission denied: source 'X' cannot write to entity_type 'Y' (entity: Z). Allowed types for 'X': [...]"`

### 10. Allowed Write Fields — Campos Permitidos

[ ] TODO: verificar

Os campos que cada `source` pode definir no payload de escrita:

| Campo        | Tipo    | Obrigatório | Default     | Restrição por source                |
|-------------|---------|:-----------:|-------------|--------------------------------------|
| client_id   | UUID    |     sim     | —           | Sem restrição                       |
| entity_type | string  |     sim     | —           | Via `_WRITE_PERMISSIONS`            |
| entity_name | string  |     sim     | —           | Normalizado para lowercase          |
| key         | string  |     sim     | —           | Normalizado para lowercase          |
| value       | dict    |     sim     | —           | Sem restrição                       |
| category    | string  |     não     | `None`      | Deve pertencer a `_VALID_CATEGORIES`|
| source      | string  |     não     | `"manual"`  | Deve pertencer a `_WRITE_PERMISSIONS`|
| confidence  | float   |     não     | `1.0`       | Range 0.0–1.0                       |
| supersede   | bool    |     não     | `False`     | Sem restrição                       |
| agent_id    | UUID    |     não     | `None`      | Armazenado em metadata              |
| ttl         | int     |     não     | `None`      | Armazenado em metadata              |
| priority    | int     |     não     | `None`      | Armazenado em metadata (0–100)      |
| ttl_tier    | string  |     não     | Inferido    | Tiers: curated, migration, specialist, memory_agent_hi, memory_agent_lo |

**Observações:**
- `source` inválido é silenciosamente normalizado para `"manual"` (fallback seguro).
- `category` inválida causa rejeição com `ToolError`.
- `agent_id`, `ttl`, `priority` são armazenados no JSONB `metadata`, não como
  colunas dedicadas.

### 11. Source Enum — Fontes de Escrita

[ ] TODO: verificar

As fontes (`source`) definem a **proveniência** de cada fato na shared memory.
O valor é armazenado na coluna `source` da tabela `shared_business_memory`.

| Source         | Definição                                                | Exemplo de uso                              |
|----------------|----------------------------------------------------------|---------------------------------------------|
| `system`       | Sistema / rotinas internas                               | `prune_shared_memory`, cron jobs            |
| `memory_agent` | DomainProjectionMemoryAgent (agente de projeção)         | Consolidação de fatos entre dimensões       |
| `specialist`   | Agentes especialistas de domínio                         | `financeiro_agent`, `clientes_agent`        |
| `manual`       | Intervenção humana ou API externa                        | Entrada manual de dados, integração REST    |
| `migration`    | Migração e importação de dados                           | Scripts de seed, importação em lote         |

**Fallback:** Se `source` não for reconhecido, o sistema normaliza para
`"manual"` — a fonte mais restritiva. Isso evita que um source inválido
ganhe acesso acidental a entity_types sensíveis.

**Enum no código:**
```python
# Valid sources (keys of _WRITE_PERMISSIONS)
# system, memory_agent, specialist, manual, migration
validated_source = source if source in _WRITE_PERMISSIONS else "manual"
```

### 12. Confidence Rules — Regras de Confiança

[ ] TODO: verificar

Toda escrita na shared memory carrega um score de **confiança** (`confidence`),
um `float` no intervalo **0.0 a 1.0**:

| Valor  | Significado                                     |
|--------|-------------------------------------------------|
| `1.0`  | Certeza absoluta (default para `manual`)        |
| 0.9–1.0| Alta confiança — agente com fontes confiáveis   |
| 0.7–0.9| Confiança moderada — inferência com respaldo    |
| 0.5–0.7| Baixa confiança — heurística ou estimativa      |
| 0.0–0.5| Muito baixa — placeholder ou dado não verificado|

**Uso:**
- Armazenado na coluna `confidence` da tabela `shared_business_memory`.
- Não há validação de range no write path atual (responsabilidade do caller).
- Consumidores (agentes de leitura, motor de busca) podem filtrar por
  `confidence` mínima para evitar fatos de baixa qualidade.
- No frontmatter de snapshots, o campo equivalente é `confianca` (também 0.0–1.0).

**Exemplo:**
```python
# Alta confiança — dado confirmado por múltiplas fontes
shared_memory_write(
    entity_type="client",
    entity_name="empresa_x",
    key="faturamento_anual",
    value={"valor": 15000000, "unidade": "BRL"},
    source="specialist",
    confidence=0.95,
)
```

### 13. Validation Behavior — Comportamento de Validação

[ ] TODO: verificar

O sistema aplica validação em três camadas:

#### 13.1 Validação de Entrada (Tool Level)

Executada em `shared_memory_write()` (wrapper MCP) **antes** de chamar
`_shared_memory_write_logic()`:

| Validação                          | Tipo de Erro | Mensagem                                    |
|------------------------------------|:------------:|---------------------------------------------|
| `client_id` ausente                | `ToolError`  | `client_id is required`                     |
| `entity_type` vazio                | `ToolError`  | `entity_type is required`                   |
| `entity_name` vazio                | `ToolError`  | `entity_name is required`                   |
| `key` vazio                        | `ToolError`  | `key is required`                           |
| `value` não-dict                   | `ToolError`  | `value must be a dict`                      |
| `category` inválida                | `ToolError`  | `Invalid category 'X'. Must be one of: [...]`|

#### 13.2 Validação de Permissão (Logic Level)

Executada em `_shared_memory_write_logic()` via `_check_write_permission()`:

| Condição                           | Tipo de Erro | Ação                                        |
|------------------------------------|:------------:|---------------------------------------------|
| `source` desconhecido              | `ValueError` | Rejeita                                     |
| `entity_type` não permitido        | `ValueError` | Rejeita com lista de tipos permitidos       |

#### 13.3 Validação Específica por entity_type

**Snapshots** (`entity_type="snapshot"`):
- `_validate_snapshot_frontmatter()`: verifica campos obrigatórios
  (`tipo`, `dimensao`, `periodo`, `gerado_em`, `gerado_por`, `versao`,
  `template_version`, `fontes`), cross-valida `dimensao` e `periodo`
  com `entity_name`.
- `_validate_snapshot_body()`: valida campos base (`_SNAPSHOT_BASE_FIELDS`)
  e indicadores da dimensão contra `_SNAPSHOT_DIMENSION_FIELDS`.
- Indicadores desconhecidos geram **WARNING** (não erro).
- Indicadores requeridos faltantes geram **ValueError**.

**Demais entity_types:** Apenas validação de tipo (deve pertencer a
`_VALID_ENTITY_TYPES`). Sem validação de schema no body.

### 14. Versioning/Audit — Versionamento e Auditoria

[ ] TODO: verificar

#### 14.1 Versionamento em `shared_memory_upsert` (legado T0.5)

A função `_shared_memory_upsert_logic()` implementa versionamento completo:

1. **Arquivamento:** Antes de sobrescrever, a versão atual é copiada para
   `shared_business_memory_versions` via `_archive_memory_version()`.
2. **Incremento:** `new_version = archived_version + 1` (ou `1` se for
   a primeira inserção).
3. **Payload:** Inclui `version: new_version` na coluna `version`.

#### 14.2 Comportamento em `shared_memory_write` (T5.2)

O `shared_memory_write` **não implementa versionamento automático**.
Comportamento:

- **Primeira escrita (INSERT):** `version` default `1` (via coluna no banco).
- **Supersede (UPSERT):** A linha é sobrescrita **sem arquivar** a versão
  anterior. A coluna `version` pode ser incrementada pelo banco via trigger,
  mas não há garantia de auditoria.

**Decisão de design:** `shared_memory_write` é otimizado para simplicidade
e performance. Para cenários que exigem trilha de auditoria completa,
use `shared_memory_upsert`.

#### 14.3 Trilha de Auditoria

A tabela `shared_business_memory` inclui colunas de auditoria padrão:

| Coluna       | Tipo        | Descrição                                  |
|-------------|-------------|---------------------------------------------|
| `id`        | int (PK)    | ID auto-increment                          |
| `created_at`| timestamptz | Timestamp de criação                       |
| `updated_at`| timestamptz | Timestamp da última atualização            |
| `source`    | text        | Fonte da última escrita                    |
| `version`   | int         | Número da versão (default 1)               |

Adicionalmente, a tabela `shared_business_memory_versions` armazena o
histórico completo de versões para entradas modificadas via
`shared_memory_upsert`.

### 15. Observability — Observabilidade

[ ] TODO: verificar

#### 15.1 Logging

O módulo `memory_module.py` usa `logging.getLogger(__name__)` com
log level `INFO` para operações normais e `ERROR` para falhas.

**Eventos logados:**

| Evento                              | Nível  | Mensagem                                                    |
|-------------------------------------|:------:|-------------------------------------------------------------|
| Write request                       | INFO   | `shared_memory_write entity_type=X entity_name=Y key=Z ...` |
| Write failure (ValueError)          | —      | Re-lançada como `ToolError` (sem log adicional)             |
| Write failure (Exception)           | ERROR  | `shared_memory_write failed: {exc}`                         |
| Tool registration                   | INFO   | `Tool 'shared_memory_write' registered.`                    |

#### 15.2 Métricas e Tracing

- **Métricas:** Não implementadas diretamente no módulo. O MCP server
  (FastMCP + Supabase) provê métricas de latência e taxa de erro via
  middleware.
- **Tracing:** `client_id` e timestamps (`created_at`, `updated_at`)
  permitem rastrear a origem e evolução de cada fato.

#### 15.3 Monitoramento de Permissões

- Toda violação de permissão gera `ValueError` com detalhes (source,
  entity_type, entity_name, allowed types).
- Esses erros são capturados pelo wrapper MCP e expostos como `ToolError`
  ao caller.
- Não há mecanismo de alerta proativo para violações repetidas — a
  responsabilidade é do agente chamador.

### 16. Non-Snapshot Upsert Examples — Exemplos para Outros entity_types

[ ] TODO: verificar

#### 16.1 Skill fact (source: specialist)

```json
{
  "entity_type": "skill",
  "entity_name": "nlp_analyzer",
  "key": "sentimento_cliente_x",
  "value": {
    "sentimento": "positivo",
    "score": 0.87,
    "ultima_analise": "2025-06-19T10:00:00Z"
  },
  "category": "knowledge",
  "source": "specialist",
  "confidence": 0.9
}
```

#### 16.2 Client fact (source: manual)

```json
{
  "entity_type": "client",
  "entity_name": "empresa_acme",
  "key": "contato_principal",
  "value": {
    "nome": "João Silva",
    "cargo": "CEO",
    "email": "joao@acme.com"
  },
  "category": "context",
  "source": "manual",
  "confidence": 1.0
}
```

#### 16.3 Routine fact (source: system)

```json
{
  "entity_type": "routine",
  "entity_name": "prune_shared_memory",
  "key": "ultima_execucao",
  "value": {
    "executado_em": "2025-06-19T03:00:00Z",
    "entradas_removidas": 42,
    "duracao_segundos": 3.5
  },
  "source": "system",
  "confidence": 1.0
}
```

#### 16.4 Agent result (source: memory_agent)

```json
{
  "entity_type": "agent_result",
  "entity_name": "domain_projection",
  "key": "projecao_semanal_2025-06-19",
  "value": {
    "dimensao_origem": "clientes",
    "dimensao_destino": "financeiro",
    "fatos_projetados": 15,
    "confianca_media": 0.88
  },
  "source": "memory_agent",
  "confidence": 0.9
}
```

#### 16.5 Migration (source: migration)

```json
{
  "entity_type": "client",
  "entity_name": "empresa_legado",
  "key": "historico_compras_2024",
  "value": {
    "total_compras": 250,
    "volume_total_brl": 1250000,
    "produtos_mais_comprados": ["produto_a", "produto_b"]
  },
  "source": "migration",
  "confidence": 1.0
}
```

### 17. Uniqueness Constraints — Constraints de Unicidade

[ ] TODO: verificar

#### 17.1 Chave Composta

A unicidade na `shared_business_memory` é garantida pela **chave composta**:

```
(client_id, entity_type, entity_name, key)
```

Esta constraint é implementada no banco via índice único
`uq_shared_memory_entry` (ou `uq_shared_business_memory`).

#### 17.2 Comportamento por Operação

| Operação                   | Comportamento                                          |
|---------------------------|--------------------------------------------------------|
| `shared_memory_write`     | INSERT estrito — falha se chave já existe              |
| `shared_memory_write` + supersede | UPSERT — sobrescreve se existe, insere se não   |
| `shared_memory_upsert`    | UPSERT — sempre sobrescreve, com versionamento         |

#### 17.3 Mensagens de Violação

**Duplicate key (INSERT sem supersede):**
```
ValueError: Memory entry already exists for skill:empresa_acme/contato_principal.
Use supersede=True to overwrite.
```

**Violação de unicidade inesperada:**
```
RuntimeError: Failed to write shared-memory entry: <detalhes do banco>
```

#### 17.4 Observações

- `entity_name` e `key` são **normalizados para lowercase e trimmed** antes
  de qualquer operação. Isso garante unicidade case-insensitive.
- A constraint cobre `client_id` — tenants diferentes podem ter a mesma
  entrada `(entity_type, entity_name, key)` sem conflito.
- A constraint **não** cobre `source` ou `confidence` — múltiplas fontes
  competem pela mesma chave (a última escrita vence no upsert).
