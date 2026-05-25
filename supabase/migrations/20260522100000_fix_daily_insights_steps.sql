-- =============================================================================
-- Fix: daily_insights routine steps — replace unreliable specialist-agent skill
-- step with a deterministic direct-LLM function call.
--
-- Root cause: the analyze_insights skill step invokes the `financeiro` specialist
-- agent graph. That agent has its own system prompt and tool-use loop; it rarely
-- returns a bare JSON array, so _extract_json_from_text fails and `insights`
-- never enters routine state. Consequently {{insights}} stays unresolved in the
-- save_insights artifact step → 0 insights written.
--
-- Fix: replace step 2 (skill) with `insights.generate_from_kpis` (function),
-- a new registration in routine_functions.py that calls the LLM directly with
-- a JSON-only system prompt and parses the response deterministically.
--
-- Steps after this migration:
--   1. analytics.get_kpi_snapshots  (function) — unchanged
--   2. insights.generate_from_kpis  (function) — replaces financeiro skill step
--   3. storage.save_insights         (artifact)  — unchanged
-- =============================================================================

UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id":       "fetch_kpis",
    "step":     1,
    "type":     "function",
    "function": "analytics.get_kpi_snapshots",
    "inputs":   {"window_days": 30, "baseline_days": 90},
    "on_failure": "halt"
  },
  {
    "id":       "generate_insights",
    "step":     2,
    "type":     "function",
    "function": "insights.generate_from_kpis",
    "inputs":   {"kpi_data": "{{kpi_data}}", "nome_empresa": "{{nome_empresa}}"},
    "on_failure": "continue"
  },
  {
    "id":            "save_insights",
    "step":          3,
    "type":          "artifact",
    "function":      "storage.save_insights",
    "inputs":        {"insights": "{{insights}}"},
    "on_failure":    "continue"
  }
]'::jsonb
WHERE id = 'daily_insights';
