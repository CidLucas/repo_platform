-- Fix 3: Reactivate post-onboarding routines and re-dispatch onboarding_complete
-- The onboarding-bootstrap seeded client_routines as inactive (status='inactive', active=false)
-- dispatch_routine_event requires active=true to enqueue the execution.

-- Step 1: Reactivate the cron routines that should be on by default
UPDATE public.client_routines
SET active = true, status = 'active'
WHERE client_id = 'aaa37322-d980-467b-8a67-d3ef2800812b'
  AND routine_id IN (
    'daily_insights',
    'morning_sync',
    'end_of_day_digest',
    'weekly_summary',
    'pending_decisions_review',
    'deadline_radar'
  )
  AND status = 'inactive';

-- Step 2: Re-dispatch onboarding_complete (now that the row is inactive, we activate it first)
UPDATE public.client_routines
SET active = true, status = 'active'
WHERE client_id = 'aaa37322-d980-467b-8a67-d3ef2800812b'
  AND routine_id = 'onboarding_complete';

-- Step 3: Manually insert the execution row for onboarding_complete
-- (dispatch_routine_event will now find the active subscription and insert)
SELECT public.dispatch_routine_event(
  'onboarding_complete',
  'aaa37322-d980-467b-8a67-d3ef2800812b'::uuid,
  '{"event_type": "onboarding_completed", "source": "manual_redispatch"}'::jsonb
);
