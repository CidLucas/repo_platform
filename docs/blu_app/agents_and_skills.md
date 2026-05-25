# Blu — Agentes & Skills

> Gerado em: 2026-05-22
> Fonte: `registry.py` + `skills.py`
> Lógica de vínculo: interseção de tags entre agente e skill (`set(agent.tags) & set(skill.tags)`)

---

## Agentes (15)

| slug | tags | descrição resumida |
|---|---|---|
| frontdesk | frontdesk, routing, rag, sql | Recepção e roteamento — primeiro contato, RAG, SQL básico |
| context-gatherer | context, mapping, transactions, routines, knowledge | Coleta contexto do cliente: transações, rotinas, conhecimento |
| crm | crm, email, clients, reengagement | Gestão de relacionamento: e-mail, engajamento, reativação |
| estrategia | strategy, analytics, kpi, growth, planning, briefs | Análise estratégica: KPIs, crescimento, planejamento |
| compras | procurement, suppliers, purchases, cost | Compras e fornecedores: pedidos, custos, supply |
| financeiro | finance, revenue, reporting, cashflow | Financeiro: receita, relatórios, fluxo de caixa |
| agenda | scheduling, follow-up, calendar, clients, agenda | Agenda: calendário, follow-ups, reuniões com clientes |
| documentos | documents, knowledge-base, rag, digest | Documentos: OCR, RAG, base de conhecimento |
| synthesis | synthesis, cross-domain, strategy, analysis, multi-dimension | Síntese cross-domain: narrativas estratégicas integradas |
| data-analyst | data, analysis, trends, correlation, quantitative, finance, purchases, clients | Análise quantitativa: tendências, correlações, dados |
| platform | platform, routines, goals, config, operations | Plataforma: rotinas, metas, configuração, operações |
| supplier-agent | suppliers, rfq, whatsapp, quotes, procurement | Agente de fornecedor: RFQ, cotações via WhatsApp |
| scheduler-agent | calendar, scheduling, deadlines, availability, meetings | Agendamento: deadlines, disponibilidade, reuniões |
| doc-writer | documents, writing, drafts, briefs, sops, proposals | Redação: SOPs, propostas, briefings, rascunhos |
| fiscal-agent | fiscal, nfe, nfse, invoice, sefaz, tax | Fiscal: NF-e, NFS-e, SEFAZ, impostos |

---

## Skills (20)

### L1 — Analíticas / RAG

| slug | tags | descrição | max_turns |
|---|---|---|---|
| analyze_csv | analytics, csv, sql | Executa SQL em CSVs uploadados; retorna tabelas, agregados e tendências | 5 |
| rag_search | rag, knowledge-base, search | Busca na base de conhecimento do cliente via similaridade vetorial | 3 |
| extract_document | ocr, documents, extraction | Extrai texto, tabelas e campos estruturados de documentos (OCR) | 4 |
| write_to_kb | knowledge-base, persistence, documents | Salva análise ou resumo na base de conhecimento para futura recuperação | 2 |

### L3 — Morning Chain

| slug | tags | descrição | max_turns |
|---|---|---|---|
| morning_plan | routines, morning, planning, narrative | Plano diário priorizado a partir de KPIs, agenda, aprovações e alertas | 2 |
| end_of_day_digest | routines, digest, narrative, eod | Resumo do dia: tarefas concluídas, pendências e destaques | 2 |
| weekly_summary | routines, weekly, summary, narrative | Resumo semanal: KPI trends, destaques e foco recomendado para a semana | 2 |

### L3 — Financeiro

| slug | tags | descrição | max_turns |
|---|---|---|---|
| reconciliation_report | routines, finance, reconciliation, narrative | Narrativa de reconciliação mensal: anomalias por categoria, top merchants, discrepâncias | 3 |
| finance_monitor_report | routines, finance, monitor, report, alert | Snapshot de saúde financeira: receita vs meta, top custos, alertas de caixa | 3 |

### L3 — Clientes

| slug | tags | descrição | max_turns |
|---|---|---|---|
| collection_messages | routines, clients, collection, messages | Mensagens de cobrança personalizadas por dias de atraso (amigável / firme / urgente) | 2 |
| followup_draft | routines, clients, followup, sales | Mensagem de follow-up pós-venda com sugestões de cross-sell | 2 |
| reactivation_proposal | routines, clients, reactivation, retention | Proposta de reativação contextualizada para clientes inativos | 2 |
| satisfaction_survey | routines, clients, nps, satisfaction | Pesquisa de satisfação pós-entrega personalizada ao perfil do cliente | 2 |
| clients_monitor_report | routines, clients, monitor, report, alert | Snapshot de saúde de clientes: ativos vs churn, inadimplentes, NPS, ações prioritárias | 3 |

