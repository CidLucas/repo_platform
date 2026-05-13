import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import {
  fetchIntegrations,
  disconnectIntegration,
  fetchAuditLog,
  requestDataExport,
  requestDataDeletion,
  fetchTeamMembers,
  ensureOwnerRow,
  inviteUser,
  updateUserPermissions,
} from '../api/admin'

export function useIntegrations() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['admin-integrations', clientId],
    queryFn: () => fetchIntegrations(clientId!),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useDisconnectIntegration() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (integrationId: string) => disconnectIntegration(integrationId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-integrations', clientId] }),
  })
}

export function useAuditLog(page = 1) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['admin-audit', clientId, page],
    queryFn: () => fetchAuditLog(clientId!, page),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useRequestDataExport() {
  const { clientId } = useAuth()
  return useMutation({
    mutationFn: () => requestDataExport(clientId!),
  })
}

export function useRequestDataDeletion() {
  const { clientId } = useAuth()
  return useMutation({
    mutationFn: () => requestDataDeletion(clientId!),
  })
}

export function useTeamMembers() {
  const { clientId, user } = useAuth()
  return useQuery({
    queryKey: ['admin-team', clientId],
    queryFn: async () => {
      const members = await fetchTeamMembers(clientId!)
      if (members.length === 0 && user?.email) {
        // Existing clients predate the client_users table — seed the owner row then refetch
        await ensureOwnerRow(clientId!, user.id, user.email, user.user_metadata?.full_name ?? null)
        return fetchTeamMembers(clientId!)
      }
      return members
    },
    enabled: !!clientId && !!user,
    staleTime: 5 * 60 * 1000,
  })
}

export function useInviteUser() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ email, name, role }: { email: string; name: string | null; role: string }) =>
      inviteUser(clientId!, email, name, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-team', clientId] }),
  })
}

export function useUpdateUserPermissions() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      userId,
      patch,
    }: {
      userId: string
      patch: { agent_permissions?: Record<string, boolean>; action_permissions?: Record<string, boolean> }
    }) => updateUserPermissions(userId, clientId!, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-team', clientId] }),
  })
}
