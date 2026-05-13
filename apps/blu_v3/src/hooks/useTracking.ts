import { useCallback } from 'react'
import { supabase } from '@blu/auth'

export function useTracking() {
  const track = useCallback((eventName: string, properties?: Record<string, unknown>) => {
    // Fire-and-forget: use two-arg .then() since PromiseLike has no .catch()
    void supabase
      .rpc('record_frontend_event', {
        p_event_name: eventName,
        p_properties: properties ?? {},
      })
      .then(() => {}, () => {})
  }, [])

  return { track }
}