### L3 — Agenda

| slug | tags | descrição | max_turns |
|---|---|---|---|
| meeting_brief | routines, agenda, scheduling, meeting, briefing | Briefing pré-reunião: contexto, histórico, pontos-chave, itens de pauta sugeridos | 3 |
| agenda_monitor_report | routines, agenda, scheduling, monitor, report, alert | Snapshot de agenda: follow-ups atrasados, reuniões próximas, gaps de contato | 3 |

### L3 — Estratégia

| slug | tags | descrição | max_turns |
|---|---|---|---|
| hidden_patterns | routines, strategy, analytics, patterns | Análise de time-series e KPIs: anomalias, sazonalidade, picos/quedas + recomendações | 3 |
| competitor_analysis | routines, strategy, competitive, analysis | Análise competitiva: posicionamento, gaps, oportunidades e ameaças vs concorrentes | 4 |
| insights_synthesis | routines, synthesis, strategy, analysis, narrative | Síntese cross-domain: finance + clients + procurement + agenda → narrativa estratégica | 4 |

### L3 — Compras

| slug | tags | descrição | max_turns |
|---|---|---|---|
| inventory_digest | routines, procurement, monitor, report, alert | Digest de compras: estoque baixo, atrasos de fornecedor, status de POs, anomalias de custo | 3 |

---

## Mapa de vínculos por agente

> Baseado em interseção de tags. Um agente pode executar qualquer skill onde `set(agent.tags) & set(skill.tags) != {}`.

### frontdesk
| skill | via |
|---|---|
| analyze_csv | sql |
| rag_search | rag |

### context-gatherer
| skill | via |
|---|---|
| morning_plan | routines |
| end_of_day_digest | routines |
| weekly_summary | routines |
| reconciliation_report | routines |
| collection_messages | routines |
| followup_draft | routines |
| reactivation_proposal | routines |
| satisfaction_survey | routines |
| meeting_brief | routines |
| hidden_patterns | routines |
| competitor_analysis | routines |
| finance_monitor_report | routines |
| clients_monitor_report | routines |
| agenda_monitor_report | routines |
| inventory_digest | routines |
| insights_synthesis | routines |

> ⚠️ **Over-match via tag `routines`** — pega todas as 16 L3 skills. Avaliar se é intencional.

### crm
| skill | via |
|---|---|
| collection_messages | clients |
| followup_draft | clients |
| reactivation_proposal | clients |
| satisfaction_survey | clients |
| clients_monitor_report | clients |

### estrategia
| skill | via |
|---|---|
| analyze_csv | analytics |
| morning_plan | planning |
| hidden_patterns | analytics, strategy |
| competitor_analysis | strategy |
| insights_synthesis | strategy |

### compras
| skill | via |
|---|---|
| inventory_digest | procurement |

### financeiro
| skill | via |
|---|---|
| reconciliation_report | finance |
| finance_monitor_report | finance |

### agenda
| skill | via |
|---|---|
| collection_messages | clients |
| followup_draft | clients |
| reactivation_proposal | clients |
| satisfaction_survey | clients |
| meeting_brief | agenda, scheduling |
| clients_monitor_report | clients |
| agenda_monitor_report | agenda, scheduling |

> ⚠️ **agenda pega 4 skills de clients** via tag `clients` — avaliar se é intenção ou ruído de roteamento.

### documentos
| skill | via |
|---|---|
| rag_search | knowledge-base, rag |
| extract_document | documents |
| write_to_kb | documents, knowledge-base |
| end_of_day_digest | digest |

> ⚠️ **end_of_day_digest vinculado a documentos** via tag `digest` — avaliar se faz sentido.

### synthesis
| skill | via |
|---|---|
| hidden_patterns | strategy |
| competitor_analysis | analysis, strategy |
| insights_synthesis | analysis, strategy, synthesis |

### data-analyst
| skill | via |
|---|---|
| reconciliation_report | finance |
| collection_messages | clients |
| followup_draft | clients |
| reactivation_proposal | clients |
| satisfaction_survey | clients |
| competitor_analysis | analysis |
| finance_monitor_report | finance |
| clients_monitor_report | clients |
| insights_synthesis | analysis |

