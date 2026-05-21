# Blu Routines — Plano de Skills
> Gerado em: 2026-05-20
> Objetivo: mapear TODAS as skills necessárias para as 26 rotinas do catálogo v2.1
> antes de definir agentes — a divisão de agentes será derivada daqui.

---

## Premissas de design

- **Skills determinísticas (L1/L2):** fetch de dados, cálculos, formatação — sem LLM, rodam em qualquer worker.
- **Skills LLM (L3):** narrativa, rascunhos, análise qualitativa — precisam de modelo. Candidatas a modelo pequeno (ex: Qwen 7B, Gemma 9B) se o prompt for bem estruturado.
- **Skills de orquestração (L4):** coordenam múltiplas L1-L3 em sequência/paralelo — precisam de modelo com raciocínio (ex: Llama 3.1 70B ou equivalente).
- **Critério para modelo pequeno:** output estruturado (JSON ou texto com template fixo), contexto < 4K tokens, sem necessidade de raciocínio multi-passo. Se atender, usar pequeno.
- **Crawler:** `crawl4ai` já disponível via `tool_pool_api/web_crawl_module` (MCP tool `web_crawl`).
- **NPS:** campo a adicionar em `analytics_v2.dim_clientes` (ex: `nps_score numeric`, `nps_data_coletada date`).
- **Config built-in:** trigger schedule aceita `expression` cron via UI — hora (diário), dia da semana (semanal), dia do mês (mensal).

---

## Mapa de Skills por Rotina

### GRUPO 1 — Morning Chain (Sistema)

#### SK-001 · `fetch_daily_context`
- **Tipo:** L1 — determinística
- **O que faz:** agrega em paralelo: KPIs do dia (`get_kpi_snapshots`), agenda Google (`get_calendar_events`), aprovações pendentes (`get_pending_approvals`), alertas de integração (`check_integration_health`).
- **Inputs:** `client_id`, `date`
- **Output:** `{kpis, agenda: [...], pendencias: [...], alertas: [...]}`
- **Modelo:** nenhum
- **Rotinas:** morning_sync, daily_briefing, pending_decisions_review

#### SK-002 · `generate_morning_plan`
- **Tipo:** L3 — LLM narrativa
- **O que faz:** recebe output de SK-001 e gera plano do dia em linguagem natural, priorizando itens por urgência/impacto.
- **Inputs:** `{kpis, agenda, pendencias, alertas, client_name, tone}`
- **Output:** `{plano_texto, itens_prioritarios: [...], alertas_criticos: [...]}`
- **Modelo:** pequeno (template fixo, output estruturado, < 3K tokens de contexto) ✅
- **Langfuse prompt:** `blu/morning_plan_v1`
- **Rotinas:** Plano do Dia

#### SK-003 · `format_daily_briefing`
- **Tipo:** L3 — LLM narrativa
- **O que faz:** transforma dados de atividade do dia anterior (`get_daily_activity`) em digest narrativo conciso.
- **Inputs:** `{atividades, kpis_ontem, pendencias_resolvidas, pendencias_novas}`
- **Output:** `{briefing_texto, destaques: [...], proximos_passos: [...]}`
- **Modelo:** pequeno ✅ (estrutura fixa tipo newsletter)
- **Langfuse prompt:** `blu/daily_briefing_v1`
- **Rotinas:** daily_briefing, Digest Diário

---

### GRUPO 2 — Resumo Semanal (Sistema + Built-in)

#### SK-004 · `fetch_weekly_performance`
- **Tipo:** L1
- **O que faz:** lê `get_weekly_activity` + `v_series_temporal` (período 7d vs 7d anterior) + `get_overdue_approvals`.
- **Inputs:** `client_id`, `week_start_date`
- **Output:** `{receita_semana, pedidos, comparativo_anterior, top_clientes, aprovacoes_pendentes}`
- **Modelo:** nenhum
- **Rotinas:** Resumo Semanal, end_of_day_digest

