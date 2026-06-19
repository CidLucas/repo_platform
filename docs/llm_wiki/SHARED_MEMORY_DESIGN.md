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
