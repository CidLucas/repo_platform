import { useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { captureTelemetryEvent } from '../lib/telemetry';

/** D1 engagement event names tracked in the activation funnel dashboard. */
export type TrackingEvent =
  | 'mc.insight.click'
  | 'chat.rail.message_sent'
  | 'tenant.sample_data.disabled'
  | 'dashboard.insight.ctr'
  | 'dashboard.chat_rail.opened'
  | 'dashboard.demo_live.switch';

/**
 * Lightweight fire-and-forget tracking hook.
 * Calls `record_frontend_event` RPC on Supabase; errors are swallowed so a
 * failed track never breaks product functionality.
 */
export function useTracking() {
  const track = useCallback(
    (event: TrackingEvent, properties: Record<string, unknown> = {}) => {
      captureTelemetryEvent(event, properties);
      supabase
        .rpc('record_frontend_event', {
          p_event_name: event,
          p_properties: properties,
        })
        .then(({ error }) => {
          if (error) {
            // Non-blocking: log in dev, silently ignore in production.
            if (import.meta.env.DEV) {
              console.warn('[useTracking] record_frontend_event failed:', error.message);
            }
          }
        });
    },
    []
  );

  return { track };
}