#### SK-005 · `generate_weekly_summary`
- **Tipo:** L3 — LLM narrativa
- **O que faz:** narrativa de performance semanal com comparativo e recomendações.
- **Inputs:** output de SK-004 + `config.tone` (executivo | detalhado)
- **Output:** `{resumo_texto, kpis_destaque, recomendacoes: [...]}`
- **Modelo:** pequeno ✅ (comparativos numéricos + template)
- **Langfuse prompt:** `blu/weekly_summary_v1`
- **Trigger config:** dia da semana (padrão: sexta) + hora
- **Rotinas:** Resumo Semanal

---

### GRUPO 3 — Financeiro (Built-in + Opcional)

#### SK-006 · `fetch_cash_position`
- **Tipo:** L1
- **O que faz:** lê `polp_accounts` por `client_id`, calcula saldo total, saldo disponível em conta corrente, limite de crédito disponível.
- **Inputs:** `client_id`, `include_credit: bool`
- **Output:** `{saldo_total, saldo_conta_corrente, limite_credito_disponivel, contas: [...]}`
- **Modelo:** nenhum
- **Fonte:** `public.polp_accounts`
- **Rotinas:** Alerta de Fluxo, Conciliação Mensal

#### SK-007 · `fetch_recent_transactions`
- **Tipo:** L1
- **O que faz:** lê `polp_transactions` últimos N dias, extrai imagens de comprovante do campo `merchant` (JSONB), agrupa por categoria, separa débitos/créditos.
- **Inputs:** `client_id`, `days: int`, `include_images: bool`
- **Output:** `{transacoes: [...], total_debitos, total_creditos, por_categoria: {}, imagens_comprovante: [url]}`
- **Nota:** `merchant` JSONB pode ter `logo_url` ou `imageUrl` — extrair e incluir na resposta para exibição no card.
- **Modelo:** nenhum
- **Fonte:** `public.polp_transactions` (`merchant` jsonb, `payment_data` jsonb, `category` jsonb)
- **Rotinas:** Conciliação, Cobrança

#### SK-008 · `evaluate_cash_alert`
- **Tipo:** L2 — computacional
- **O que faz:** compara `saldo_total` com `config.threshold`, calcula dias de runway com base em média de saídas dos últimos 30d, retorna `should_alert: bool` + `severity`.
- **Inputs:** output de SK-006, `config.threshold`, `config.runway_days_warn`
- **Output:** `{should_alert, severity, saldo_atual, threshold, runway_days, mensagem}`
- **Modelo:** nenhum (lógica pura)
- **Trigger:** numeric (avaliado pelo dispatcher)
- **Rotinas:** Alerta de Fluxo de Caixa

#### SK-009 · `generate_reconciliation_report`
- **Tipo:** L3 — LLM narrativa
- **O que faz:** recebe transações do mês + KPIs + saldo e gera relatório de conciliação narrativo com destaques (maiores saídas, inconsistências, categorias acima do normal).
- **Inputs:** `{transacoes, saldo_pos, saldo_inicio, kpis, mes_referencia}`
- **Output:** `{relatorio_texto, alertas: [...], categorias_destaque: [...], imagens_comprovante: [url]}`
- **Modelo:** médio (análise de padrões + narrativa) — **não** pequeno, precisa de raciocínio sobre anomalias
- **Langfuse prompt:** `blu/reconciliation_v1`
- **Trigger config:** dia do mês (padrão: dia 5)
- **Rotinas:** Relatório de Conciliação

---

### GRUPO 4 — Clientes e Vendas (Built-in + Opcional)

#### SK-010 · `fetch_overdue_customers`
- **Tipo:** L1
- **O que faz:** query em `dim_clientes` + `fato_transacoes` filtrando `dias_recencia > config.dias_atraso` e `receita_total > 0`, ordena por valor em aberto estimado.
- **Inputs:** `client_id`, `min_dias_atraso: int`, `max_results: int`
- **Output:** `{inadimplentes: [{nome, telefone, dias_recencia, receita_total, ultima_compra}], total_count}`
- **Modelo:** nenhum
- **Rotinas:** Cobrança de Inadimplentes

