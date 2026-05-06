import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'
import { QUERY_KEYS } from '@/utils/constants'

/**
 * Mounts one Supabase Realtime channel in AppShell.
 * Invalidates TanStack Query caches when relevant tables change.
 */
export function useRealtime() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const channelRef = useRef<ReturnType<typeof supabase.channel> | null>(null)

  useEffect(() => {
    if (!clientId) return

    const channel = supabase
      .channel('app-realtime')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'approval_requests',
          filter: `client_id=eq.${clientId}`,
        },
        () => {
          qc.invalidateQueries({ queryKey: QUERY_KEYS.approvals(clientId) })
          qc.invalidateQueries({ queryKey: QUERY_KEYS.agents(clientId) })
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'approval_requests',
          filter: `client_id=eq.${clientId}`,
        },
        () => {
          qc.invalidateQueries({ queryKey: QUERY_KEYS.approvals(clientId) })
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'notifications',
          filter: `client_id=eq.${clientId}`,
        },
        () => {
          qc.invalidateQueries({ queryKey: QUERY_KEYS.notifications(clientId) })
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'client_enabled_agents',
          filter: `client_id=eq.${clientId}`,
        },
        () => {
          qc.invalidateQueries({ queryKey: QUERY_KEYS.agents(clientId) })
        }
      )
      .subscribe()

    channelRef.current = channel

    return () => {
      supabase.removeChannel(channel)
    }
  }, [clientId, qc])
}
