-- ─────────────────────────────────────────────────────────────────────────────
-- Migrate all routine steps from type=llm (Langfuse chat prompt) to
-- type=skill (agent-skill dispatch via AgentTypeRegistry + SkillFactory).
--
-- All prompts now live as builtin fallback templates in
-- blu_prompt_management/templates.py (skill:*:system keys) and can optionally
-- be overridden in Langfuse. The llm step type is deprecated.
--
-- Mapping:
--   collection_overdue   gen_messages       → skill  crm   / collection_messages
--   sales_followup       gen_followup        → skill  crm   / followup_draft
--   client_reactivation  gen_reactivation    → skill  crm   / reactivation_proposal
--   satisfaction_survey  gen_survey          → skill  crm   / satisfaction_survey
--   meeting_prep         gen_brief           → skill  agenda / meeting_brief
--   hidden_patterns      detect_patterns     → skill  estrategia / hidden_patterns
--   competitor_analysis  gen_analysis        → skill  estrategia / competitor_analysis
--
-- Also wires L3 narrative skills into routines that previously went straight
-- to artifact without an LLM step:
--   daily_briefing    → morning_plan  skill (crm/estrategia → planner picks it)
--   end_of_day_digest → end_of_day_digest skill
--   weekly_summary    → weekly_summary skill
-- ─────────────────────────────────────────────────────────────────────────────