#### SK-011 · `generate_collection_messages`
- **Tipo:** L3 — LLM por item
- **O que faz:** para cada cliente inadimplente, gera mensagem de cobrança personalizada (WhatsApp/email) ajustando tom por tempo de atraso e histórico de relacionamento.
- **Inputs:** `{clientes: [...], config.tom (amigável|firme|urgente), config.canal}`
- **Output:** `{mensagens: [{cliente_id, texto, canal}]}`
- **Modelo:** pequeno ✅ (template com variáveis, output por item)
- **Langfuse prompt:** `blu/collection_message_v1`
- **Rotinas:** Cobrança de Inadimplentes

#### SK-012 · `fetch_client_pipeline`
- **Tipo:** L1
- **O que faz:** lê `dim_clientes` com `nivel_cluster`, `frequencia_mensal`, `dias_recencia`, `data_ultima_compra`. Segmenta em: ativos, em risco, inativos, novos.
- **Inputs:** `client_id`, `segment_filter: str | None`
- **Output:** `{ativos: [...], em_risco: [...], inativos: [...], novos: [...], totais: {}}`
- **Modelo:** nenhum
- **Rotinas:** Pipeline de Clientes, Reativação

#### SK-013 · `generate_followup_draft`
- **Tipo:** L3 — LLM
- **O que faz:** pós-venda aprovada (`sale_approved`), gera mensagem de follow-up/agradecimento personalizado, podendo incluir sugestões de produtos complementares.
- **Inputs:** `{cliente, pedido, config.canal, config.incluir_crosssell: bool}`
- **Output:** `{texto_followup, canal, cliente_id}`
- **Modelo:** pequeno ✅
- **Langfuse prompt:** `blu/followup_v1`
- **Rotinas:** Follow-up de Vendas

#### SK-014 · `generate_reactivation_proposal`
- **Tipo:** L3 — LLM
- **O que faz:** para clientes inativos (SK-012 segmento `inativos`), gera proposta de reativação contextualizada (última compra, histórico, possível oferta).
- **Inputs:** `{cliente, historico, config.incluir_desconto: bool, config.canal}`
- **Output:** `{proposta_texto, canal, cliente_id, score_prioridade}`
- **Modelo:** pequeno ✅ (template, variáveis por cliente)
- **Langfuse prompt:** `blu/reactivation_v1`
- **Trigger config:** dia do mês (padrão: dia 15)
- **Rotinas:** Reativação de Clientes

---

### GRUPO 5 — Operações (Built-in)

#### SK-015 · `fetch_inventory_alerts`
- **Tipo:** L1
- **O que faz:** lê `dim_inventory` comparando `quantidade_atual` com `estoque_minimo` (campo do produto ou `config.threshold_global`). Retorna SKUs críticos e próximos do limite.
- **Inputs:** `client_id`, `config.threshold_pct` (% do mínimo que já alerta)
- **Output:** `{criticos: [{sku, nome, qty_atual, qty_minima}], proximos: [...], ok: int}`
- **Modelo:** nenhum
- **Nota:** verificar se `dim_inventory` tem `estoque_minimo` — se não, adicionar campo ou usar `config` da rotina como threshold global.
- **Rotinas:** Nível de Estoque Crítico

#### SK-016 · `fetch_supplier_orders`
- **Tipo:** L1
- **O que faz:** lê `fato_compras` + `dim_fornecedores`, agrupa pedidos por fornecedor, calcula status de entregas (no prazo, atrasado, pendente).
- **Inputs:** `client_id`, `days_back: int`
- **Output:** `{fornecedores: [{nome, pedidos_open, pedidos_atrasados, valor_aberto}], resumo}`
- **Modelo:** nenhum
- **Rotinas:** Gestão de Fornecedores

---

### GRUPO 6 — Agenda e Reuniões (Opcional)

#### SK-017 · `fetch_upcoming_meetings`
- **Tipo:** L1 (já existe como `get_calendar_events`)
- **O que faz:** filtra eventos das próximas 24h com participantes externos (email externo ao domínio do cliente).
- **Inputs:** `client_id`, `hours_ahead: int`
- **Output:** `{reunioes: [{title, starts_at, participants, hangout_link}]}`
- **Modelo:** nenhum
- **Rotinas:** Prep Reunião

