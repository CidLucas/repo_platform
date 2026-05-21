markdown
Blu — Infraestrutura de Rotinas: Análise Técnica v1.0
Data: 2026-05-20
Propósito: Referência de engenharia para implementação das rotinas do catálogo v2.1,
ancorada no estado real do repositório. Cobre triggers, funções, skills, classificação
system/built-in e gaps identificados.

    1. TRIGGERS — O QUE TEMOS VS O QUE O CATÁLOGO EXIGE

    1.1 O que existe hoje (live no banco)

    O sistema de disparo já está construído e funcional. Resumo do que existe:

    pg_cron jobs ativos:
    Job: dispatch_routine_executions_to_agent
    Schedule: * * * * *
    O que faz: Chama dispatch_routine_executions() → HTTP POST para agent_api a cada
      minuto
    ────────────────────────────────────────
    Job: process_pending_routine_executions
    Schedule: * * * * *
    O que faz: Processa execuções pendentes via SQL
    ────────────────────────────────────────
    Job: enqueue_monthly_close
    Schedule: 0 23 28-31 * *
    O que faz: Enfileira fechamento mensal

    RPCs de disparo existentes:
    - enqueue_routine(client_id, routine_id, triggered_by, trigger_data, cooldown_h) — enfileira execução com cooldown guard
    - enqueue_custom_routine() — variante para rotinas UUID (custom)
    - enqueue_routine_for_me() — disparo autenticado pelo próprio usuário
    - dispatch_routine_event(routine_id, client_id, trigger_data) — dispara rotina event-triggered com guards (active, in-flight, stamp)
    - fire_event_for_client(event_type, client_id, trigger_data) — rota evento para TODAS as rotinas subscritas ao event_type
    - auto_enroll_catalog_routines() / auto_enroll_system_routines() — matrícula automática de novos clientes nas rotinas

    Fluxo de execução (já funcional):

    pg_cron (every minute)
      → dispatch_routine_executions()   [SQL]
          → HTTP POST /internal/routines/run-dispatched  [agent_api]
              → claim_routine_executions() SKIP LOCKED   [SQL]
                  → execute steps: function | skill | artifact  [Python engine]
                      → result_text + result_metadata stored   [client_routine_executions]


    Tipos de trigger suportados no schema:
    cross_agent_routines.trigger_type aceita: cron, event, manual, document

    Rotinas já seedadas no banco (cross_agent_routines):
    id: morning_sync
    nome: Sincronização da Manhã
    trigger_type: cron
    cron/event: 0 10 * * * (07:00 BRL)
    ────────────────────────────────────────
    id: daily_briefing
    nome: Plano do Dia
    trigger_type: cron
    cron/event: 30 10 * * * (07:30 BRL)
    ────────────────────────────────────────
    id: deadline_radar
    nome: Radar de Prazos
    trigger_type: cron
    cron/event: 0 12 * * * (09:00 BRL)
    ────────────────────────────────────────
    id: pending_decisions_review
    nome: Revisão de Decisões Pendentes
    trigger_type: cron
    cron/event: 0 11 * * *
    ────────────────────────────────────────
    id: end_of_day_digest
    nome: Digest do Fim de Dia
    trigger_type: cron
    cron/event: 0 21 * * * (18:00 BRL)
    ────────────────────────────────────────
    id: weekly_summary
    nome: Resumo Semanal
    trigger_type: cron
    cron/event: 0 20 * * 5 (17:00 BRL Fri)
    ────────────────────────────────────────
    id: daily_insights
    nome: Insights Diários
    trigger_type: cron
    cron/event: 0 6 * * *
    ────────────────────────────────────────
    id: context_report_monthly
    nome: Relatório de Contexto (Mensal)
    trigger_type: cron
    cron/event: 0 3 1 * *
    ────────────────────────────────────────
    id: context_report_post_ingestion
    nome: Relatório de Contexto (Pós-Ingestão)
    trigger_type: event
    cron/event: ingestion_completed
    ────────────────────────────────────────
    id: onboarding_complete
    nome: Mapa de Contexto (Onboarding)
    trigger_type: event
    cron/event: onboarding_completed

    1.2 O que o catálogo v2.1 exige e ainda não temos

    CRON multi-tenant configurável por usuário:
    Hoje o cron é global (mesmo horário para todos). O catálogo prevê que o usuário configure
    hora/dia por rotina. Para isso, o enqueue_routine() precisa ser chamado com base no
    trigger_config de cada client_routines — ou seja, precisamos de um dispatcher que
    leia o trigger_config.expression por cliente e compare com last_run_at.
    → Gap: o pg_cron hoje dispara globalmente. Para timezone/hora por cliente, precisamos
    de um cron dispatcher que itere client_routines e avalie should_run_now().

    Event: routine_completed (morning chain):
    O catálogo define que Sincronização da Manhã → on_success → dispara Radar de Prazos →
    on_complete → dispara Plano do Dia. O mecanismo de fire_event_for_client() já existe,
    mas não está sendo chamado ao final dos steps. O execution engine (routines.py) precisa
    de um hook on_complete_event por step ou por rotina.
    → Gap: adicionar campo on_complete.fire_event no schema de steps e lógica no engine.

    Event: calendar webhook (15 min antes):
    Preparação de Reunião exige webhook push do Google Calendar / Outlook. Não temos receiver
    para isso. Precisaria de uma Edge Function ou endpoint no agent_api que receba o push,
    calcule "evento em 15 min?", e chame fire_event_for_client('calendar_event_soon', ...).
    → Gap: novo webhook receiver + integração com Google Calendar push.

    Event: sale_approved (Emissão de NF):
    Emissão de Notas Fiscais tem trigger "on sale approval". O sistema de approval_requests
    já existe; a aprovação de uma venda precisa chamar fire_event_for_client('sale_approved').
    → Gap: adicionar fire_event_for_client no callback on_approval_completed() para
    action_type = sale_approved.



    2. FUNÇÕES DETERMINÍSTICAS — MAPEAMENTO FUNÇÃO → REGISTRO EXISTENTE

    2.1 O que existe hoje em routine_functions.py

    O registry @register("namespace.function_name") já tem:
    - analytics.query_inactive_clients — clientes sem compra em N dias
    - analytics.gather_client_context — enriquece lista com cluster label, ticket formatado
    - (demais funções a mapear nos outros namespaces registrados)

    E routine_artifacts.py tem handlers como:
    - channels.create_alert — cria alerta/card na UI (usado em todos os briefings seedados)
    - channels.send_email_batch — envia email em batch

    2.2 Funções que precisamos criar (por namespace)

    Cada item abaixo é um @register() novo em routine_functions.py ou
    routine_artifacts.py. Nomenclatura segue o padrão namespace.verb_noun.

    Namespace integrations.*
    função: integrations.check_health
    o que faz: Valida status de cada integração vs threshold de freshness. Retorna
      health_report + alert_priority.
    rotinas que usam: Sincronização da Manhã ✅ (já seedada, function existe?)
    ────────────────────────────────────────
    função: integrations.get_stale_list
    o que faz: Lista integrações com dados > N horas sem sync.
    rotinas que usam: Sincronização da Manhã

    Namespace agenda.*
    função: agenda.get_calendar_events
    o que faz: Busca eventos do calendário nas próximas N horas/dias. Retorna lista
      com attendees, subject, datetime.
    rotinas que usam: Plano do Dia ✅ (já seedada), Preparação de Reunião
    ────────────────────────────────────────
    função: agenda.get_fiscal_obligations
    o que faz: Busca obrigações fiscais do regime do CNPJ (DAS, ISS, IRPJ) nos
      próximos N dias.
    rotinas que usam: Radar de Prazos
    ────────────────────────────────────────
    função: agenda.match_attendees_to_crm
    o que faz: Cruza attendees de um evento com registros de CRM por email/nome.
    rotinas que usam: Preparação de Reunião
    ────────────────────────────────────────
    função: agenda.find_free_slots
    o que faz: Identifica blocos de 2h livres em dias com < N reuniões.
    rotinas que usam: Bloqueio de Foco

    Namespace analytics.* (além dos já existentes)
    função: analytics.get_pending_approvals
    o que faz: Lista aprovações pendentes > N horas de todas as salas.
    rotinas que usam: Plano do Dia ✅ seedada
    ────────────────────────────────────────
    função: analytics.get_kpi_snapshots
    o que faz: KPIs do dia vs baseline configurável.
    rotinas que usam: Plano do Dia ✅ seedada
    ────────────────────────────────────────
    função: analytics.get_overdue_items
    o que faz: NFs não emitidas, tarefas vencidas, follow-ups atrasados.
    rotinas que usam: Plano do Dia, Digest
    ────────────────────────────────────────
    função: analytics.get_decisions_today
    o que faz: Aprovações resolvidas hoje + ações executadas por agentes.
    rotinas que usam: Digest do Fim de Dia
    ────────────────────────────────────────
    função: analytics.score_urgency_items
    o que faz: Aplica pesos determinísticos (urgência × valor × prazo) a lista de
      itens.
    rotinas que usam: Plano do Dia
    ────────────────────────────────────────
    função: analytics.get_night_decisions
    o que faz: Itens que, se aprovados antes das 7h, desbloqueiam a manhã.
    rotinas que usam: Digest do Fim de Dia

    Namespace financeiro.*
    função: financeiro.get_bank_balance
    o que faz: Saldo confirmado no banco.
    rotinas que usam: Alerta de Fluxo
    ────────────────────────────────────────
    função: financeiro.get_payables_forecast
    o que faz: Contas a pagar próximos N dias com datas exatas.
    rotinas que usam: Alerta de Fluxo
    ────────────────────────────────────────
    função: financeiro.get_receivables_forecast
    o que faz: Contas a receber próximos N dias, ponderadas por taxa de pagamento
      histórica do cliente.
    rotinas que usam: Alerta de Fluxo
    ────────────────────────────────────────
    função: financeiro.project_daily_balance
    o que faz: Calcula saldo projetado dia-a-dia. Identifica primeiro dia abaixo do
      safety threshold.
    rotinas que usam: Alerta de Fluxo
    ────────────────────────────────────────
    função: financeiro.get_bank_transactions
    o que faz: Transações bancárias dos últimos N dias.
    rotinas que usam: Conciliação Bancária
    ────────────────────────────────────────
    função: financeiro.get_erp_invoices
    o que faz: NFs e recibos do ERP no mesmo período.
    rotinas que usam: Conciliação Bancária
    ────────────────────────────────────────
    função: financeiro.fuzzy_match_transactions
    o que faz: Match exato + near-match (valor ±1%, data ±2 dias, nome >85%) entre
      banco e ERP.
    rotinas que usam: Conciliação Bancária
    ────────────────────────────────────────
    função: financeiro.get_overdue_receivables
    o que faz: Recebíveis vencidos > N dias com perfil do cliente.
    rotinas que usam: Cobrança de Inadimplentes
    ────────────────────────────────────────
    função: financeiro.segment_debtors
    o que faz: Segmenta inadimplentes: crônico / primeira vez / high-value.
    rotinas que usam: Cobrança de Inadimplentes
    ────────────────────────────────────────
    função: financeiro.get_pl_data
    o que faz: Receita, COGS, despesas de 3 períodos (mês atual, mês anterior, mesmo
      mês ano passado).
    rotinas que usam: Relatório Mensal
    ────────────────────────────────────────
    função: financeiro.calculate_pl
    o que faz: Calcula P&L, margem bruta, margem líquida, variação MoM e YoY.
    rotinas que usam: Relatório Mensal
    ────────────────────────────────────────
    função: financeiro.calculate_burn_rate
    o que faz: Custos fixos mensais ÷ caixa final.
    rotinas que usam: Relatório Mensal
    ────────────────────────────────────────
    função: financeiro.get_margin_by_sku
    o que faz: Margem atual vs trimestre anterior por SKU.
    rotinas que usam: Revisão de Margem
    ────────────────────────────────────────
    função: financeiro.calculate_margin_delta
    o que faz: Delta % por SKU, determina causa (custo subiu / preço caiu / mix).
    rotinas que usam: Revisão de Margem
    ────────────────────────────────────────
    função: financeiro.calculate_das
    o que faz: Calcula DAS (MEI fixo / Simples Nacional com alíquota por faixa de
      RBT12).
    rotinas que usam: DAS / Simples Nacional

    Namespace compras.*
    função: compras.get_inventory_levels
    o que faz: Estoque atual por SKU.
    rotinas que usam: Alerta de Estoque, Sugestão de Compra, Auditoria
    ────────────────────────────────────────
    função: compras.get_sales_velocity
    o que faz: Unidades/dia nos últimos N dias, com ajuste de tendência.
    rotinas que usam: Alerta de Estoque, Sugestão de Compra
    ────────────────────────────────────────
    função: compras.get_supplier_lead_times
    o que faz: Prazo de entrega por fornecedor.
    rotinas que usam: Alerta de Estoque, Sugestão de Compra
    ────────────────────────────────────────
    função: compras.calculate_reorder_points
    o que faz: Auto-calcula ponto de reorder = (velocidade × lead time) + safety
      stock.
    rotinas que usam: Alerta de Estoque
    ────────────────────────────────────────
    função: compras.predict_stockout_date
    o que faz: Prevê data de ruptura: estoque_atual ÷ velocidade.
    rotinas que usam: Sugestão de Compra
    ────────────────────────────────────────
    função: compras.consolidate_purchase_orders
    o que faz: Agrupa SKUs por fornecedor em rascunhos de PO.
    rotinas que usam: Sugestão de Compra
    ────────────────────────────────────────
    função: compras.get_supplier_invoices
    o que faz: Notas de compra dos últimos 90 dias.
    rotinas que usam: Revisão de Fornecedores
    ────────────────────────────────────────
    função: compras.analyze_supplier_performance
    o que faz: Regressão linear em preço; delta prazo entrega; mudança de condições.
    rotinas que usam: Revisão de Fornecedores
    ────────────────────────────────────────
    função: compras.cross_check_inventory
    o que faz: Confronta sistema vs contagem física; calcula discrepâncias.
    rotinas que usam: Auditoria de Estoque

    Namespace clientes.*
    função: clientes.get_postsale_targets
    o que faz: Clientes com compra exatamente N dias atrás (sem follow-up esta
      semana).
    rotinas que usam: Follow-up Pós-Venda
    ────────────────────────────────────────
    função: clientes.get_dormant_clients
    o que faz: Clientes sem compra > N dias com LTV e segmento.
    rotinas que usam: Reativação
    ────────────────────────────────────────
    função: clientes.segment_by_ltv
    o que faz: Segmenta por tier (high/medium/low) para ação diferenciada.
    rotinas que usam: Reativação, Cobrança
    ────────────────────────────────────────
    função: clientes.get_vip_birthdays
    o que faz: Aniversários / datas de fundação de clientes VIP (top 20% receita) de
      hoje.
    rotinas que usam: Aniversário VIP
    ────────────────────────────────────────
    função: clientes.get_survey_responses
    o que faz: Respostas NPS do último mês (score + texto).
    rotinas que usam: NPS / Satisfação
    ────────────────────────────────────────
    função: clientes.calculate_nps
    o que faz: % promotores - % detratores; keyword frequency; urgency flag (score ≤6
      + palavras negativas).
    rotinas que usam: NPS / Satisfação
    ────────────────────────────────────────
    função: clientes.get_stalled_pipeline
    o que faz: Oportunidades sem atividade > N dias com valor e estágio.
    rotinas que usam: Pipeline Review
    ────────────────────────────────────────
    função: clientes.suggest_pipeline_action
    o que faz: Regra determinística por estágio: proposta / follow-up / desconto /
      qualificar.
    rotinas que usam: Pipeline Review
    ────────────────────────────────────────
    função: clientes.get_customer_history
    o que faz: Histórico de compras, NFs em aberto, últimos touchpoints de um cliente.
    rotinas que usam: Preparação de Reunião

    Namespace documentos.*
    função: documentos.get_sales_without_nf
    o que faz: Vendas aprovadas sem NF emitida.
    rotinas que usam: Emissão de NF
    ────────────────────────────────────────
    função: documentos.populate_nf_fields
    o que faz: Calcula impostos (ISS/ICMS/IPI/PIS/COFINS) por regime e NCM/CFOP.
      Retorna XML pre-validado.
    rotinas que usam: Emissão de NF
    ────────────────────────────────────────
    função: documentos.validate_nf_xml
    o que faz: Valida XML contra spec SEFAZ (regras determinísticas).
    rotinas que usam: Emissão de NF
    ────────────────────────────────────────
    função: documentos.get_nf_sefaz
    o que faz: NFs emitidas via SEFAZ dos últimos N dias (por chave de acesso).
    rotinas que usam: Validação XML
    ────────────────────────────────────────
    função: documentos.cross_check_nf_erp
    o que faz: Confronta SEFAZ vs ERP; identifica gaps e cancelamentos.
    rotinas que usam: Validação XML
    ────────────────────────────────────────
    função: documentos.get_expiring_contracts
    o que faz: Contratos com vencimento nos próximos 30/60 dias com flag de
      auto-renovação.
    rotinas que usam: Revisão de Contratos
    ────────────────────────────────────────
    função: documentos.get_obsolete_customer_data
    o que faz: Registros com last_activity > 3 anos, excluindo legal hold e retenção
      fiscal.
    rotinas que usam: LGPD

    Namespace estrategia.*
    função: estrategia.get_business_timeseries
    o que faz: Séries temporais de 12 meses: vendas, marketing, estoque, CAC.
    rotinas que usam: Padrões Escondidos
    ────────────────────────────────────────
    função: estrategia.run_lagged_correlation
    o que faz: Pearson/Spearman com lags 1-30 dias; filtra p-value < 0.2.
    rotinas que usam: Padrões Escondidos
    ────────────────────────────────────────
    função: estrategia.get_goals_vs_actuals
    o que faz: Metas configuradas vs realizado do mês fechado.
    rotinas que usam: Revisão de Metas
    ────────────────────────────────────────
    função: estrategia.calculate_seasonality_index
    o que faz: Mesmo mês dos últimos 3 anos vs média anual.
    rotinas que usam: Revisão de Metas
    ────────────────────────────────────────
    função: estrategia.get_competitor_prices
    o que faz: Preços de fontes web configuradas vs próprios preços.
    rotinas que usam: Análise de Mercado
    ────────────────────────────────────────
    função: estrategia.get_industry_news
    o que faz: Feeds RSS/configurados filtrados por relevância.
    rotinas que usam: Análise de Mercado

    Namespace channels.* (artifacts — efeitos colaterais)
    artifact: channels.create_alert
    o que faz: Cria card na UI (room + surface + priority). ✅ Já existe
    usado em: Todos os briefings
    ────────────────────────────────────────
    artifact: channels.send_message_batch
    o que faz: Envia mensagens (email/WhatsApp) em batch para lista de clientes.
    usado em: Cobrança, Follow-up, Reativação, Aniversário VIP
    ────────────────────────────────────────
    artifact: channels.submit_nf_sefaz
    o que faz: Submete XML para SEFAZ e registra no ERP.
    usado em: Emissão de NF
    ────────────────────────────────────────
    artifact: channels.create_calendar_event
    o que faz: Cria evento no calendário (Bloqueio de Foco).
    usado em: Bloqueio de Foco
    ────────────────────────────────────────
    artifact: channels.fire_routine_event
    o que faz: Chama fire_event_for_client() ao final de um step — morning chain.
    usado em: Sincronização → Radar → Plano



    3. SKILLS (LLM) — QUAIS ROTINAS PRECISAM E POR QUÊ

    O engine de rotinas já suporta type: "skill" como step. A SkillFactory (blu_agent_framework)
    é invocada com um task_template que pode referenciar outputs dos steps anteriores via {{key}}.

    3.1 Rotinas que precisam de skill (step LLM)

    Rotina: Plano do Dia
    Skill name (proposto): routines.daily_briefing
    O que o LLM faz: Redige narrativa do briefing; categoriza itens em
      Decidir/Executar/Acompanhar; adiciona tom de segunda-feira se aplicável.
    Inputs do state: pending_items, kpi_summary, calendar_events, overdue_items,
      deadline_buckets
    ────────────────────────────────────────
    Rotina: Digest do Fim de Dia
    Skill name (proposto): routines.end_of_day_digest
    O que o LLM faz: Redige "Hoje no escritório" + "Para amanhã" + "Decisões noturnas"
      em linguagem natural.
    Inputs do state: decisions_today, actions_today, pending_tomorrow, night_decisions
    ────────────────────────────────────────
    Rotina: Resumo Semanal
    Skill name (proposto): routines.weekly_summary
    O que o LLM faz: Narrativa com tendências semana-a-semana; top 3 bloqueios para
      segunda; prévia do calendário.
    Inputs do state: decision_log, financial_movement, customer_touchpoints, blockers,
      monday_preview
    ────────────────────────────────────────
    Rotina: Cobrança de Inadimplentes
    Skill name (proposto): routines.collections_draft
    O que o LLM faz: Redige mensagem personalizada por segmento (crônico / primeira
      vez / high-value).
    Inputs do state: client_profile, invoice_list, days_overdue, segment, channel
    ────────────────────────────────────────
    Rotina: Follow-up Pós-Venda
    Skill name (proposto): routines.postsale_followup
    O que o LLM faz: Personaliza template por produto e perfil do cliente.
    Inputs do state: customer_name, product_name, purchase_date, category
    ────────────────────────────────────────
    Rotina: Reativação de Clientes Dormidos
    Skill name (proposto): routines.reactivation_draft
    O que o LLM faz: Redige oferta de win-back por tier (call pessoal / desconto /
      soft reengagement).
    Inputs do state: client_list, segment, days_inactive, ltv_tier
    ────────────────────────────────────────
    Rotina: Preparação de Reunião
    Skill name (proposto): routines.meeting_prep
    O que o LLM faz: Monta brief contextual: quem é, o que tem aberto, agenda
      sugerida.
    Inputs do state: attendees, customer_history, open_invoices, last_touchpoints
    ────────────────────────────────────────
    Rotina: Padrões Escondidos
    Skill name (proposto): routines.hidden_patterns
    O que o LLM faz: Explica correlação estatística em linguagem natural; sugere
      experimento para validar.
    Inputs do state: correlation_results, business_context
    ────────────────────────────────────────
    Rotina: Análise de Concorrência / Mercado
    Skill name (proposto): routines.market_analysis
    O que o LLM faz: Sumariza news por impacto; compara preços; sugere resposta.
    Inputs do state: competitor_prices, own_prices, news_items

    Total: 9 skills a criar no SKILL_REGISTRY.

    3.2 Rotinas 100% determinísticas (sem step LLM)

    Todas as demais 17 rotinas do catálogo rodam como puro function + artifact.
    Nenhuma chamada LLM — só dados, cálculos e cards. Isso é intencional para custo e latência.

    Rotina: Sincronização da Manhã
    Steps: integrations.check_health → channels.create_alert +
      channels.fire_routine_event
    ────────────────────────────────────────
    Rotina: Radar de Prazos
    Steps: agenda.get_calendar_events + agenda.get_fiscal_obligations +
      documentos.get_expiring_contracts → categorize → channels.create_alert +
      channels.fire_routine_event
    ────────────────────────────────────────
    Rotina: Alerta de Fluxo de Caixa
    Steps: financeiro.get_bank_balance → financeiro.get_payables_forecast →
      financeiro.get_receivables_forecast → financeiro.project_daily_balance →
      channels.create_alert (condicional)
    ────────────────────────────────────────
    Rotina: Conciliação Bancária
    Steps: financeiro.get_bank_transactions + financeiro.get_erp_invoices →
      financeiro.fuzzy_match_transactions → channels.create_alert (approval card por
      item)
    ────────────────────────────────────────
    Rotina: Cobrança de Inadimplentes
    Steps: financeiro.get_overdue_receivables → financeiro.segment_debtors → skill →
      channels.create_alert (batch approval)
    ────────────────────────────────────────
    Rotina: Revisão de Margem
    Steps: financeiro.get_margin_by_sku → financeiro.calculate_margin_delta →
      channels.create_alert
    ────────────────────────────────────────
    Rotina: DAS / Simples Nacional
    Steps: financeiro.calculate_das → channels.create_alert (approval)
    ────────────────────────────────────────
    Rotina: Relatório Mensal
    Steps: financeiro.get_pl_data → financeiro.calculate_pl +
      financeiro.calculate_burn_rate → channels.create_alert
    ────────────────────────────────────────
    Rotina: Alerta de Estoque Mínimo
    Steps: compras.get_inventory_levels + compras.get_sales_velocity →
      compras.calculate_reorder_points → channels.create_alert
    ────────────────────────────────────────
    Rotina: Sugestão de Compra
    Steps: compras.predict_stockout_date → compras.consolidate_purchase_orders →
      channels.create_alert (approval)
    ────────────────────────────────────────
    Rotina: Revisão de Fornecedores
    Steps: compras.get_supplier_invoices → compras.analyze_supplier_performance →
      channels.create_alert
    ────────────────────────────────────────
    Rotina: Auditoria de Estoque
    Steps: compras.cross_check_inventory → channels.create_alert (condicional)
    ────────────────────────────────────────
    Rotina: Aniversário de Cliente VIP
    Steps: clientes.get_vip_birthdays → channels.create_alert
    ────────────────────────────────────────
    Rotina: NPS / Satisfação Leitura
    Steps: clientes.get_survey_responses → clientes.calculate_nps →
      channels.create_alert
    ────────────────────────────────────────
    Rotina: Pipeline de Vendas Review
    Steps: clientes.get_stalled_pipeline → clientes.suggest_pipeline_action →
      channels.create_alert (approval)
    ────────────────────────────────────────
    Rotina: Emissão de Notas Fiscais
    Steps: documentos.get_sales_without_nf → documentos.populate_nf_fields →
      documentos.validate_nf_xml → channels.create_alert (approval)
    ────────────────────────────────────────
    Rotina: Validação de XML / Escrituração
    Steps: documentos.get_nf_sefaz + documentos.cross_check_nf_erp →
      channels.create_alert (condicional)
    ────────────────────────────────────────
    Rotina: Revisão de Contratos a Vencer
    Steps: documentos.get_expiring_contracts → channels.create_alert (approval por
      contrato)
    ────────────────────────────────────────
    Rotina: LGPD — Revisão de Dados Obsoletos
    Steps: documentos.get_obsolete_customer_data → channels.create_alert (NUNCA
      auto-deleta)
    ────────────────────────────────────────
    Rotina: Bloqueio de Foco
    Steps: agenda.get_calendar_events → agenda.find_free_slots → channels.create_alert
      (approval) → channels.create_calendar_event



    5. SYSTEM vs BUILT-IN vs OPTIONAL — CLASSIFICAÇÃO DEFINITIVA

    5.1 Critério de classificação

    - SYSTEM: roda para todos os clientes sem nenhuma ação. Se a integração não existe,
      a rotina reporta "desconectado" mas não falha. Não aparece na UI de configuração —
      é infraestrutura do bureau.
    - BUILT-IN: vem ativa por padrão via auto_enroll_catalog_routines(). Aparece na
      UI em "Rotinas ativas". O usuário pode pausar, mudar cadência ou ajustar threshold
      mínimo. Requer mínima ou nenhuma configuração.
    - OPTIONAL: o usuário ativa explicitamente, geralmente porque precisa configurar
      integrações ou parâmetros de negócio antes de fazer sentido.

    5.2 Tabela de classificação

    Rotina: Sincronização da Manhã
    Classificação: SYSTEM
    Config mínima: Nenhuma
    Observação: Dispara a cadeia. Sempre roda.
    ────────────────────────────────────────
    Rotina: Radar de Prazos
    Classificação: SYSTEM
    Config mínima: Nenhuma
    Observação: Triggered por Sincronização.
    ────────────────────────────────────────
    Rotina: Aniversário de Cliente VIP
    Classificação: SYSTEM
    Config mínima: Nenhuma
    Observação: Só lê datas. Silencioso se sem VIPs.
    ────────────────────────────────────────
    Rotina: Validação de XML / Escrituração
    Classificação: SYSTEM
    Config mínima: Nenhuma
    Observação: Compliance. Silencioso se clean.
    ────────────────────────────────────────
    Rotina: LGPD — Revisão de Dados Obsoletos
    Classificação: SYSTEM
    Config mínima: Nenhuma
    Observação: Quarterly. Nunca auto-deleta.
    ────────────────────────────────────────
    Rotina: Auditoria de Estoque
    Classificação: SYSTEM
    Config mínima: Nenhuma
    Observação: Mensal. Silencioso se clean.
    ────────────────────────────────────────
    Rotina: Plano do Dia
    Classificação: BUILT-IN
    Config mínima: Hora (via cadeia)
    Observação: ON por default.
    ────────────────────────────────────────
    Rotina: Digest do Fim de Dia
    Classificação: BUILT-IN
    Config mínima: Hora
    Observação: ON por default.
    ────────────────────────────────────────
    Rotina: Resumo Semanal
    Classificação: BUILT-IN
    Config mínima: Dia + hora
    Observação: ON por default.
    ────────────────────────────────────────
    Rotina: Alerta de Fluxo de Caixa
    Classificação: BUILT-IN
    Config mínima: Saldo mínimo em R$
    Observação: Pede config na ativação.
    ────────────────────────────────────────
    Rotina: Conciliação Bancária Sugerida
    Classificação: BUILT-IN
    Config mínima: Dia da semana
    Observação: ON por default (segunda).
    ────────────────────────────────────────
    Rotina: Relatório Mensal de Performance
    Classificação: BUILT-IN
    Config mínima: Dia do mês
    Observação: ON por default (dia 1).
    ────────────────────────────────────────
    Rotina: Cobrança de Inadimplentes
    Classificação: BUILT-IN
    Config mínima: Dias de atraso threshold
    Observação: Default: 15 dias.
    ────────────────────────────────────────
    Rotina: Alerta de Estoque Mínimo
    Classificação: BUILT-IN
    Config mínima: Auto-learn (zero config)
    Observação: ON por default.
    ────────────────────────────────────────
    Rotina: Sugestão de Compra
    Classificação: BUILT-IN
    Config mínima: Dia da semana
    Observação: ON por default (terça).
    ────────────────────────────────────────
    Rotina: Follow-up Pós-Venda
    Classificação: BUILT-IN
    Config mínima: Dias após compra
    Observação: Default: 7 dias.
    ────────────────────────────────────────
    Rotina: Pipeline de Vendas Review
    Classificação: BUILT-IN
    Config mínima: Threshold dias parado
    Observação: Default: 14 dias.
    ────────────────────────────────────────
    Rotina: Preparação de Reunião
    Classificação: BUILT-IN
    Config mínima: Nenhuma
    Observação: Depende de calendar integrado.
    ────────────────────────────────────────
    Rotina: Emissão de Notas Fiscais
    Classificação: BUILT-IN
    Config mínima: Regime fiscal + modo
    Observação: Obrigatório configurar regime.
    ────────────────────────────────────────
    Rotina: Bloqueio de Foco
    Classificação: BUILT-IN
    Config mínima: Dias preferidos + faixas
    Observação: Default: dias com < 2 reuniões.
    ────────────────────────────────────────
    Rotina: Revisão de Margem
    Classificação: OPTIONAL
    Config mínima: Nenhuma
    Observação: Ativa via UI.
    ────────────────────────────────────────
    Rotina: DAS / Simples Nacional
    Classificação: OPTIONAL
    Config mínima: Regime (MEI ou Simples)
    Observação: Só para regimes específicos.
    ────────────────────────────────────────
    Rotina: Revisão de Fornecedores
    Classificação: OPTIONAL
    Config mínima: Nenhuma
    Observação: Faz sentido após 3 meses de dados.
    ────────────────────────────────────────
    Rotina: Reativação de Clientes Dormidos
    Classificação: OPTIONAL
    Config mínima: Threshold inatividade
    Observação: Default: 90 dias.
    ────────────────────────────────────────
    Rotina: NPS / Satisfação Leitura
    Classificação: OPTIONAL
    Config mínima: Integração com pesquisa
    Observação: Depende de ferramenta externa.
    ────────────────────────────────────────
    Rotina: Revisão de Contratos a Vencer
    Classificação: OPTIONAL
    Config mínima: Nenhuma
    Observação: Depende de docs carregados.
    ────────────────────────────────────────
    Rotina: Padrões Escondidos
    Classificação: OPTIONAL
    Config mínima: Nenhuma
    Observação: Precisa de 12 meses de dados.
    ────────────────────────────────────────
    Rotina: Revisão de Metas vs. Realidade
    Classificação: OPTIONAL
    Config mínima: Metas configuradas (ou sem)
    Observação: Funciona sem metas (sugere).
    ────────────────────────────────────────
    Rotina: Análise de Concorrência / Mercado
    Classificação: OPTIONAL
    Config mínima: Keywords + fontes
    Observação: Não faz sentido sem configuração.



    6. GAPS IDENTIFICADOS

    6.1 Scheduler per-tenant
    O pg_cron hoje dispara globalmente. Para suportar horários diferentes por cliente (fuso,
    preferência de horário), o dispatcher precisa ser uma função SQL ou worker Python que:
    1. Lê client_routines WHERE trigger_type = 'cron' AND active = true AND status = 'active'
    2. Avalia se cron_expression + last_run_at + timezone do cliente implica "deve rodar agora"
    3. Chama enqueue_routine() para cada cliente elegível
    O job de pg_cron (every minute) já existe e chama o dispatcher HTTP — precisamos adaptar
    a lógica dentro do agent_api para fazer essa iteração per-cliente.

    6.2 On_complete hook para morning chain
    O campo steps[].on_complete.fire_event não existe no schema atual. Precisamos:
    - Adicionar ao schema de steps: "on_complete": {"fire_event": "event_type", "pass_keys": ["key1"]}
    - No execution engine (routines.py), após cada step com sucesso, verificar se
      on_complete.fire_event está definido e chamar fire_event_for_client() com os
      outputs selecionados como trigger_data.

    6.3 Calendar webhook receiver
    Preparação de Reunião depende de push do Google Calendar / Outlook. Precisamos:
    - Endpoint no agent_api (ou Edge Function) que receba push notification
    - Lógica: "evento começa em ≤ 15 min?" → fire_event_for_client('calendar_event_soon', {event_data})
    - OAuth scope: https://www.googleapis.com/auth/calendar.readonly + watch channel

    6.4 Sale_approved event trigger
    O on_approval_completed() (SQL trigger / Python callback) precisa verificar se
    action_type = 'sale_approved' e chamar fire_event_for_client('sale_approved', {sale_data}).
    Emissão de NF está à espera disso.

    6.5 Approval card com context rico
    A tabela approval_requests já tem title, body, priority, payload. O que falta
    é um schema padronizado para cards de aprovação de rotinas com:
    - Preview de mensagem/documento (para Cobrança, Follow-up, NF)
    - Ações granulares: aprovar_todos / editar_individual / rejeitar / snooze(N dias)
    - Expiração automática (campo expires_at já existe)
    O engine já checa _has_pending_approvals_sync() antes de completar a execução.
    Falta o componente de UI para renderizar esses cards com ações granulares.

    6.6 Função channels.fire_routine_event
    O artifact que dispara o próximo elo da cadeia (Sincronização → Radar → Plano) não
    existe como artifact registrado. Precisa ser criado em routine_artifacts.py:
    python
    @register("channels.fire_routine_event")
    async def _fire_routine_event(inputs: dict, client_id: str) -> dict:
        event_type = inputs["event_type"]
        trigger_data = inputs.get("trigger_data", {})
        count = await call_rpc("fire_event_for_client", {
            "p_event_type": event_type,
            "p_client_id": client_id,
            "p_trigger_data": trigger_data,
        })
        return {"fired_count": count}


    6.7 Funções de fetch de dados reais (integrações externas)
    As funções de namespace financeiro., compras., clientes.* listadas na seção 2
    precisam ser implementadas. Hoje temos funções que leem do schema analytics_v2
    (dados já ingeridos). As funções de rotinas precisarão:
    - Ler de analytics_v2 para dados agregados (já disponível)
    - Ler de integrações ao vivo (banco, ERP, SEFAZ) via credencial_servico_externo +
      adaptadores em blu_data_connectors
    - O padrão _call_mcp_tool() já existe no routine_functions.py — funções podem
      delegar para tools do tool_pool_api onde a lógica já existir



    Fim do documento — próximo passo: discutir gaps e prioridade de implementação.
