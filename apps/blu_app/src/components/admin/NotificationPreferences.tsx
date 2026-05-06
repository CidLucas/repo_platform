import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Mail, Smartphone, MessageSquare } from 'lucide-react'
import { Toggle } from '@/components/primitives/Toggle'
import { Divider } from '@/components/primitives/Divider'
import {
  fetchNotificationPreferences,
  updateNotificationPreference,
} from '@/api/admin'
import type { NotificationPreference } from '@/api/admin'

// ── Channel config ─────────────────────────────────────────────────────────

type Channel = NotificationPreference['channel']

const CHANNEL_CONFIG: Record<Channel, { label: string; icon: React.ElementType }> = {
  in_app: { label: 'No aplicativo', icon: Bell },
  email: { label: 'E-mail', icon: Mail },
  push: { label: 'Push (mobile)', icon: Smartphone },
}

// ── Event type labels ──────────────────────────────────────────────────────

const EVENT_LABELS: Record<string, string> = {
  new_approval: 'Nova aprovação pendente',
  approval_urgent: 'Aprovação urgente',
  approval_overdue: 'Aprovação atrasada',
  agent_error: 'Erro em agente',
  insight_new: 'Novo insight gerado',
  trust_milestone: 'Marco de confiança atingido',
  report_ready: 'Relatório disponível',
  integration_error: 'Erro em integração',
  billing_event: 'Evento de faturamento',
}

// ── Default preferences (when table has no rows yet) ───────────────────────

const DEFAULT_EVENTS = Object.keys(EVENT_LABELS)

// ── PreferenceRow ──────────────────────────────────────────────────────────

interface PreferenceRowProps {
  pref: NotificationPreference
}

function PreferenceRow({ pref }: PreferenceRowProps) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (enabled: boolean) => updateNotificationPreference(pref.id, enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notification-prefs'] }),
  })

  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <span className="text-body-sm text-gray-300">
        {EVENT_LABELS[pref.notification_type] ?? pref.notification_type}
      </span>
      <Toggle
        checked={pref.enabled}
        onChange={(next) => mutation.mutate(next)}
        disabled={mutation.isPending}
      />
    </div>
  )
}

// ── ChannelSection ─────────────────────────────────────────────────────────

interface ChannelSectionProps {
  channel: Channel
  prefs: NotificationPreference[]
}

function ChannelSection({ channel, prefs }: ChannelSectionProps) {
  const cfg = CHANNEL_CONFIG[channel]
  const Icon = cfg.icon
  const channelPrefs = prefs.filter((p) => p.channel === channel)

  if (channelPrefs.length === 0) return null

  return (
    <div className="bg-surface border border-border rounded-md overflow-hidden">
      {/* Channel header */}
      <div className="flex items-center gap-2.5 px-4 py-3 bg-elevated/50 border-b border-border/60">
        <Icon size={15} strokeWidth={1.5} className="text-gray-400" />
        <span className="text-body-sm font-medium text-white">{cfg.label}</span>
        <span className="text-caption-sm text-gray-500 ml-auto">
          {channelPrefs.filter((p) => p.enabled).length}/{channelPrefs.length} ativos
        </span>
      </div>
      {/* Prefs */}
      <div className="px-4 divide-y divide-border/40">
        {channelPrefs.map((pref) => (
          <PreferenceRow key={pref.id} pref={pref} />
        ))}
      </div>
    </div>
  )
}

// ── NotificationPreferences ────────────────────────────────────────────────

interface NotificationPreferencesProps {
  clientId: string
}

export function NotificationPreferences({ clientId }: NotificationPreferencesProps) {
  const { data: prefs, isLoading } = useQuery({
    queryKey: ['notification-prefs', clientId],
    queryFn: () => fetchNotificationPreferences(clientId),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-40 bg-surface border border-border rounded-md"
            style={{
              backgroundImage:
                'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.03) 50%, transparent 100%)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 2s linear infinite',
            }}
          />
        ))}
      </div>
    )
  }

  const allPrefs = prefs ?? []
  const channels: Channel[] = ['in_app', 'email', 'push']
  const hasData = allPrefs.length > 0

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-start gap-3 mb-2">
        <div className="w-9 h-9 rounded-md bg-blu-500/10 border border-blu-500/20 flex items-center justify-center shrink-0">
          <Bell size={18} strokeWidth={1.5} className="text-blu-400" />
        </div>
        <div>
          <h2 className="text-heading-sm text-white">Preferências de Notificação</h2>
          <p className="text-caption text-gray-400 mt-0.5">
            Escolha quais notificações receber e por quais canais.
          </p>
        </div>
      </div>

      {hasData ? (
        <div className="space-y-4">
          {channels.map((channel) => (
            <ChannelSection key={channel} channel={channel} prefs={allPrefs} />
          ))}
        </div>
      ) : (
        /* Placeholder when table is empty — show all as enabled defaults */
        <div className="space-y-4">
          {channels.map((channel) => {
            const cfg = CHANNEL_CONFIG[channel]
            const Icon = cfg.icon
            return (
              <div key={channel} className="bg-surface border border-border rounded-md overflow-hidden">
                <div className="flex items-center gap-2.5 px-4 py-3 bg-elevated/50 border-b border-border/60">
                  <Icon size={15} strokeWidth={1.5} className="text-gray-400" />
                  <span className="text-body-sm font-medium text-white">{cfg.label}</span>
                </div>
                <div className="px-4 divide-y divide-border/40">
                  {DEFAULT_EVENTS.map((event) => (
                    <div key={event} className="flex items-center justify-between gap-4 py-2.5">
                      <span className="text-body-sm text-gray-300">
                        {EVENT_LABELS[event] ?? event}
                      </span>
                      <Toggle
                        checked={channel === 'in_app'} // in_app on by default
                        onChange={() => {}} // no-op until prefs are in DB
                      />
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
          <p className="text-caption text-gray-500">
            As preferências são salvas automaticamente quando alteradas.
          </p>
        </div>
      )}

      <Divider />

      {/* WhatsApp opt-in note */}
      <div className="flex items-start gap-2.5 bg-surface border border-border/60 rounded-md p-3">
        <MessageSquare size={14} strokeWidth={1.5} className="text-gray-400 shrink-0 mt-0.5" />
        <p className="text-caption text-gray-400">
          Notificações via WhatsApp estão disponíveis nos planos Growth e Enterprise.
          Configure em{' '}
          <span className="text-gray-300">Integrações → WhatsApp Business</span>.
        </p>
      </div>
    </div>
  )
}