#### SK-018 · `fetch_meeting_participant_context`
- **Tipo:** L1 + L2
- **O que faz:** para cada participante externo de uma reunião, busca: (a) em `dim_clientes` (se for cliente), (b) crawl4ai no domínio do email (se for novo) para extrair contexto da empresa.
- **Inputs:** `{participantes: [email], client_id}`
- **Output:** `{participantes: [{email, nome, empresa, contexto_cliente, contexto_web}]}`
- **Modelo:** nenhum (crawl4ai é determinístico)
- **Tool:** MCP `web_crawl` via `tool_pool_api`
- **Rotinas:** Prep Reunião

#### SK-019 · `generate_meeting_brief`
- **Tipo:** L3 — LLM
- **O que faz:** recebe outputs de SK-017 + SK-018 + histórico do cliente e gera briefing de reunião com: quem é o participante, histórico de negócios, pontos de atenção, sugestões de pauta.
- **Inputs:** `{reuniao, participantes_contexto, historico_cliente}`
- **Output:** `{briefing_texto, pontos_atencao: [...], sugestoes_pauta: [...]}`
- **Modelo:** médio (síntese de múltiplas fontes, raciocínio sobre relacionamento)
- **Langfuse prompt:** `blu/meeting_brief_v1`
- **Rotinas:** Prep Reunião

---

### GRUPO 7 — Estratégia e Insights (Opcional)

#### SK-020 · `fetch_sales_performance`
- **Tipo:** L1
- **O que faz:** lê `v_series_temporal` (últimos 90d), `v_resumo_dashboard`, `v_distribuicao_regional`. Calcula tendência (regressão linear simples), top produtos, top regiões.
- **Inputs:** `client_id`, `period_days: int`
- **Output:** `{tendencia_receita, top_produtos: [...], top_regioes: [...], crescimento_pct, serie_temporal: [...]}`
- **Modelo:** nenhum
- **Rotinas:** Padrões Escondidos, Análise de Concorrência

#### SK-021 · `detect_hidden_patterns`
- **Tipo:** L3 — LLM análise
- **O que faz:** analisa `v_series_temporal` buscando anomalias estatísticas (picos, quedas, sazonalidade inesperada), compara com histórico e gera narrativa explicativa.
- **Inputs:** `{serie_temporal, kpis, periodo, contexto_empresa}`
- **Output:** `{padroes: [{descricao, severidade, periodo_afetado}], narrativa, recomendacoes}`
- **Modelo:** médio/grande (raciocínio analítico sobre dados temporais, sem template fixo)
- **Langfuse prompt:** `blu/hidden_patterns_v1`
- **Trigger config:** dia da semana (padrão: domingo)
- **Rotinas:** Padrões Escondidos

#### SK-022 · `crawl_competitor_pages`
- **Tipo:** L1 — determinística (usa crawl4ai)
- **O que faz:** crawl de até 3 URLs de concorrentes configuradas em `config.competitor_urls`, extrai markdown de páginas de produto/preço/home.
- **Inputs:** `{competitor_urls: [str], max_pages_each: int}`
- **Output:** `{concorrentes: [{url, titulo, conteudo_markdown}]}`
- **Modelo:** nenhum (crawl4ai)
- **Tool:** MCP `web_crawl`
- **Rotinas:** Análise de Concorrência

#### SK-023 · `generate_competitor_analysis`
- **Tipo:** L3 — LLM análise
- **O que faz:** compara dados do cliente (SK-020) com conteúdo crawlado dos concorrentes (SK-022), gera análise competitiva: posicionamento, gaps, oportunidades.
- **Inputs:** `{performance_cliente, concorrentes_conteudo, contexto_empresa, config.foco (preco|produto|posicionamento)}`
- **Output:** `{analise_texto, oportunidades: [...], ameacas: [...], recomendacoes: [...]}`
- **Modelo:** médio/grande (síntese comparativa, raciocínio estratégico)
- **Langfuse prompt:** `blu/competitor_analysis_v1`
- **Trigger config:** dia do mês (padrão: dia 1) + `competitor_urls` no config_schema
- **Rotinas:** Análise de Concorrência

