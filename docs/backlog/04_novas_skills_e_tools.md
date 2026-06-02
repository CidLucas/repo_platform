# Backlog — Novas Skills & Tools (Plano de Implementação)

*Origem: análise dos improvement docs das 19 skills revisadas (Mai-Jun/2026).*

---

## Grupo A — Extensões do Monday ✅ Baixo risco, implementar primeiro

**Tools novas a adicionar ao skill `monday`:**

| Tool | Descrição | Razão |
|------|-----------|-------|
| `monday_search_items` | Busca items por keyword, assignee ou status | Ausente hoje; CRM e agenda precisam buscar tasks |
| `monday_move_item` | Move item entre grupos/boards | Fluxo de Kanban interno |
| `monday_add_update` | Posta comentário/update em item | Fecha loop de acompanhamento |

**Status:** ❌ Nenhuma das 3 encontrada no repo.

**Ação:** adicionar as 3 tools ao `required_tool_names` da skill `monday` + documentar no prompt.

**Estimativa:** 2h

---

## Grupo B — Skills de Narrativa Pura ✅ Só prompt + SkillDefinition

| Skill | Agente | Descrição | Status |
|-------|--------|-----------|--------|
| `reconciliation_narrative` | financeiro | Narrativa mensal de reconciliação com anomalias | ⚠ Já existe como `reconciliation_report` — renomear se necessário, não criar nova |
| `budget_vs_actual` | financeiro | Compara gasto real vs orçamento por categoria, flag desvios >10% | ❌ Nova — sem overlap direto |
| `cash_flow_forecast` | financeiro | Projeção 30/60/90 dias com recebíveis + pagamentos + recorrências | ❌ Nova — sem overlap direto |
| `nota_fiscal_history` | fiscal-agent | Filtra e resume NFs emitidas por período/cliente/status (read-only) | ❌ Nova — complementa `fiscal` que só emite |

**Decisão pendente:** `budget_vs_actual` e `cash_flow_forecast` como skills separadas ou absorvidas por `finance_monitor_report` com parâmetros?

---

## Grupo C — Skills de CRM Avançado 🟡 Discutir overlap primeiro

| Skill | Agente | Descrição | Overlap a discutir |
|-------|--------|-----------|-------------------|
| `churn_risk_analysis` | crm | Previsão de churn com sinais pré-churn e plano de retenção por tier | `crm_ops` já faz churn+LTV+segmentação — esta seria drill-down interativo vs snapshot |
| `nps_response_drafter` | crm | Rascunha resposta personalizada para detratores/promotores NPS | `satisfaction_survey` gera survey; esta responde após receber NPS |
| `weekly_summary` enhanced | financeiro/strategy | WoW comparison com breakdown por categoria | `weekly_summary` já existe — avaliar se é parâmetro ou skill separada |

**Recomendação:** antes de criar, mapear o que `crm_ops` não cobre em runtime — pode ser só expansão de prompt.

---

## Grupo D — Tools Transversais de Alto Impacto 🟡 Avaliar esforço/benefício

| Tool | Skills que usariam | Descrição | Esforço |
|------|-------------------|-----------|---------|
| `validate_sql_dry_run` | sql_analytics | EXPLAIN antes de executar — evita queries perigosas | Médio (requer suporte no sql_module backend) |
| `get_week_kpis` | weekly_summary, morning_plan | Busca KPIs agregados sem SQL manual | Baixo (view no banco) / Médio (tool nova) |
| `fiscal_consultar_nota` | fiscal | Query de NFs por número/chave/período via ERP | Alto (integração ERP/SEFAZ) |

---

## Grupo E — Fora de Escopo Atual ❌ Não implementar

- `web_scraper`, `competitor_content_fetcher` — infra de scraping externa
- `fiscal_cancelar_nota`, `fiscal_deadline_calendar` — integrações SEFAZ avançadas
- `send_whatsapp_template`, `log_survey_response` — substituídos pelo `communication` skill
- `linear`, `asana`, `cross_pm_status` — plataformas fora do stack atual
- `swot_analysis`, `market_positioning`, `tax_regime_advisor` — consultoria estratégica pesada

---

## Próximos Passos Sugeridos

1. Implementar **Grupo A** (monday tools) — sem decisão arquitetural necessária
2. Discutir overlaps **Grupo B** (budget_vs_actual vs finance_monitor_report) e **Grupo C** (churn vs crm_ops)
3. Decidir `strategy_analysis` e cross-agent data entry (ver `03_agentes_e_skills.md`)
4. Implementar **Grupo B** após decisão de granularidade
5. **Grupo C e D** após validação de uso real com primeiros clientes
