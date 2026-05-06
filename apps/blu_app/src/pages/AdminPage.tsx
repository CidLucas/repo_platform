import { useQuery } from '@tanstack/react-query'
import { AdminLayout } from '@/components/admin/AdminLayout'
import { IntegrationsPanel } from '@/components/admin/IntegrationCard'
import { UserTable } from '@/components/admin/UserTable'
import { BillingCard } from '@/components/admin/BillingCard'
import { AuditLog } from '@/components/admin/AuditLog'
import { DataPrivacyPanel } from '@/components/admin/DataPrivacyPanel'
import { NotificationPreferences } from '@/components/admin/NotificationPreferences'
import { useAuth } from '@/hooks/useAuth'
import { fetchClientUsers } from '@/api/admin'

export function AdminPage() {
  const { clientId, user } = useAuth()

  const usersQ = useQuery({
    queryKey: ['admin-users', clientId ?? ''],
    queryFn: () => fetchClientUsers(clientId!),
    enabled: !!clientId,
    staleTime: 120_000,
  })

  // Derive tier from first user record (the account owner)
  const ownerRecord = usersQ.data?.[0]
  const tier = ownerRecord?.tier ?? 'free'

  return (
    <AdminLayout
      // ── Integrações — self-contained panel with catalog + modal ────
      integrations={<IntegrationsPanel />}
      // ── Usuários ───────────────────────────────────────────
      users={
        <UserTable
          users={usersQ.data ?? []}
          loading={usersQ.isLoading}
          currentUserId={user?.id}
        />
      }
      // ── Faturamento ────────────────────────────────────────
      billing={<BillingCard tier={tier} />}
      // ── Auditoria ──────────────────────────────────────────
      audit={
        clientId ? (
          <AuditLog clientId={clientId} />
        ) : (
          <p className="text-body-sm text-gray-400">Carregando...</p>
        )
      }
      // ── LGPD ───────────────────────────────────────────────
      lgpd={
        clientId ? (
          <DataPrivacyPanel clientId={clientId} />
        ) : (
          <p className="text-body-sm text-gray-400">Carregando...</p>
        )
      }
      // ── Notificações ───────────────────────────────────────
      notifications={
        clientId ? (
          <NotificationPreferences clientId={clientId} />
        ) : (
          <p className="text-body-sm text-gray-400">Carregando...</p>
        )
      }
    />
  )
}