> ⚠️ **Over-match** — data-analyst pega skills de clients e strategy via tags genéricas (analysis, clients, finance).

### platform
| skill | via |
|---|---|
| morning_plan | routines |
| end_of_day_digest | routines |
| weekly_summary | routines |
| reconciliation_report | routines |
| collection_messages | routines |
| followup_draft | routines |
| reactivation_proposal | routines |
| satisfaction_survey | routines |
| meeting_brief | routines |
| hidden_patterns | routines |
| competitor_analysis | routines |
| finance_monitor_report | routines |
| clients_monitor_report | routines |
| agenda_monitor_report | routines |
| inventory_digest | routines |
| insights_synthesis | routines |

> ⚠️ **Over-match via tag `routines`** — igual ao context-gatherer. Avaliar se é intencional.

### supplier-agent
| skill | via |
|---|---|
| inventory_digest | procurement |

### scheduler-agent
| skill | via |
|---|---|
| meeting_brief | scheduling |
| agenda_monitor_report | scheduling |

### doc-writer
| skill | via |
|---|---|
| extract_document | documents |
| write_to_kb | documents |

### fiscal-agent
> ❌ **Zero skills vinculadas** — nenhuma skill possui tags fiscais (fiscal, nfe, nfse, tax, sefaz).
> Criar skill `nfe_summary` ou `tax_reconciliation` para cobrir este agente.

---

## Issues identificados

| # | tipo | agente/skill | problema | ação sugerida |
|---|---|---|---|---|
| 1 | 🔴 CRÍTICO | fiscal-agent | Zero skills vinculadas | Criar skill fiscal (nfe_summary, tax_reconciliation) |
| 2 | 🟡 OVER-MATCH | context-gatherer | Tag `routines` conecta todas as 16 L3 skills | Avaliar se é intencional ou deve ser restringido |
| 3 | 🟡 OVER-MATCH | platform | Tag `routines` conecta todas as 16 L3 skills | Idem acima |
| 4 | 🟡 OVER-MATCH | data-analyst | Tags genéricas puxam skills de clients e strategy | Refinar tags do agente ou das skills |
| 5 | 🟡 RUÍDO | agenda | Tag `clients` conecta 4 skills de CRM | Avaliar se agenda deve executar cobrança/reativação |
| 6 | 🟡 RUÍDO | documentos | Tag `digest` conecta end_of_day_digest | Avaliar se documentos deve processar digest EOD |

---

## Resultado das rotinas Polen (2026-05-22)

> Rodadas manualmente via `triggered_by = 'manual_test'`
> 10 rotinas ativas | 20 execuções (2 runs cada) | **20 completed | 0 failed**

| rotina | worker_slug | tempo (s) | resultado |
|---|---|---|---|
| daily_briefing | morning_plan | 14–58 | ✅ KPIs MTD ok |
| weekly_summary | weekly_summary | 21–35 | ✅ KPIs MTD ok |
| end_of_day_digest | end_of_day_digest | 71 | ✅ 14 atividades, digest ok |
| daily_insights | insights_synthesis | 77–107 | ✅ KPIs MTD ok |
| onboarding_complete | insights_synthesis | 53–74 | ✅ Context report 1321 chars, 23 métricas, indexado no RAG |
| morning_sync | — | 25–65 | ✅ check_health: 0, KPIs ok |
| pending_decisions_review | — | 18–25 | ✅ get_overdue: 0 |
| context_report_monthly | — | 92–101 | ✅ Context report 1321 chars |
| context_report_post_ingestion | — | 122–153 | ✅ Context report 1321 chars |
| deadline_radar | — | 124–126 | ⚠️ Google Calendar não conectado |

### Observações das rotinas
- `_run_skill_direct` funcionando — workers resolvidos corretamente (morning_plan, weekly_summary, insights_synthesis, end_of_day_digest)
- Tempos dentro do esperado: 14s–153s, sem timeouts
- `deadline_radar` — Google Calendar não integrado ao Polen (dado de integração, não bug de plataforma)
- `pending_decisions_review` e `morning_sync` sem `worker_slug` registrado — steps inline sem skill, avaliar se deveria ter worker
- Rotinas sem `client_routine` ativa no Polen (não testadas): `agenda_monitor`, `clientes_monitor`, `financeiro_monitor`, `compras_monitor`, `daily_insights` (catálogo), entre outras
