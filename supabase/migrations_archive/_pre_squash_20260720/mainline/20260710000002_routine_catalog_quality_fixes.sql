-- Fixes de qualidade no catálogo de rotinas (rodada completa 2026-07-10):
--
-- 1. collection_overdue.gen_messages referenciava {{overdue_list}}, mas a
--    função analytics.get_overdue_customers retorna overdue_customers/
--    overdue_count — o placeholder nunca era preenchido e o LLM recebia o
--    template cru (com inadimplentes reais sairia lixo; com 0 saía um card
--    HITL "0 clientes" com o LLM reclamando do placeholder vazio).
-- 2. client_reactivation.gen_reactivation usava {{pipeline_summary}} (sempre
--    não-vazio, ex. "11 ativos · 0 inativos") — o gate de suficiência nunca
--    pulava com 0 inativos e o LLM respondia prosa sem saída estruturada
--    (partial). Agora usa {{client_list}} (a lista de inativos em si) e pede
--    JSON explícito; o corpo do push_card referencia só {{propostas}} para o
--    skip encadeado do executor suprimir o card quando não há inativos.
-- 3. financeiro_monitor.analyze_cashflow gerava "Saldo crítico" (error) com
--    saldo=0 por ausência de conta bancária conectada — regra explícita no
--    prompt: sem contas conectadas, zeros não são crise; no máximo 1 insight
--    info recomendando conectar o Open Finance.
--
-- Acompanha mudanças de código no executor (skip encadeado approval/artifact
-- via _gated_keys + restrição do insight_key ao nome da chave) — routines.py.
--
-- APLICADA em prod via psql em 2026-07-10 (prod tem drift; não usar db push).

UPDATE cross_agent_routines
SET steps = jsonb_set(
  steps, '{1,task_template}',
  to_jsonb(E'Gere mensagens de cobrança personalizadas para os clientes inadimplentes da {{nome_empresa}}.\n\nTom solicitado: {{tom}}\n\nClientes em atraso ({{overdue_count}}):\n{{overdue_customers}}\n\nPara cada cliente gere uma mensagem de cobrança com o tom indicado. Inclua valor em aberto, dias de atraso e uma chamada à ação clara.\n\nResponda em JSON com a chave "mensagens": lista com uma mensagem por cliente.'::text)
)
WHERE id = 'collection_overdue';

UPDATE cross_agent_routines
SET steps = jsonb_set(
  jsonb_set(
    steps, '{1,task_template}',
    to_jsonb(E'Elabore propostas de reativação para clientes inativos da {{nome_empresa}}.\n\nClientes inativos (min {{min_dias_inatividade}} dias sem compra):\n{{client_list}}\n\n{% if incluir_proposta %}Para cada cliente inclua uma proposta especial ou desconto personalizado.{% endif %}\n\nGere uma mensagem por cliente com tom amigável e proposta de retorno concreta.\n\nResponda em JSON com a chave "propostas": lista com uma proposta por cliente (lista vazia se não houver clientes inativos).'::text)
  ),
  '{2,inputs,body}',
  to_jsonb(E'Propostas de reativação para clientes inativos:\n\n{{propostas}}'::text)
)
WHERE id = 'client_reactivation';

UPDATE cross_agent_routines
SET steps = jsonb_set(
  steps, '{5,task_template}',
  to_jsonb((steps->5->>'task_template') || E'\n\nREGRA CRÍTICA: se a avaliação de caixa indicar que NÃO há contas bancárias conectadas (ex.: "Nenhuma conta conectada") ou o saldo vier zerado por ausência de integração bancária, isso NÃO é um problema financeiro real — NÃO gere insights de saldo crítico, liquidez ou runway com severity warning/error. Nesse caso emita no máximo 1 insight info recomendando conectar o Open Finance e baseie os demais insights apenas nos dados realmente presentes (transações do período, KPIs).')
)
WHERE id = 'financeiro_monitor';
