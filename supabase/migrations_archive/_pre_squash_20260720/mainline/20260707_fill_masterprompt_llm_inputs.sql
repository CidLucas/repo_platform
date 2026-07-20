-- onboarding_complete / step 4 (fill_masterprompt):
-- - pass the full context report markdown (new context_report_markdown output
--   of analytics.generate_context_report) so the LLM synthesis has real data
-- - drop vestigial skill_slug/task_template left over from the old skill step
--   (ignored since type=function, but misleading)

UPDATE cross_agent_routines
SET steps = (
  SELECT jsonb_agg(
    CASE
      WHEN s.step->>'id' = 'fill_masterprompt' THEN
        (s.step - 'skill_slug' - 'task_template') || jsonb_build_object(
          'inputs',
          (s.step->'inputs') || jsonb_build_object(
            'context_report_markdown', '{{context_report_markdown}}'
          )
        )
      ELSE s.step
    END
    ORDER BY s.ord
  )
  FROM jsonb_array_elements(steps) WITH ORDINALITY AS s(step, ord)
)
WHERE id = 'onboarding_complete';
