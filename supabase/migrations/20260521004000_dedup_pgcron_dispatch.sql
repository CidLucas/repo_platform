-- Remove duplicate pg_cron job (jobid=7, kept jobid=9 'dispatch_routine_executions')
SELECT cron.unschedule('dispatch_routine_executions_to_agent');
