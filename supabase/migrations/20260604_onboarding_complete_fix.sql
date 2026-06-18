-- Fix onboarding_complete routine:
-- - step 3 (get_masterprompt): on_failure = continue
-- - step 4: replace insights_synthesis skill with knowledge.fill_masterprompt function
-- - step 5: keep as-is (storage.save_context_document)
-- - step 6: keep as-is (alert) — rendering logic handled in code

WITH updated AS (
  UPDATE cross_agent_routines
  SET steps = (
    SELECT jsonb_agg(
      CASE
        WHEN s.step_order = 3 THEN
          s.step || jsonb_build_object('on_failure', 'continue')
        WHEN s.step_order = 4 THEN
          s.step || jsonb_build_object(
            'type', 'function',
            'function', 'knowledge.fill_masterprompt',
            'on_failure', 'continue',
            'inputs', jsonb_build_object(
              'masterprompt', '{{masterprompt}}',
              'website_content', '{{website_content}}',
              'context_report_summary', '{{context_report_summary}}',
              'client_name', '{{nome_empresa}}'
            ),
            'outputs', jsonb_build_array('filled_masterprompt')
          )
        ELSE s.step
      END
    )
    FROM jsonb_array_elements(steps) WITH ORDINALITY AS s(step, step_order)
    WHERE id = 'onboarding_complete'
  )
  WHERE id = 'onboarding_complete'
  RETURNING id, steps
)
SELECT id FROM updated;
