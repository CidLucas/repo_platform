-- Migration: D1 success metrics canonical event aliases (Section 7)
-- Date: 2026-04-27
--
-- Adds canonical event names from docs/plans/2026-04-27-blu-cro-revamp.md
-- while preserving legacy dashboard.* names for backward compatibility.

BEGIN;

CREATE OR REPLACE VIEW public.d1_engagement_summary AS
SELECT
  event_name,
  COUNT(DISTINCT client_id) AS unique_tenants,
  COUNT(*) AS total_events,
  COUNT(*) FILTER (WHERE occurred_at >= now() - interval '7 days') AS events_last_7d,
  COUNT(*) FILTER (WHERE occurred_at >= now() - interval '24 hours') AS events_last_24h
FROM public.frontend_events
WHERE event_name IN (
  'mc.insight.click',
  'chat.rail.message_sent',
  'tenant.sample_data.disabled',
  'dashboard.insight.ctr',
  'dashboard.chat_rail.opened',
  'dashboard.demo_live.switch'
)
GROUP BY event_name
ORDER BY total_events DESC;

COMMENT ON VIEW public.d1_engagement_summary IS
  'Aggregated D1 engagement counts for Section 7 success metrics. Supports canonical (mc/chat/tenant.*) and legacy (dashboard.*) event names.';

COMMIT;