---

### GRUPO 8 — NPS e Satisfação (Opcional)

#### SK-024 · `fetch_nps_data`
- **Tipo:** L1
- **O que faz:** lê campo NPS de `analytics_v2.dim_clientes` (`nps_score`, `nps_data_coletada` — campos a adicionar). Agrupa por score range (promotores 9-10, neutros 7-8, detratores 0-6).
- **Inputs:** `client_id`, `min_responses: int`
- **Output:** `{nps_score, promotores_pct, detratores_pct, neutros_pct, n_respostas, data_coleta}`
- **Modelo:** nenhum
- **Nota:** requer migration para adicionar `nps_score numeric, nps_data_coletada date` em `dim_clientes`
- **Rotinas:** Pesquisa de Satisfação

#### SK-025 · `generate_satisfaction_survey`
- **Tipo:** L3 — LLM
- **O que faz:** pós-entrega (`pedido_entregue` event), gera mensagem de pesquisa de satisfação personalizada para o cliente. Canal configurável.
- **Inputs:** `{cliente, pedido, config.canal, config.template}`
- **Output:** `{mensagem_texto, link_pesquisa, canal}`
- **Modelo:** pequeno ✅ (template com personalização mínima)
- **Langfuse prompt:** `blu/satisfaction_survey_v1`
- **Rotinas:** Pesquisa de Satisfação

---

### GRUPO 9 — Polp Webhook + Imagens (Infra)

#### SK-026 · `polp_webhook_receiver` *(não é skill de rotina — é infraestrutura)*
- **O que é:** endpoint `POST /webhooks/polp` no `tool_pool_api` (padrão idêntico ao `twilio_webhook_router.py`).
- **O que faz:** recebe notificação de nova transação Polp → upsert em `polp_transactions` → `fire_event_for_client('new_transaction', {account_id, amount, type})`.
- **Evento dispara:** rotinas com `trigger_type='event'` e `event='new_transaction'` (ex: Alerta de Fluxo em tempo real).
- **Imagens de transação:** campo `merchant.logo_url` e `payment_data.receiver` do JSONB existente — extrair na SK-007 e incluir nos cards como thumbnails.
- **Arquivo destino:** `services/tool_pool_api/src/tool_pool_api/api/polp_webhook_router.py`

---

## Resumo de Skills

| ID | Nome | Tipo | Modelo | Rotinas |
|---|---|---|---|---|
| SK-001 | fetch_daily_context | L1 | nenhum | morning_sync, daily_briefing |
| SK-002 | generate_morning_plan | L3 | **pequeno** | Plano do Dia |
| SK-003 | format_daily_briefing | L3 | **pequeno** | Digest Diário |
| SK-004 | fetch_weekly_performance | L1 | nenhum | Resumo Semanal |
| SK-005 | generate_weekly_summary | L3 | **pequeno** | Resumo Semanal |
| SK-006 | fetch_cash_position | L1 | nenhum | Alerta Fluxo, Conciliação |
| SK-007 | fetch_recent_transactions | L1 | nenhum | Conciliação, Cobrança |
| SK-008 | evaluate_cash_alert | L2 | nenhum | Alerta Fluxo |
| SK-009 | generate_reconciliation_report | L3 | **médio** | Conciliação |
| SK-010 | fetch_overdue_customers | L1 | nenhum | Cobrança |
| SK-011 | generate_collection_messages | L3 | **pequeno** | Cobrança |
| SK-012 | fetch_client_pipeline | L1 | nenhum | Pipeline, Reativação |
| SK-013 | generate_followup_draft | L3 | **pequeno** | Follow-up |
| SK-014 | generate_reactivation_proposal | L3 | **pequeno** | Reativação |
| SK-015 | fetch_inventory_alerts | L1 | nenhum | Estoque Crítico |
| SK-016 | fetch_supplier_orders | L1 | nenhum | Fornecedores |
| SK-017 | fetch_upcoming_meetings | L1 | nenhum | Prep Reunião |
| SK-018 | fetch_meeting_participant_context | L1+L2 | nenhum | Prep Reunião |
| SK-019 | generate_meeting_brief | L3 | **médio** | Prep Reunião |
| SK-020 | fetch_sales_performance | L1 | nenhum | Padrões, Concorrência |
| SK-021 | detect_hidden_patterns | L3 | **médio/grande** | Padrões Escondidos |
| SK-022 | crawl_competitor_pages | L1 | nenhum (crawl4ai) | Concorrência |
| SK-023 | generate_competitor_analysis | L3 | **médio/grande** | Concorrência |
| SK-024 | fetch_nps_data | L1 | nenhum | Satisfação |
| SK-025 | generate_satisfaction_survey | L3 | **pequeno** | Satisfação |