-- ── collection_overdue — gen_messages: llm → skill/crm ───────────────────────
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_overdue",
    "step": 1,
    "type": "function",
    "function": "analytics.get_overdue_customers",
    "inputs": {"min_dias": "{{min_dias_atraso}}", "max_results": 50},
    "on_failure": "halt"
  },
  {
    "id": "gen_messages",
    "step": 2,
    "type": "skill",
    "skill_slug": "crm",
    "task_template": "Gere mensagens de cobrança personalizadas para os clientes inadimplentes da {{nome_empresa}}.\n\nTom solicitado: {{tom}}\n\nClientes em atraso:\n{{overdue_list}}\n\nPara cada cliente gere uma mensagem de cobrança com o tom indicado. Inclua valor em aberto, dias de atraso e uma chamada à ação clara.",
    "outputs": {"mensagens": "lista de mensagens de cobrança por cliente"},
    "on_failure": "continue"
  },
  {
    "id": "approval",
    "step": 3,
    "type": "approval",
    "inputs": {
      "title": "💰 Revisar Cobranças — {{overdue_count}} clientes",
      "body": "{{mensagens}}",
      "priority": "normal"
    },
    "on_failure": "continue"
  },
  {
    "id": "push_card",
    "step": 4,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "💰 Cobranças Aprovadas",
      "body": "{{overdue_count}} mensagens de cobrança aprovadas e prontas para envio.\n\n{{mensagens}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'collection_overdue';


-- ── sales_followup — gen_followup: llm → skill/crm ──────────────────────────
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_pipeline",
    "step": 1,
    "type": "function",
    "function": "analytics.get_client_pipeline",
    "inputs": {"segment": "ativos"},
    "on_failure": "continue"
  },
  {
    "id": "gen_followup",
    "step": 2,
    "type": "skill",
    "skill_slug": "crm",
    "task_template": "Crie uma mensagem de follow-up de vendas para os clientes ativos da {{nome_empresa}}.\n\nPipeline atual:\n{{pipeline_summary}}\n\n{% if incluir_crosssell %}Inclua sugestões de cross-sell relevantes com base nos produtos já adquiridos.{% endif %}\n\nGere uma mensagem personalizada, calorosa e com próximo passo claro.",
    "outputs": {"followup_mensagem": "mensagem de follow-up pronta para envio"},
    "on_failure": "continue"
  },
  {
    "id": "push_card",
    "step": 3,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "📩 Follow-up de Venda",
      "body": "{{followup_mensagem}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'sales_followup';


-- ── client_reactivation — gen_reactivation: llm → skill/crm ─────────────────
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_pipeline",
    "step": 1,
    "type": "function",
    "function": "analytics.get_client_pipeline",
    "inputs": {"segment": "inativos"},
    "on_failure": "halt"
  },
  {
    "id": "gen_reactivation",
    "step": 2,
    "type": "skill",
    "skill_slug": "crm",
    "task_template": "Elabore propostas de reativação para clientes inativos da {{nome_empresa}}.\n\nClientes inativos (min {{min_dias_inatividade}} dias sem compra):\n{{pipeline_summary}}\n\n{% if incluir_proposta %}Para cada cliente inclua uma proposta especial ou desconto personalizado.{% endif %}\n\nGere uma mensagem por cliente com tom amigável e proposta de retorno concreta.",
    "outputs": {"propostas": "lista de propostas de reativação por cliente"},
    "on_failure": "continue"
  },
  {
    "id": "push_card",
    "step": 3,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "🔄 Reativação de Clientes",
      "body": "{{pipeline_summary}}\n\nPropostas geradas para clientes inativos.\n\n{{propostas}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'client_reactivation';


-- ── satisfaction_survey — gen_survey: llm → skill/crm ───────────────────────
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_nps",
    "step": 1,
    "type": "function",
    "function": "analytics.get_nps_data",
    "inputs": {},
    "on_failure": "continue"
  },
  {
    "id": "gen_survey",
    "step": 2,
    "type": "skill",
    "skill_slug": "crm",
    "task_template": "Crie uma mensagem de pesquisa de satisfação para os clientes da {{nome_empresa}}.\n\nDados NPS recentes:\n{{nps_summary}}\n\nO pedido foi entregue. Gere uma mensagem curta, cordial e com link/instrução para avaliar a experiência. Adapte o tom ao contexto da entrega.",
    "outputs": {"survey_mensagem": "mensagem de pesquisa de satisfação"},
    "on_failure": "continue"
  },
  {
    "id": "push_card",
    "step": 3,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "⭐ Pesquisa de Satisfação",
      "body": "{{survey_mensagem}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'satisfaction_survey';


-- ── meeting_prep — gen_brief: llm → skill/agenda ────────────────────────────
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_meetings",
    "step": 1,
    "type": "function",
    "function": "agenda.get_upcoming_meetings",
    "inputs": {"hours_ahead": 24},
    "on_failure": "halt"
  },
  {
    "id": "get_participant_ctx",
    "step": 2,
    "type": "function",
    "function": "web.get_meeting_participant_context",
    "inputs": {"reunioes": "{{reunioes}}"},
    "on_failure": "continue"
  },
  {
    "id": "gen_brief",
    "step": 3,
    "type": "skill",
    "skill_slug": "agenda",
    "task_template": "Prepare briefings executivos para as reuniões da {{nome_empresa}} nas próximas 24h.\n\nReuniões agendadas:\n{{reunioes}}\n\nContexto dos participantes:\n{{participant_context}}\n\nPara cada reunião gere: objetivo provável, pontos de atenção, perguntas sugeridas e contexto relevante dos participantes.",
    "outputs": {"briefings": "briefings executivos das reuniões"},
    "on_failure": "continue"
  },
  {
    "id": "push_card",
    "step": 4,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "📋 Prep Reunião",
      "body": "{{meeting_count}} reunião(ões) nas próximas 24h.\n\n{{briefings}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'meeting_prep';


-- ── hidden_patterns — detect_patterns: llm → skill/estrategia ───────────────
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_performance",
    "step": 1,
    "type": "function",
    "function": "analytics.get_sales_performance",
    "inputs": {},
    "on_failure": "halt"
  },
  {
    "id": "detect_patterns",
    "step": 2,
    "type": "skill",
    "skill_slug": "estrategia",
    "task_template": "Analise os dados de desempenho da {{nome_empresa}} e identifique padrões não óbvios que podem gerar vantagem competitiva.\n\nDados de performance:\n{{performance_summary}}\n\nBusque: correlações inesperadas entre produtos/clientes/períodos, sazonalidades ocultas, segmentos de clientes sub-atendidos, anomalias positivas replicáveis.",
    "outputs": {"analise_padroes": "análise de padrões escondidos com recomendações"},
    "on_failure": "continue"
  },
  {
    "id": "push_card",
    "step": 3,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "🔍 Padrões Escondidos",
      "body": "{{performance_summary}}\n\n{{analise_padroes}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'hidden_patterns';


-- ── competitor_analysis — gen_analysis: llm → skill/estrategia ──────────────
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_performance",
    "step": 1,
    "type": "function",
    "function": "analytics.get_sales_performance",
    "inputs": {},
    "on_failure": "continue"
  },
  {
    "id": "crawl_competitors",
    "step": 2,
    "type": "function",
    "function": "web.crawl_competitor_pages",
    "inputs": {"concorrentes": "{{concorrentes}}"},
    "on_failure": "continue"
  },
  {
    "id": "gen_analysis",
    "step": 3,
    "type": "skill",
    "skill_slug": "estrategia",
    "task_template": "Faça uma análise competitiva para a {{nome_empresa}}.\n\nDesempenho interno:\n{{performance_summary}}\n\nInformações dos concorrentes coletadas:\n{{competitor_data}}\n\nGere: posicionamento relativo, ameaças imediatas, oportunidades de diferenciação e ações recomendadas para o próximo mês.",
    "outputs": {"analise_concorrencia": "análise competitiva com recomendações"},
    "on_failure": "continue"
  },
  {
    "id": "push_card",
    "step": 4,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "🏁 Análise de Concorrência",
      "body": "{{analise_concorrencia}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'competitor_analysis';


-- ── daily_briefing — insert morning_plan skill step before artifact ──────────
-- Was: function→function→function→artifact
-- Now: function→function→function→skill(morning_plan)→artifact
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_pending",
    "step": 1,
    "type": "function",
    "function": "analytics.get_pending_approvals",
    "inputs": {"limit": 5},
    "on_failure": "continue"
  },
  {
    "id": "get_kpis",
    "step": 2,
    "type": "function",
    "function": "analytics.get_kpi_snapshots",
    "inputs": {"window_days": 1, "baseline_days": 7},
    "on_failure": "continue"
  },
  {
    "id": "get_agenda",
    "step": 3,
    "type": "function",
    "function": "agenda.get_calendar_events",
    "inputs": {"window_hours": 18},
    "on_failure": "continue"
  },
  {
    "id": "gen_plan",
    "step": 4,
    "type": "skill",
    "skill_slug": "estrategia",
    "task_template": "Gere o plano do dia para a {{nome_empresa}}.\n\nKPIs de hoje vs semana anterior:\n{{kpi_summary}}\n\nAgenda:\n{{calendar_summary}}\n\nAprovações pendentes:\n{{pending_summary}}\n\nGere uma narrativa de planejamento diário: prioridades do dia, alertas de atenção e próximos passos. Tom executivo, conciso.",
    "outputs": {"plano_do_dia": "narrativa do plano do dia"},
    "on_failure": "continue"
  },
  {
    "id": "alert",
    "step": 5,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "☀️ Plano do Dia",
      "body": "{{plano_do_dia}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'daily_briefing';


-- ── end_of_day_digest — insert end_of_day_digest skill step before artifact ──
-- Was: function→function→artifact
-- Now: function→function→skill(end_of_day_digest)→artifact
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_activity",
    "step": 1,
    "type": "function",
    "function": "analytics.get_daily_activity",
    "inputs": {},
    "on_failure": "continue"
  },
  {
    "id": "get_pending",
    "step": 2,
    "type": "function",
    "function": "analytics.get_pending_approvals",
    "inputs": {"limit": 5},
    "on_failure": "continue"
  },
  {
    "id": "gen_digest",
    "step": 3,
    "type": "skill",
    "skill_slug": "estrategia",
    "task_template": "Gere o digest do fim do dia para a {{nome_empresa}}.\n\nAtividade do dia:\n{{activity_summary}}\n\nPendências para amanhã:\n{{pending_summary}}\n\nResuma o dia: o que foi feito, o que ficou pendente e os principais alertas para amanhã. Tom reflexivo e orientado a ação.",
    "outputs": {"digest_do_dia": "narrativa do digest do fim do dia"},
    "on_failure": "continue"
  },
  {
    "id": "alert",
    "step": 4,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "🌅 Digest do Dia",
      "body": "{{digest_do_dia}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'end_of_day_digest';


-- ── weekly_summary — insert weekly_summary skill step before artifact ─────────
-- Was: function→function→artifact
-- Now: function→function→skill(weekly_summary)→artifact
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "get_kpis",
    "step": 1,
    "type": "function",
    "function": "analytics.get_kpi_snapshots",
    "inputs": {"window_days": 7, "baseline_days": 30},
    "on_failure": "continue"
  },
  {
    "id": "get_activity",
    "step": 2,
    "type": "function",
    "function": "analytics.get_daily_activity",
    "inputs": {},
    "on_failure": "continue"
  },
  {
    "id": "gen_summary",
    "step": 3,
    "type": "skill",
    "skill_slug": "estrategia",
    "task_template": "Gere o resumo semanal executivo da {{nome_empresa}}.\n\nKPIs da semana vs mês anterior:\n{{kpi_summary}}\n\nAtividade semanal:\n{{activity_summary}}\n\nGere: destaques da semana (positivos e negativos), tendências identificadas, metas da próxima semana. Formato executivo com bullets e métricas.",
    "outputs": {"resumo_semanal": "narrativa do resumo semanal executivo"},
    "on_failure": "continue"
  },
  {
    "id": "alert",
    "step": 4,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "📊 Resumo Semanal",
      "body": "{{resumo_semanal}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt"
  }
]'::jsonb
WHERE id = 'weekly_summary';