**Total: 25 skills** (+ SK-026 infraestrutura webhook)

---

## Agrupamento por perfil de modelo

| Perfil | Skills | Candidato |
|---|---|---|
| Sem modelo (L1/L2) | SK-001,004,006,007,008,010,012,015,016,017,018,020,022,024 — 14 skills | worker Python puro |
| Modelo pequeno (L3 template) | SK-002,003,005,011,013,014,025 — 7 skills | Qwen 7B / Gemma 9B |
| Modelo médio (L3 síntese) | SK-009,019 — 2 skills | Llama 3.1 8B ou 70B |
| Modelo médio/grande (L3 analítico) | SK-021,023 — 2 skills | Llama 3.1 70B ou equivalente |

**Implicação para agentes:**
- Rotinas com apenas L1/L2 podem ser executadas sem agente LLM algum — só o engine Python.
- Rotinas com L3-pequeno podem usar um agente com modelo leve (1 agente pode cobrir todas as 7).
- Rotinas com L3-médio/grande precisam de agente com modelo maior (2-4 rotinas no máximo simultâneas).
- Isso sugere **2 agentes LLM** no mínimo: um para narrativas simples (7 skills), um para análise (4 skills). A divisão exata vem depois.

---

## Decisions confirmadas

| # | Decisão | Resolução |
|---|---|---|
| 1 | NPS | Campo em `analytics_v2.dim_clientes` — fetch traz tudo do cliente (bom para listas/buscas) |
| 2 | Estoque mínimo | Campo por SKU em `dim_inventory.estoque_minimo` |
| 3 | `competitor_urls` | Dict `{"nome": "url"}` até 3 entradas — mais flexível que linhas de texto |
| 4 | Canal de notificação | **Somente card no app** no MVP — sem WhatsApp/email por ora |
| 5 | Polp webhook | `external_id: "pluggy_tx_abc123"` confirma que Polp é wrapper do **Pluggy**. Usar Pluggy Webhook padrão. Ver abaixo. |

---

## Polp/Pluggy Webhook — detalhes técnicos

O Polp usa Pluggy como provedor bancário open finance. O `external_id` das transações segue o formato `pluggy_tx_*`.

**Payload do Pluggy webhook (evento `transaction/created`):**
```json
{
  "event": "transaction/created",
  "itemId": "<pluggy_item_id>",  // = polp_integrations.polp_integration_id
  "data": {
    "id": "pluggy_tx_abc123",
    "accountId": "<pluggy_account_id>",
    "description": "UBER TRIP HELP.UBER.COM",
    "amount": -18.90,
    "date": "2024-04-14",
    "type": "DEBIT",
    "balance": 4231.10,
    "category": {"id": 45, "description": "Transporte", "color": "#4A90E2", "icon": "directions_car"},
    "merchant": {
      "id": 7, "name": "Uber", "business_name": "UBER DO BRASIL TECNOLOGIA LTDA",
      "logo_url": "https://assets.polp.io/uber.png", "domain": "uber.com"
    }
  }
}
```

**Mapeamento Pluggy → Blu:**
- `itemId` → busca `polp_integrations WHERE polp_integration_id = itemId` → obtém `client_id`
- `data.id` → `polp_transactions.external_id`
- `merchant.logo_url` → disponível direto no JSONB, sem fetch extra

**Arquivo destino:** `services/tool_pool_api/src/tool_pool_api/api/polp_webhook_router.py`  
**Padrão:** idêntico a `twilio_webhook_router.py` já existente (validação de assinatura → upsert → `fire_event_for_client`)

**Eventos disparados:**
- `new_transaction` → rotinas de monitoramento de caixa em tempo real
- `account_updated` → recalcular `cash_position` no cache

---

## Migrations e campos novos necessários

| Item | Tipo | Descrição |
|---|---|---|
| `analytics_v2.dim_clientes.nps_score` | ALTER TABLE | `numeric NULL` — score NPS agregado |
| `analytics_v2.dim_clientes.nps_data_coletada` | ALTER TABLE | `date NULL` — data da última coleta NPS |
| `analytics_v2.dim_clientes.nps_detalhes` | ALTER TABLE | `jsonb NULL` — breakdown promotores/neutros/detratores |
| `analytics_v2.dim_inventory.estoque_minimo` | ALTER TABLE | `numeric NULL` — threshold mínimo por SKU |
| `polp_webhook_router.py` | arquivo novo | receptor Pluggy webhook em `tool_pool_api` — mapeando `itemId` → `client_id` via `polp_integrations` |
| `google_calendar_webhook_router.py` | arquivo novo | receptor Google Calendar push notification em `agent_api` |
| Seed updates `cross_agent_routines` | SQL UPDATE | `config_schema` + `trigger_config` corretos para todas as built-ins |

---

## Config schema padrão para built-ins

```json
// Alerta de Fluxo de Caixa — trigger numeric
{
  "config_schema": [
    {"key": "threshold", "label": "Saldo mínimo (R$)", "type": "number", "default": 5000},
    {"key": "runway_days_warn", "label": "Alertar se runway < N dias", "type": "number", "default": 15}
  ],
  "trigger_type": "numeric",
  "trigger_config": {"metric": "saldo_conta_corrente", "operator": "lt", "field": "threshold"}
}

// Cobrança de Inadimplentes — cron semanal (usuário escolhe dia + hora)
{
  "config_schema": [
    {"key": "min_dias_atraso", "label": "Dias de atraso mínimo", "type": "number", "default": 30},
    {"key": "tom", "label": "Tom da mensagem", "type": "select",
     "options": [{"value": "amigavel", "label": "Amigável"}, {"value": "firme", "label": "Firme"}, {"value": "urgente", "label": "Urgente"}],
     "default": "amigavel"}
  ],
  "trigger_type": "schedule",
  "trigger_config": {"expression": "0 9 * * 1"}
}

// Análise de Concorrência — cron mensal (usuário escolhe dia do mês)
{
  "config_schema": [
    {"key": "concorrentes", "label": "Concorrentes (nome: URL)", "type": "dict",
     "max_entries": 3,
     "default": {}},
    {"key": "foco", "label": "Foco da análise", "type": "select",
     "options": [{"value": "preco", "label": "Preço"}, {"value": "produto", "label": "Produto"}, {"value": "posicionamento", "label": "Posicionamento"}],
     "default": "posicionamento"}
  ],
  "trigger_type": "schedule",
  "trigger_config": {"expression": "0 8 1 * *"}
}

// Reativação de Clientes — cron mensal (usuário escolhe dia)
{
  "config_schema": [
    {"key": "min_dias_inatividade", "label": "Inativo há mais de (dias)", "type": "number", "default": 60},
    {"key": "incluir_proposta", "label": "Incluir proposta/desconto", "type": "boolean", "default": false}
  ],
  "trigger_type": "schedule",
  "trigger_config": {"expression": "0 9 15 * *"}
}
```

**Nota sobre config_schema tipo `dict`:** o `SchemaField` do front (`RoutineConfigSection.tsx`) cobre `boolean`, `select`, `number`, `text`. O tipo `dict` com `max_entries: 3` precisará de um novo renderer para os campos de concorrentes (3 pares nome/URL). Pequena adição no componente `SchemaField`.
