import { useState, useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import {
  Gear, Link, UsersThree, ClipboardText, Bell, CreditCard, Lock, MapTrifold,
  CheckCircle, FileArrowDown, ChartBar, Table, Broom, Trash, Warning, Bank,
  CalendarDots, HardDrive, Database, Receipt, Target, ShoppingCart, PencilSimpleLine,
  SquaresFour, ChatCircleDots,
  Globe, Buildings,
  BookOpen, CheckFat, ListBullets, GitFork,
} from '@phosphor-icons/react'
import { useAppStore } from '../../store/appStore'
import { useIntegrations, useDisconnectIntegration, useAuditLog, useRequestDataExport, useRequestDataDeletion, useTeamMembers, useUpdateUserPermissions, useInviteUser } from '../../hooks/useAdmin'
import { useQuery } from '@tanstack/react-query'
import { fetchInsights } from '../../api/insights'
import { useAuth } from '../../hooks/useAuth'
import { useStartSync } from '../../hooks/useConnectorStatus'
import { useNotificationPreferences, useSaveNotificationPreferences } from '../../hooks/useNotifications'
import { connectGoogleCalendar, connectGoogleDrive, captureCalendarToken, captureDriveToken } from '../../api/agenda'
import { createCredential } from '../../api/connectors'
import { supabase } from '@blu/auth'
import type { Integration, AuditEntry } from '../../api/admin'
import Toggle from '../../components/shared/Toggle'
import Modal from '../../components/shared/Modal'
import { IconCheck, IconSearch } from '../../components/shared/Icons'

// Polp institution IDs (from GET /api/v1/institutions — Polp sequential IDs, not bank codes)
const POLP_INSTITUTIONS = [
  { id: 56,  name: 'Itaú' },
  { id: 60,  name: 'Itaú Empresas' },
  { id: 24,  name: 'Bradesco' },
  { id: 25,  name: 'Bradesco Empresas' },
  { id: 95,  name: 'Santander' },
  { id: 100, name: 'Santander Empresas' },
  { id: 11,  name: 'Banco do Brasil' },
  { id: 12,  name: 'Banco do Brasil Empresas' },
  { id: 36,  name: 'Caixa Econômica Federal' },
  { id: 37,  name: 'Caixa Econômica Federal Empresas' },
  { id: 71,  name: 'Nubank' },
  { id: 72,  name: 'Nubank Empresas' },
  { id: 52,  name: 'Inter' },
  { id: 53,  name: 'Inter Empresas' },
  { id: 73,  name: 'PagBank' },
  { id: 74,  name: 'PagBank Empresas' },
  { id: 26,  name: 'BTG Pactual' },
  { id: 27,  name: 'BTG Pactual Empresas' },
  { id: 113, name: 'XP Banking' },
  { id: 114, name: 'XP Banking Empresas' },
  { id: 34,  name: 'C6 Bank' },
  { id: 35,  name: 'C6 Bank Empresas' },
  { id: 101, name: 'Sicoob' },
  { id: 103, name: 'Sicredi' },
  { id: 105, name: 'Stone Pagamentos' },
  { id: 0,   name: 'Outro (inserir ID manualmente)' },
]

type AdminTab = 'integracoes' | 'usuarios' | 'auditoria' | 'notificacoes' | 'faturamento' | 'lgpd' | 'contexto'

// ── Static catalogs ──────────────────────────────────────────────────────────

interface CatalogIntegration {
  id: string
  name: string
  desc: string
  provider: string
}

const LANES: { label: string; integrations: CatalogIntegration[] }[] = [
  {
    label: 'ERPs & Gestão',
    integrations: [
      { id: 'ic-conta-azul', name: 'Conta Azul', desc: 'NF-e e financeiro', provider: 'conta_azul' },
    ],
  },
  {
    label: 'Google',
    integrations: [
      { id: 'ic-gcal',  name: 'Google Calendar', desc: 'Agenda',        provider: 'google_calendar' },
      { id: 'ic-gdrive', name: 'Google Drive',    desc: 'Planilhas',     provider: 'google_drive' },
    ],
  },
  {
    label: 'Open Finance',
    integrations: [
      { id: 'ic-polp', name: 'Open Finance', desc: 'Contas bancárias reais', provider: 'polp' },
    ],
  },
  {
    label: 'Dados & Analytics',
    integrations: [
      { id: 'ic-bigquery', name: 'BigQuery',   desc: 'Data warehouse',  provider: 'bigquery' },
    ],
  },
  {
    label: 'Gestão de Projetos',
    integrations: [
      { id: 'monday',  name: 'Monday.com', desc: 'Boards, tarefas e updates',   provider: 'monday' },
      { id: 'notion',  name: 'Notion',      desc: 'Páginas e databases',          provider: 'notion' },
      { id: 'ic-asana',   name: 'Asana',       desc: 'Projetos e tarefas',           provider: 'asana' },
      { id: 'ic-clickup', name: 'ClickUp',     desc: 'Listas e tarefas',             provider: 'clickup' },
      { id: 'ic-linear',  name: 'Linear',      desc: 'Issues e projetos',            provider: 'linear' },
    ],
  },
  {
    label: 'Comunicação',
    integrations: [
      { id: 'ic-slack', name: 'Slack', desc: 'Canais, mensagens e alertas', provider: 'slack' },
    ],
  },
]

// Providers that use OAuth redirect instead of API key forms
const OAUTH_PROVIDERS = new Set(['google_calendar', 'google_drive'])

function getProviderIcon(provider: string, size = 20): ReactNode {
  switch (provider) {
    case 'conta_azul':      return <Receipt size={size} />
    case 'google_calendar': return <CalendarDots size={size} />
    case 'google_drive':    return <HardDrive size={size} />
    case 'polp':            return <Bank size={size} />
    case 'bigquery':
    case 'postgresql':      return <Database size={size} />
    case 'monday':          return <SquaresFour size={size} />
    case 'slack':           return <ChatCircleDots size={size} />
    case 'notion':          return <BookOpen size={size} />
    case 'asana':           return <CheckFat size={size} />
    case 'clickup':         return <ListBullets size={size} />
    case 'linear':          return <GitFork size={size} />
    default:                return <Link size={size} />
  }
}

function getDomainIcon(name: string): ReactNode {
  switch (name) {
    case 'Identidade': return <Buildings size={13} />
    case 'Operações':  return <Gear size={13} />
    case 'Pessoas':    return <UsersThree size={13} />
    case 'Externo':    return <Globe size={13} />
    case 'Estratégia': return <Target size={13} />
    default:           return null
  }
}

function getDbIntegration(provider: string, dbList: Integration[]): Integration | undefined {
  return dbList.find(i => i.provider === provider)
}

function isConnected(provider: string, dbList: Integration[]): boolean {
  return getDbIntegration(provider, dbList)?.status === 'connected'
}

function agentReadiness(dbList: Integration[]): { icon: ReactNode; name: string; status: string; st: string }[] {
  const AGENT_PROVIDERS: Record<string, string[]> = {
    financeiro: ['conta_azul'],
    estrategia: ['bigquery', 'postgresql'],
    clientes:   ['conta_azul'],
    compras:    ['conta_azul'],
    documentos: ['google_calendar'],
    agenda:     ['google_calendar'],
  }
  const ICONS: Record<string, ReactNode> = {
    financeiro: <ChartBar size={13} />,
    estrategia: <Target size={13} />,
    clientes:   <UsersThree size={13} />,
    compras:    <ShoppingCart size={13} />,
    documentos: <PencilSimpleLine size={13} />,
    agenda:     <CalendarDots size={13} />,
  }
  const NAMES: Record<string, string> = { financeiro: 'Financeiro', estrategia: 'Estratégia', clientes: 'Clientes', compras: 'Compras', documentos: 'Documentos', agenda: 'Agenda' }

  return Object.keys(AGENT_PROVIDERS).map(slug => {
    const required = AGENT_PROVIDERS[slug]
    const connectedCount = dbList.filter(i => required.includes(i.provider) && i.status === 'connected').length
    const status = connectedCount === 0 ? 'Inativo' : connectedCount >= Math.ceil(required.length / 2) ? 'Pronto' : 'Parcial'
    const st = status === 'Pronto' ? 'sts-ok' : status === 'Parcial' ? 'sts-par' : 'sts-err'
    return { icon: ICONS[slug], name: NAMES[slug], status, st }
  })
}

function formatTs(iso: string) {
  const d = new Date(iso)
  return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function agentColor(slug: string | null): string {
  const MAP: Record<string, string> = { compras: 'var(--blue3)', financeiro: 'var(--teal)', agenda: 'var(--orange)', documentos: 'var(--pink)', estrategia: 'var(--yellow)', clientes: 'var(--teal)' }
  return (slug && MAP[slug]) ? MAP[slug] : 'var(--mu)'
}







export default function AdminScreen() {
  const go = useAppStore(s => s.go)
  const initialTab = useAppStore(s => s.initialTab)

  // Read tab from hash on mount (e.g. #room/admin?tab=integracoes), fallback to initialTab or default
  const tabFromHash = (): AdminTab => {
    const m = window.location.hash.match(/[?&]tab=([^&]+)/)
    if (m) return m[1] as AdminTab
    return (initialTab as AdminTab) || 'integracoes'
  }

  const [tab, setTabState] = useState<AdminTab>(tabFromHash)

  const setTab = (t: AdminTab) => {
    const newHash = `#room/admin?tab=${t}`
    if (window.location.hash !== newHash) {
      window.history.pushState({ screen: 'admin', label: 'Admin', tab: t }, '', newHash)
    }
    setTabState(t)
  }

  // Sync tab when browser back/forward fires (popstate updates hash, re-read it)
  useEffect(() => {
    const onPop = () => setTabState(tabFromHash())
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [expandedLog, setExpandedLog] = useState<string | null>(null)
  const [expandedUser, setExpandedUser] = useState<string | null>(null)
  const [modalIntgId, setModalIntgId] = useState<string | null>(null) // catalog id
  const [modalMode, setModalMode] = useState<'connect' | 'config'>('connect')
  const [logSearch, setLogSearch] = useState('')
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteForm, setInviteForm] = useState({ name: '', email: '', role: 'member' })


  const { data: dbIntegrations = [], refetch: refetchIntegrations } = useIntegrations()
  const disconnect = useDisconnectIntegration()
  const syncMut = useStartSync()
  const { data: auditData } = useAuditLog()
  const exportData = useRequestDataExport()
  const deleteData = useRequestDataDeletion()
  const { data: teamMembers = [], isLoading: teamLoading } = useTeamMembers()
  const updatePermissions = useUpdateUserPermissions()
  const inviteUser = useInviteUser()

  // Integration connect form state
  const [connFormData, setConnFormData] = useState<Record<string, string>>({})
  const [connSaving, setConnSaving] = useState(false)
  const [connError, setConnError] = useState<string | null>(null)

  // ── Google OAuth return handler ─────────────────────────────────────────────
  // After signInWithOAuth redirects back, getSession() has provider_refresh_token.
  // onAuthStateChange alone is unreliable for re-auth (user already logged in).
  useEffect(() => {
    const isOAuthCallback =
      window.location.hash.includes('access_token') ||
      window.location.search.includes('code=')
    if (!isOAuthCallback) return

    const calPending  = localStorage.getItem('admin_cal_oauth_pending') === '1'
    const drivePending = localStorage.getItem('admin_drive_oauth_pending') === '1'
    if (!calPending && !drivePending) return

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session?.provider_refresh_token) return

      if (calPending) {
        localStorage.removeItem('admin_cal_oauth_pending')
        void captureCalendarToken({
          refreshToken: session.provider_refresh_token,
          accessToken: session.provider_token ?? '',
          email: session.user?.email ?? '',
        }).then(() => refetchIntegrations())
      } else if (drivePending) {
        localStorage.removeItem('admin_drive_oauth_pending')
        void captureDriveToken({
          refreshToken: session.provider_refresh_token,
          accessToken: session.provider_token ?? '',
          email: session.user?.email ?? '',
        }).then(() => refetchIntegrations())
      }
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Polp Open Finance auth URL modal (Pluggy widget)
  const [polpAuthUrl, setPolpAuthUrl] = useState<string | null>(null)
  // Polling for url_to_authenticate after UPDATING status (webhook delivers it async)
  const [polpPendingIntgId, setPolpPendingIntgId] = useState<number | null>(null)
  const polpClientIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (!polpPendingIntgId || !polpClientIdRef.current) return
    const clientId = polpClientIdRef.current
    const interval = setInterval(async () => {
      const { data } = await supabase
        .from('polp_integrations')
        .select('url_to_authenticate, status')
        .eq('polp_integration_id', polpPendingIntgId)
        .eq('client_id', clientId)
        .maybeSingle()
      if (data?.url_to_authenticate) {
        setPolpAuthUrl(data.url_to_authenticate)
        setPolpPendingIntgId(null)
      } else if (data?.status === 'UPDATED' || data?.status === 'DELETED') {
        setPolpPendingIntgId(null)
        void refetchIntegrations()
      }
    }, 3000)
    const timeout = setTimeout(() => setPolpPendingIntgId(null), 5 * 60 * 1000)
    return () => { clearInterval(interval); clearTimeout(timeout) }
  }, [polpPendingIntgId])

  // Notifications tab
  const { data: notifPrefs, isLoading: notifLoading } = useNotificationPreferences()
  const saveNotifPrefs = useSaveNotificationPreferences()
  const [savingKind, setSavingKind] = useState<string | null>(null)

  const auditEntries: AuditEntry[] = auditData?.entries ?? []
  const { clientId } = useAuth()
  const { data: insightsData } = useQuery({
    queryKey: ['admin-insights-anomalias', clientId ?? ''],
    queryFn: () => fetchInsights(),
    enabled: !!clientId,
    staleTime: 120_000,
  })
  const anomaliasCount = (insightsData ?? []).filter((i: { severity: string }) => i.severity === 'error').length
  const auditTotal: number = auditData?.total ?? 0

  // Derived audit KPIs
  const approvedCount = auditEntries.filter(e => e.action?.toLowerCase().includes('aprovad')).length
  const approvalRate = auditTotal > 0 ? Math.round((approvedCount / auditEntries.length) * 100) : 0

  const filteredLogs = auditEntries.filter(e =>
    logSearch === '' ||
    e.action?.toLowerCase().includes(logSearch.toLowerCase()) ||
    e.actor?.toLowerCase().includes(logSearch.toLowerCase())
  )

  const modalCatalogIntg = modalIntgId ? LANES.flatMap(l => l.integrations).find(i => i.id === modalIntgId) : null
  const modalDbIntg = modalCatalogIntg ? getDbIntegration(modalCatalogIntg.provider, dbIntegrations) : null

  const openConnect = (id: string) => { setModalIntgId(id); setModalMode('connect'); setConnFormData({}); setConnError(null) }
  const openConfig  = (id: string) => { setModalIntgId(id); setModalMode('config') }

  const doConnect = async () => {
    if (!modalCatalogIntg) return
    setConnSaving(true)
    setConnError(null)

    try {
      const { data: clientId } = await supabase.rpc('get_my_client_id')
      if (!clientId) throw new Error('Cliente não encontrado.')

      if (modalCatalogIntg.provider === 'conta_azul') {
        await createCredential(clientId, 'conta_azul', 'Conta Azul', {
          username: connFormData.username ?? '',
          password: connFormData.password ?? '',
        })
      } else if (modalCatalogIntg.provider === 'bigquery') {
        if (!connFormData.service_account_json) throw new Error('Cole o JSON da Service Account.')
        let sa: Record<string, unknown> = {}
        try { sa = JSON.parse(connFormData.service_account_json) } catch { throw new Error('JSON inválido.') }
        await createCredential(clientId, 'bigquery', 'BigQuery', {
          project_id: (sa.project_id as string) ?? '',
          dataset_id: connFormData.dataset_id ?? '',
          table_name: connFormData.table_name ?? '',
          location: connFormData.location ?? 'southamerica-east1',
          service_account_json: sa,
        })
      } else if (modalCatalogIntg.provider === 'polp') {
        const institutionId = parseInt(connFormData.institution_id ?? '0', 10)
        if (!institutionId) throw new Error('Selecione uma instituição.')
        const { data, error } = await supabase.functions.invoke('polp-connect', {
          body: {
            client_id: clientId,
            institution_id: institutionId,
            cpf: connFormData.cpf || undefined,
            cnpj: connFormData.cnpj || undefined,
          },
        })
        if (error) throw new Error(error.message)
        setModalIntgId(null)
        if (data?.url_to_authenticate) {
          // URL is ready immediately — user must click to open (can't auto-open after async)
          setPolpAuthUrl(data.url_to_authenticate)
        } else if (data?.polp_integration_id) {
          // Status is UPDATING — url_to_authenticate arrives via webhook. Poll for it.
          polpClientIdRef.current = clientId
          setPolpPendingIntgId(data.polp_integration_id)
        }
        await refetchIntegrations()
        return
      } else if (modalCatalogIntg.provider === 'slack' || modalCatalogIntg.provider === 'monday' ||
                 modalCatalogIntg.provider === 'notion' || modalCatalogIntg.provider === 'asana' ||
                 modalCatalogIntg.provider === 'clickup' || modalCatalogIntg.provider === 'linear') {
        const apiToken = connFormData.api_token?.trim()
        if (!apiToken) throw new Error('Informe o token de API.')
        const { data: session } = await supabase.auth.getSession()
        const accessToken = session?.session?.access_token
        if (!accessToken) throw new Error('Sessão expirada, faça login novamente.')
        const resp = await fetch(
          `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/save-api-token`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({
              provider: modalCatalogIntg.provider,
              api_token: apiToken,
              account_label: modalCatalogIntg.provider === 'slack' ? 'workspace' : 'account',
            }),
          }
        )
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}))
          throw new Error((err as any).error ?? 'Erro ao salvar token.')
        }
      }

      await refetchIntegrations()
      setModalIntgId(null)
    } catch (e: any) {
      setConnError(e.message)
    } finally {
      setConnSaving(false)
    }
  }

  const doDisconnect = async () => {
    if (modalDbIntg) {
      await disconnect.mutateAsync(modalDbIntg.id)
      await refetchIntegrations()
    }
    setModalIntgId(null)
  }

  const TABS: { id: AdminTab; icon: ReactNode; label: string }[] = [
    { id: 'integracoes',  icon: <Link size={13} />,          label: 'Integrações' },
    { id: 'usuarios',     icon: <UsersThree size={13} />,    label: 'Usuários' },
    { id: 'auditoria',   icon: <ClipboardText size={13} />, label: 'Auditoria' },
    { id: 'notificacoes', icon: <Bell size={13} />,          label: 'Notificações' },
    { id: 'faturamento',  icon: <CreditCard size={13} />,    label: 'Faturamento' },
    { id: 'lgpd',         icon: <Lock size={13} />,          label: 'LGPD' },
    { id: 'contexto',     icon: <MapTrifold size={13} />,    label: 'Contexto' },
  ]

  const agentReadinessData = agentReadiness(dbIntegrations)

  function statusPct(agentName: string): number {
    const a = agentReadinessData.find(r => r.name.toLowerCase() === agentName)
    return a?.status === 'Pronto' ? 90 : a?.status === 'Parcial' ? 55 : 15
  }
  const totalIntg = LANES.flatMap(l => l.integrations).length
  const connPct = totalIntg > 0
    ? Math.round((dbIntegrations.filter(i => i.status === 'connected').length / totalIntg) * 100)
    : 0

  function domainColor(pct: number): string {
    return pct >= 70 ? 'var(--ok)' : pct >= 40 ? 'var(--att)' : 'var(--urg)'
  }

  const domainData = [
    { icon: '🏢', name: 'Identidade', pct: Math.round((statusPct('financeiro') + statusPct('clientes')) / 2) },
    { icon: '⚙️', name: 'Operações',  pct: Math.round((statusPct('compras') + statusPct('financeiro') + statusPct('documentos')) / 3) },
    { icon: '👥', name: 'Pessoas',    pct: statusPct('clientes') },
    { icon: '🌐', name: 'Externo',    pct: connPct },
    { icon: '🎯', name: 'Estratégia', pct: statusPct('estratégia') },
  ].map(d => ({ ...d, color: domainColor(d.pct) }))

  const ctxScore = Math.round(domainData.reduce((s, d) => s + d.pct, 0) / domainData.length)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="rh">
        <div className="rav"><Gear size={16} /></div>
        <div><div className="rn">Admin</div><div className="rd">Configurações, integrações e controles</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
        </div>
      </div>

      <div className="ad-tabs">
        {TABS.map(t => (
          <div key={t.id} className={`ad-tab${tab === t.id ? ' on' : ''}`} onClick={() => setTab(t.id)}>{t.icon}{t.label}</div>
        ))}
      </div>

      {/* INTEGRAÇÕES */}
      <div className={`ad-tc${tab === 'integracoes' ? ' on' : ''}`}>
        {LANES.map(lane => (
          <div key={lane.label} className="int-lane">
            <div className="int-lane-hd">
              <span className="int-lane-lbl">{lane.label}</span>
              <span className="int-lane-ct">{lane.integrations.filter(i => isConnected(i.provider, dbIntegrations)).length} de {lane.integrations.length} conectadas</span>
            </div>
            <div className="int-carousel">
              {lane.integrations.map(intg => {
                const conn = isConnected(intg.provider, dbIntegrations)
                const dbIntg = getDbIntegration(intg.provider, dbIntegrations)
                const isSyncing = syncMut.isPending && syncMut.variables === dbIntg?.id
                return (
                  <div key={intg.id} className={`int-card${conn ? ' conn' : ''}`}>
                    <div className="int-card-ico">
                      {getProviderIcon(intg.provider, 20)}
                      <div className="ic-dot">✓</div>
                    </div>
                    <div className="int-card-nm">{intg.name}</div>
                    <div className="int-card-dc">
                      {dbIntg?.last_synced_at
                        ? `Sync: ${new Date(dbIntg.last_synced_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}`
                        : dbIntg?.connection_detail ?? intg.desc}
                    </div>
                    <div className="int-card-ft">
                      <span className={`int-status-tag ${conn ? 'int-status-conn' : 'int-status-disc'}`}>
                        {isSyncing ? '↻ Sincronizando…' : conn ? '● Conectado' : '○ Desconectado'}
                      </span>
                      {conn ? (
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button
                            className="btn bs"
                            style={{ fontSize: 10, padding: '3px 8px' }}
                            disabled={isSyncing}
                            onClick={() => dbIntg && syncMut.mutate(dbIntg.id)}
                          >
                            {isSyncing ? '…' : '↻'}
                          </button>
                          <button className="btn bg" style={{ fontSize: 10, padding: '3px 10px' }} onClick={() => openConfig(intg.id)}>Config</button>
                        </div>
                      ) : (
                        <button className="btn bp" style={{ fontSize: 10.5, padding: '4px 12px' }} onClick={() => openConnect(intg.id)}>Conectar</button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* USUÁRIOS */}
      <div className={`ad-tc${tab === 'usuarios' ? ' on' : ''}`}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
          <button
            className="int-btn"
            style={{ background: 'var(--ac)', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
            onClick={() => { setInviteForm({ name: '', email: '', role: 'member' }); setShowInviteModal(true) }}
          >
            + Adicionar usuário
          </button>
        </div>
        {teamLoading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>
        ) : teamMembers.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--mu)', fontSize: 12 }}>Nenhum usuário encontrado</div>
        ) : teamMembers.map(u => {
          const initials = (u.name ?? u.email ?? '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
          return (
            <div key={u.id}>
              <div className={`usr-row${expandedUser === u.id ? ' open' : ''}`} onClick={() => setExpandedUser(expandedUser === u.id ? null : u.id)}>
                <div className="usr-av" style={{ background: 'var(--ac)22', color: 'var(--ac)' }}>{initials}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600 }}>{u.name ?? u.email ?? '—'}</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)' }}>{u.role.charAt(0).toUpperCase() + u.role.slice(1)}{!u.accepted_at ? ' · Convite pendente' : ''}</div>
                </div>
                <span className="usr-perm">{expandedUser === u.id ? '▼' : '▶'}</span>
              </div>
              <div className={`perm-box${expandedUser === u.id ? ' open' : ''}`} onClick={e => e.stopPropagation()}>
                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 7 }}>Acesso por agente</div>
                  {['compras', 'financeiro', 'agenda', 'documentos', 'estrategia', 'clientes'].map(agent => {
                    const enabled = u.agent_permissions[agent] !== false
                    return (
                      <div key={agent} className="perm-row">
                        <span className="perm-nm" style={{ textTransform: 'capitalize' }}>{agent}</span>
                        <Toggle
                          checked={enabled}
                          onChange={() => updatePermissions.mutate({
                            userId: u.id,
                            patch: { agent_permissions: { ...u.agent_permissions, [agent]: !enabled } },
                          })}
                        />
                      </div>
                    )
                  })}
                </div>
                <div>
                  <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 7, marginTop: 8 }}>Permissões de ação</div>
                  {[['aprovar', 'Aprovar decisões'], ['exportar', 'Exportar dados'], ['usuarios', 'Gerenciar usuários'], ['config', 'Configurar agentes']].map(([key, label]) => {
                    const enabled = u.action_permissions[key] === true
                    return (
                      <div key={key} className="perm-row">
                        <span className="perm-nm">{label}</span>
                        <Toggle
                          checked={enabled}
                          onChange={() => updatePermissions.mutate({
                            userId: u.id,
                            patch: { action_permissions: { ...u.action_permissions, [key]: !enabled } },
                          })}
                        />
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )
        })}

        {/* Invite modal */}
        <Modal open={showInviteModal} onClose={() => setShowInviteModal(false)} title="Adicionar usuário" width="320px">
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 4 }}>Nome</div>
            <input
              style={{ width: '100%', boxSizing: 'border-box', padding: '7px 10px', borderRadius: 8, border: '1px solid var(--gb)', background: 'var(--sb)', color: 'var(--tx)', fontSize: 12 }}
              placeholder="Nome completo"
              value={inviteForm.name}
              onChange={e => setInviteForm(f => ({ ...f, name: e.target.value }))}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 4 }}>E-mail</div>
            <input
              style={{ width: '100%', boxSizing: 'border-box', padding: '7px 10px', borderRadius: 8, border: '1px solid var(--gb)', background: 'var(--sb)', color: 'var(--tx)', fontSize: 12 }}
              placeholder="email@empresa.com"
              type="email"
              value={inviteForm.email}
              onChange={e => setInviteForm(f => ({ ...f, email: e.target.value }))}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 4 }}>Papel</div>
            <select
              style={{ width: '100%', padding: '7px 10px', borderRadius: 8, border: '1px solid var(--gb)', background: 'var(--sb)', color: 'var(--tx)', fontSize: 12 }}
              value={inviteForm.role}
              onChange={e => setInviteForm(f => ({ ...f, role: e.target.value }))}
            >
              <option value="admin">Admin</option>
              <option value="manager">Gerente</option>
              <option value="member">Membro</option>
            </select>
          </div>

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button className="btn bs" onClick={() => setShowInviteModal(false)}>Cancelar</button>
            <button
              className="btn bp"
              style={{ opacity: inviteUser.isPending ? 0.6 : 1 }}
              disabled={!inviteForm.email || inviteUser.isPending}
              onClick={async () => {
                await inviteUser.mutateAsync({ email: inviteForm.email, name: inviteForm.name || null, role: inviteForm.role })
                setShowInviteModal(false)
              }}
            >
              {inviteUser.isPending ? 'Adicionando…' : 'Adicionar'}
            </button>
          </div>
        </Modal>
      </div>

      {/* AUDITORIA */}
      <div className={`ad-tc${tab === 'auditoria' ? ' on' : ''}`}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8, marginBottom: 14 }}>
          <div className="kpi-cell"><div className="kpi-lbl">Total de ações</div><div className="kpi-val">{auditTotal.toLocaleString('pt-BR')}</div><div className="kpi-d" style={{ color: 'var(--mu)' }}>histórico</div></div>
          <div className="kpi-cell"><div className="kpi-lbl">Taxa de aprovação</div><div className="kpi-val">{auditTotal > 0 ? `${approvalRate}%` : '—'}</div><div className="kpi-d" style={{ color: 'var(--mu)' }}>nesta página</div></div>
          <div className="kpi-cell"><div className="kpi-lbl">Economia gerada</div><div className="kpi-val">—</div><div className="kpi-d" style={{ color: 'var(--mu)' }}>em breve</div></div>
          <div className="kpi-cell"><div className="kpi-lbl">Anomalias</div><div className="kpi-val" style={{ color: anomaliasCount > 0 ? 'var(--urg)' : 'var(--ok)' }}>{anomaliasCount}</div><div className="kpi-d" style={{ color: 'var(--mu)' }}>insights com erro</div></div>
        </div>
        <div className="aud-search">
          <IconSearch size={13} />
          <input placeholder="Buscar nos logs…" value={logSearch} onChange={e => setLogSearch(e.target.value)} />
        </div>
        {auditEntries.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--mu)', fontSize: 12 }}>Nenhum log de auditoria disponível</div>
        ) : (
          <div>
            {filteredLogs.map((entry, i) => {
              const isOpen = expandedLog === entry.id
              const meta = (entry.metadata ?? {}) as Record<string, unknown>
              const value = (meta.value as string | null) ?? (meta.amount as string | null) ?? null
              const justification = (meta.justification as string | null) ?? (meta.reason as string | null) ?? null
              return (
                <div key={i} className="log-wrap">
                  <div className={`log-row${isOpen ? ' expanded' : ''}`} onClick={() => setExpandedLog(isOpen ? null : entry.id)} style={{ border: 'none', borderBottom: isOpen ? '1px solid var(--gb)' : 'none' }}>
                    <span className="log-ts">{formatTs(entry.created_at)}</span>
                    <div className="log-ag" style={{ background: agentColor(entry.agent_slug) }} />
                    <div className="log-act">{entry.action}</div>
                    <span className="log-usr">{entry.actor ?? 'Sistema'}</span>
                    <span className="log-st lok">Registrado</span>
                    <span style={{ color: 'var(--mu)', fontSize: 10, marginLeft: 6 }}>{isOpen ? '▼' : '▶'}</span>
                  </div>
                  {isOpen && (
                    <div className="log-det open">
                      <div className="ld-grid">
                        <div><div className="ld-lbl">Agente</div><div className="ld-val">{entry.agent_slug ?? '—'}</div></div>
                        <div><div className="ld-lbl">Usuário</div><div className="ld-val">{entry.actor ?? 'Sistema'}</div></div>
                        <div><div className="ld-lbl">Ação</div><div className="ld-val">{entry.action}</div></div>
                        {value && <div><div className="ld-lbl">Valor</div><div className="ld-val" style={{ fontFamily: 'var(--mono)' }}>{value}</div></div>}
                        <div><div className="ld-lbl">Entidade</div><div className="ld-val">{entry.entity_type ?? '—'}</div></div>
                        <div><div className="ld-lbl">ID</div><div className="ld-val" style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{entry.entity_id ?? '—'}</div></div>
                      </div>
                      {justification && (
                        <>
                          <div className="ld-just-hd">Justificativa</div>
                          <div className="ld-just">{justification}</div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* LGPD */}
      <div className={`ad-tc${tab === 'lgpd' ? ' on' : ''}`}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 640 }}>
          <div style={{ background: 'var(--odim)', border: '1px solid rgba(16,185,129,.3)', borderRadius: 'var(--r)', padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'center' }}>
            <CheckCircle size={20} weight="fill" color="var(--ok)" />
            <div><div style={{ fontWeight: 600, fontSize: 13 }}>LGPD em conformidade</div><div style={{ fontSize: 11.5, color: 'var(--mu)', marginTop: 2 }}>Políticas ativas de retenção e portabilidade</div></div>
          </div>
          <div className="lgpd-sec">
            <div className="lgpd-ttl">Exportar dados</div>
            <div className="lgpd-desc">Baixe uma cópia de todos os dados processados pelo Blu para auditoria ou portabilidade.</div>
            <div className="lgpd-act">
              <button className="btn bs" style={{ fontSize: 11.5, display: 'flex', alignItems: 'center', gap: 5 }} disabled={exportData.isPending} onClick={() => exportData.mutate()}>
                <FileArrowDown size={12} />
                {exportData.isPending ? 'Gerando…' : 'Exportar tudo (JSON)'}
              </button>
              <button className="btn bs" style={{ fontSize: 11.5, display: 'flex', alignItems: 'center', gap: 5 }}><ChartBar size={12} />Por agente</button>
              <button className="btn bs" style={{ fontSize: 11.5, display: 'flex', alignItems: 'center', gap: 5 }}><Table size={12} />CSV resumido</button>
            </div>
          </div>
          <div className="lgpd-sec">
            <div className="lgpd-ttl">Exclusão e anonimização</div>
            <div className="lgpd-desc">Remova ou anonimize dados específicos conforme solicitações de titulares ou fins de retenção.</div>
            <div className="lgpd-act">
              <button className="btn bs" style={{ fontSize: 11.5, display: 'flex', alignItems: 'center', gap: 5 }}><Broom size={12} />Anonimizar usuários inativos</button>
              <button className="btn bs" style={{ fontSize: 11.5, display: 'flex', alignItems: 'center', gap: 5 }}><Trash size={12} />Limpar logs antigos (&gt;2 anos)</button>
              <button className="btn brd" style={{ fontSize: 11.5, display: 'flex', alignItems: 'center', gap: 5 }} disabled={deleteData.isPending} onClick={() => setConfirmDelete(true)}>
                <Warning size={12} />
                {deleteData.isPending ? 'Processando…' : 'Excluir conta'}
              </button>
            </div>
          </div>

          {confirmDelete && (
            <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Excluir conta permanentemente?" width="360px">
              <div style={{ fontSize: 12, color: 'var(--mu)', marginBottom: 20 }}>Esta ação não pode ser desfeita. Todos os dados serão removidos.</div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button className="btn bs" onClick={() => setConfirmDelete(false)}>Cancelar</button>
                <button className="btn brd" style={{ display: 'flex', alignItems: 'center', gap: 5 }} onClick={() => { setConfirmDelete(false); deleteData.mutate() }}>
                  <Warning size={12} />Excluir
                </button>
              </div>
            </Modal>
          )}
          <div className="lgpd-sec">
            <div className="lgpd-ttl">Retenção de dados</div>
            <div className="lgpd-desc">Define por quanto tempo o Blu mantém logs de decisão e dados operacionais.</div>
            <div className="pills"><span className="pill">6 meses</span><span className="pill on">1 ano</span><span className="pill">2 anos</span><span className="pill">Indefinido</span></div>
          </div>
        </div>
      </div>

      {/* CONTEXTO */}
      <div className={`ad-tc${tab === 'contexto' ? ' on' : ''}`} style={tab === 'contexto' ? { padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' } : {}}>
        <div className="ctx-grid" style={{ flex: 1, minHeight: 0, width: '100%', height: 'auto' }}>
          <div className="ctx-map-wrap" style={{ minWidth: 0 }}>
            <div className="ctx-svg-cont">
              <svg width="100%" height="100%" viewBox="0 0 540 380" style={{ display: 'block' }}>
                <defs>
                  <radialGradient id="cg" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="rgba(140,95,219,0.2)" />
                    <stop offset="100%" stopColor="rgba(140,95,219,0)" />
                  </radialGradient>
                </defs>
                <circle cx="270" cy="190" r="120" fill="url(#cg)" />
                {[[270,190,270,60],[270,190,400,130],[270,190,370,300],[270,190,140,300],[270,190,130,130]].map(([x1,y1,x2,y2],i) => (
                  <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--gb)" strokeWidth="1.5" />
                ))}
                <circle cx="270" cy="190" r="32" fill="rgba(140,95,219,0.2)" stroke="rgba(140,95,219,0.5)" strokeWidth="1.5" />
                <text x="270" y="185" textAnchor="middle" fill="white" fontSize="13" fontWeight="700">{ctxScore}%</text>
                <text x="270" y="200" textAnchor="middle" fill="rgba(223,227,238,0.6)" fontSize="9">NEGÓCIO</text>
                {[
                  { x: 270, y: 60,  ...domainData[4] },
                  { x: 400, y: 130, ...domainData[0] },
                  { x: 370, y: 300, ...domainData[1] },
                  { x: 140, y: 300, ...domainData[2] },
                  { x: 130, y: 130, ...domainData[3] },
                ].map((d, i) => (
                  <g key={i} className="ctx-node" style={{ cursor: 'pointer' }}>
                    <circle cx={d.x} cy={d.y} r="26" fill="rgba(255,255,255,0.04)" stroke={d.color} strokeWidth="1.5" strokeOpacity="0.6" />
                    <text x={d.x} y={d.y - 4} textAnchor="middle" fontSize="14">{d.icon}</text>
                    <text x={d.x} y={d.y + 10} textAnchor="middle" fill={d.color} fontSize="9.5" fontWeight="700">{d.pct}%</text>
                    <text x={d.x} y={d.y + 42} textAnchor="middle" fill="rgba(223,227,238,0.6)" fontSize="9">{d.name}</text>
                  </g>
                ))}
              </svg>
            </div>
          </div>

          <div className="ctx-right">
            <div className="ctx-overall">
              <div className="ctx-score" style={{ color: 'var(--att)' }}>{ctxScore}%</div>
              <div className="ctx-score-lbl">Cobertura de contexto</div>
            </div>
            <div className="ctx-cov-sec">
              <div className="ctx-cov-ttl">Por domínio</div>
              {domainData.map((d, i) => (
                <div key={i} className="ctx-dom-row">
                  <span className="ctx-dom-icon">{getDomainIcon(d.name)}</span>
                  <span className="ctx-dom-name">{d.name}</span>
                  <div className="ctx-dom-bar"><div className="ctx-dom-fill" style={{ width: `${d.pct}%`, background: d.color }} /></div>
                  <span className="ctx-dom-pct" style={{ color: d.color }}>{d.pct}%</span>
                </div>
              ))}
            </div>
            <div className="ctx-agents">
              <div className="ctx-cov-ttl">Prontidão dos agentes</div>
              {agentReadinessData.map((a, i) => (
                <div key={i} className="ctx-agent-row">
                  <span className="ctx-agent-ic">{a.icon}</span>
                  <span className="ctx-agent-name">{a.name}</span>
                  <span className={`ctx-agent-status ${a.st}`}>{a.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>

      {/* NOTIFICAÇÕES */}
      <div className={`ad-tc${tab === 'notificacoes' ? ' on' : ''}`} style={{ maxWidth: 640 }}>
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Preferências de Notificação</div>
          <div style={{ fontSize: 11.5, color: 'var(--mu)' }}>Escolha quais eventos geram alertas e por quais canais.</div>
        </div>

        {notifLoading ? (
          <div style={{ color: 'var(--mu)', fontSize: 12, padding: '16px 0' }}>Carregando preferências…</div>
        ) : (
          <>
            {/* Channel toggles */}
            <div className="lgpd-sec" style={{ marginBottom: 10 }}>
              <div className="lgpd-ttl">Canais ativos</div>
              {([
                { key: 'channel_email',     label: 'E-mail' },
                { key: 'channel_push',      label: 'Push (mobile)' },
                { key: 'channel_whatsapp',  label: 'WhatsApp Business' },
              ] as const).map(ch => (
                <div key={ch.key} className="perm-row" style={{ paddingLeft: 0 }}>
                  <span className="perm-nm">{ch.label}</span>
                  <Toggle
                    checked={Boolean(notifPrefs?.[ch.key])}
                    onChange={async () => {
                      if (saveNotifPrefs.isPending) return
                      await saveNotifPrefs.mutateAsync({ [ch.key]: !notifPrefs?.[ch.key] })
                    }}
                  />
                </div>
              ))}
            </div>

            {/* Event kind toggles */}
            <div className="lgpd-sec">
              <div className="lgpd-ttl">Tipos de evento</div>
              {([
                { kind: 'new_approval',      label: 'Nova aprovação pendente' },
                { kind: 'approval_urgent',   label: 'Aprovação urgente' },
                { kind: 'approval_overdue',  label: 'Aprovação atrasada' },
                { kind: 'agent_error',       label: 'Erro em agente' },
                { kind: 'insight_new',       label: 'Novo insight gerado' },
                { kind: 'trust_milestone',   label: 'Marco de confiança atingido' },
                { kind: 'report_ready',      label: 'Relatório disponível' },
                { kind: 'integration_error', label: 'Erro em integração' },
                { kind: 'billing_event',     label: 'Evento de faturamento' },
              ]).map(ev => {
                const enabled = (notifPrefs?.kinds_enabled ?? []).includes(ev.kind)
                const isSaving = savingKind === ev.kind
                return (
                  <div key={ev.kind} className="perm-row" style={{ paddingLeft: 0 }}>
                    <span className="perm-nm">{ev.label}</span>
                    <Toggle
                      checked={enabled}
                      disabled={isSaving}
                      onChange={async () => {
                        if (isSaving || saveNotifPrefs.isPending) return
                        setSavingKind(ev.kind)
                        const current = notifPrefs?.kinds_enabled ?? []
                        const next = enabled
                          ? current.filter(k => k !== ev.kind)
                          : [...current, ev.kind]
                        await saveNotifPrefs.mutateAsync({ kinds_enabled: next })
                        setSavingKind(null)
                      }}
                    />
                  </div>
                )
              })}
            </div>

            <div style={{ fontSize: 11, color: 'var(--mu)', marginTop: 10 }}>
              WhatsApp disponível nos planos Growth e Enterprise.
            </div>
          </>
        )}
      </div>

      {/* FATURAMENTO */}
      <div className={`ad-tc${tab === 'faturamento' ? ' on' : ''}`} style={{ maxWidth: 700 }}>
        {/* Current plan */}
        <div style={{ background: 'var(--glass)', border: '1px solid rgba(140,95,219,.35)', borderRadius: 'var(--rl)', padding: '16px 18px', marginBottom: 14, backdropFilter: 'blur(12px)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 4 }}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--ac)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                <span style={{ fontSize: 13.5, fontWeight: 700 }}>Plano atual: Starter</span>
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--mu)', marginBottom: 6 }}>Para negócios que estão crescendo.</div>
              <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--mono)', letterSpacing: '-1px' }}>R$ 197<span style={{ fontSize: 13, fontWeight: 400, color: 'var(--mu)' }}>/mês</span></div>
            </div>
            <span style={{ fontSize: 9.5, fontWeight: 700, padding: '3px 8px', borderRadius: 4, background: 'var(--odim)', color: 'var(--ok)' }}>Starter</span>
          </div>
          <button
            className="btn bp"
            style={{ fontSize: 11.5, marginTop: 12 }}
            onClick={() => window.open('https://blu.ai/planos', '_blank', 'noopener')}
          >
            Fazer upgrade para Growth ↗
          </button>
        </div>

        {/* Plans grid */}
        <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 8 }}>Todos os planos</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8, marginBottom: 14 }}>
          {([
            { tier: 'Free',       price: 'R$ 0/mês',      color: 'var(--blue2)', features: ['1 agente', '20 aprovações/mês', 'Histórico 7 dias'] },
            { tier: 'Starter',    price: 'R$ 197/mês',    color: '#5FB8A3', features: ['3 agentes', 'Aprovações ilimitadas', 'Histórico 90 dias'], current: true },
            { tier: 'Growth',     price: 'R$ 397/mês',    color: '#D4A843', features: ['6 agentes', 'Automações ilimitadas', 'Multi-usuário (5)'] },
            { tier: 'Enterprise', price: 'Sob consulta',  color: '#E07A5F', features: ['Tudo do Growth', 'Usuários ilimitados', 'SLA garantido'] },
          ]).map(p => (
            <div
              key={p.tier}
              style={{
                background: p.current ? 'var(--glass)' : 'rgba(0,0,0,.2)',
                border: `1px solid ${p.current ? 'rgba(140,95,219,.4)' : 'var(--gb)'}`,
                borderRadius: 'var(--r)',
                padding: '10px 12px',
                opacity: p.current ? 1 : 0.7,
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 700, color: p.color, marginBottom: 2 }}>{p.tier}</div>
              <div style={{ fontSize: 13, fontWeight: 800, fontFamily: 'var(--mono)', marginBottom: 8 }}>{p.price}</div>
              {p.features.map(f => (
                <div key={f} style={{ fontSize: 10.5, color: 'var(--mu2)', display: 'flex', alignItems: 'center', gap: 5, marginBottom: 3 }}>
                  <IconCheck size={10} weight="bold" color={p.color} />
                  {f}
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Billing actions */}
        <div className="lgpd-sec">
          <div className="lgpd-ttl">Faturamento</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 12, color: 'var(--mu2)' }}>Histórico de faturas</span>
              <button className="btn bs" style={{ fontSize: 10.5 }} onClick={() => window.open('https://blu.ai/faturas', '_blank', 'noopener')}>Ver faturas ↗</button>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 12, color: 'var(--mu2)' }}>Método de pagamento</span>
              <button className="btn bs" style={{ fontSize: 10.5 }} onClick={() => window.open('https://blu.ai/pagamento', '_blank', 'noopener')}>Gerenciar ↗</button>
            </div>
          </div>
        </div>
      </div>

      {/* POLP BANK AUTH — waiting banner */}
      {(polpAuthUrl || polpPendingIntgId) && (
        <div className="intg-modal open">
          <div className="intg-box" style={{ width: 420, maxWidth: '95vw' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{ fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}><Bank size={14} /> Autenticação bancária</span>
              <button className="btn bg" style={{ fontSize: 11, padding: '3px 10px' }} onClick={() => { setPolpAuthUrl(null); setPolpPendingIntgId(null); void refetchIntegrations() }}>Fechar</button>
            </div>
            {polpPendingIntgId && !polpAuthUrl ? (
              <p style={{ fontSize: 12, color: 'var(--mu)', margin: '0 0 16px' }}>
                Aguardando URL de autenticação do banco… (pode levar alguns segundos)
              </p>
            ) : (
              <>
                <p style={{ fontSize: 12, color: 'var(--mu)', margin: '0 0 16px' }}>
                  Clique no botão abaixo para acessar a página do seu banco e autorizar o acesso. Volte aqui quando concluir.
                </p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className="btn bp"
                    style={{ flex: 1, fontSize: 12 }}
                    onClick={() => window.open(polpAuthUrl!, '_blank', 'noopener,noreferrer')}
                  >
                    Ir para o banco →
                  </button>
                  <button
                    className="btn bs"
                    style={{ flex: 1, fontSize: 12 }}
                    onClick={() => { setPolpAuthUrl(null); void refetchIntegrations() }}
                  >
                    Já autorizei ✓
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* MODAL */}
      {modalIntgId && modalCatalogIntg && (
        <div className="intg-modal open" onClick={() => setModalIntgId(null)}>
          <div className="intg-box" onClick={e => e.stopPropagation()}>
            {modalMode === 'connect' ? (
              <>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: 6 }}>{getProviderIcon(modalCatalogIntg.provider, 16)} Conectar {modalCatalogIntg.name}</h3>
                {OAUTH_PROVIDERS.has(modalCatalogIntg.provider) ? (
                  <>
                    <div className="msub">
                      {modalCatalogIntg.provider === 'google_calendar'
                        ? 'Autorize o acesso à sua conta Google para sincronizar a agenda. Você será redirecionado para o Google e voltará aqui automaticamente.'
                        : modalCatalogIntg.provider === 'google_drive'
                          ? 'Autorize o acesso ao Google Drive para importar planilhas diretamente. Concede acesso a Drive e Calendar na mesma autorização.'
                          : 'Autorize o acesso via OAuth. Você será redirecionado e voltará aqui automaticamente.'}
                    </div>
                    <div className="modal-acts">
                      <button className="btn bg" onClick={() => setModalIntgId(null)}>Cancelar</button>
                      <button
                        className="btn bp"
                        style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                        onClick={() => {
                          setModalIntgId(null)
                          if (modalCatalogIntg.provider === 'google_calendar') {
                            void connectGoogleCalendar()
                          } else if (modalCatalogIntg.provider === 'google_drive') {
                            localStorage.setItem('admin_drive_oauth_pending', '1')
                            void connectGoogleDrive(window.location.href)
                          }
                        }}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
                        Conectar com Google
                      </button>
                    </div>
                  </>
                ) : modalCatalogIntg.provider === 'conta_azul' ? (
                  <>
                    <div className="msub">Insira o e-mail e a senha que você usa para entrar no Conta Azul.</div>
                    <div className="intg-field">
                      <label>E-mail do Conta Azul</label>
                      <input
                        type="email"
                        placeholder="voce@empresa.com.br"
                        value={connFormData.username ?? ''}
                        onChange={e => setConnFormData(d => ({ ...d, username: e.target.value }))}
                      />
                    </div>
                    <div className="intg-field">
                      <label>Senha do Conta Azul</label>
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={connFormData.password ?? ''}
                        onChange={e => setConnFormData(d => ({ ...d, password: e.target.value }))}
                      />
                    </div>
                    {connError && <div style={{ fontSize: 12, color: 'var(--urg)', margin: '4px 0' }}>{connError}</div>}
                    <div className="modal-acts">
                      <button className="btn bg" onClick={() => setModalIntgId(null)}>Cancelar</button>
                      <button
                        className="btn bp"
                        disabled={connSaving || !connFormData.username || !connFormData.password}
                        onClick={doConnect}
                      >
                        {connSaving ? 'Conectando…' : 'Conectar'}
                      </button>
                    </div>
                  </>
                ) : modalCatalogIntg.provider === 'bigquery' ? (
                  <>
                    <div className="msub">Cole o conteúdo do arquivo JSON da Service Account do Google Cloud (contém project_id).</div>
                    <div className="intg-field">
                      <label>Service Account JSON</label>
                      <textarea
                        rows={5}
                        placeholder={'{"type": "service_account", "project_id": "...", ...}'}
                        value={connFormData.service_account_json ?? ''}
                        onChange={e => setConnFormData(d => ({ ...d, service_account_json: e.target.value }))}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid var(--gb)', background: 'var(--bg)', color: 'var(--fg)', fontSize: 11, fontFamily: 'monospace', resize: 'vertical' }}
                      />
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <div className="intg-field" style={{ flex: 1 }}>
                        <label>Dataset ID</label>
                        <input type="text" placeholder="meu_dataset" value={connFormData.dataset_id ?? ''} onChange={e => setConnFormData(d => ({ ...d, dataset_id: e.target.value }))} />
                      </div>
                      <div className="intg-field" style={{ flex: 1 }}>
                        <label>Nome da tabela</label>
                        <input type="text" placeholder="minha_tabela" value={connFormData.table_name ?? ''} onChange={e => setConnFormData(d => ({ ...d, table_name: e.target.value }))} />
                      </div>
                    </div>
                    <div className="intg-field">
                      <label>Região</label>
                      <select value={connFormData.location ?? 'southamerica-east1'} onChange={e => setConnFormData(d => ({ ...d, location: e.target.value }))} style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid var(--gb)', background: 'var(--bg)', color: 'var(--fg)', fontSize: 12 }}>
                        <option value="southamerica-east1">South America — São Paulo</option>
                        <option value="US">United States (US)</option>
                        <option value="EU">European Union (EU)</option>
                        <option value="us-east1">US East</option>
                        <option value="us-west1">US West</option>
                        <option value="asia-northeast1">Asia Northeast — Tokyo</option>
                      </select>
                    </div>
                    {connError && <div style={{ fontSize: 12, color: 'var(--urg)', margin: '4px 0' }}>{connError}</div>}
                    <div className="modal-acts">
                      <button className="btn bg" onClick={() => setModalIntgId(null)}>Cancelar</button>
                      <button
                        className="btn bp"
                        disabled={connSaving || !connFormData.service_account_json || !connFormData.dataset_id || !connFormData.table_name}
                        onClick={doConnect}
                      >
                        {connSaving ? 'Conectando…' : 'Conectar'}
                      </button>
                    </div>
                  </>
                ) : modalCatalogIntg.provider === 'polp' ? (
                  <>
                    <div className="msub">Conecte sua conta bancária via Open Finance. Você será redirecionado para autenticação segura com o banco.</div>
                    <div className="intg-field">
                      <label>Banco / Instituição</label>
                      <select
                        value={connFormData.institution_id ?? ''}
                        onChange={e => setConnFormData(d => ({ ...d, institution_id: e.target.value }))}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid var(--gb)', background: 'var(--bg)', color: 'var(--fg)', fontSize: 12 }}
                      >
                        <option value="">Selecione o banco…</option>
                        {POLP_INSTITUTIONS.map(inst => (
                          <option key={inst.id} value={inst.id}>{inst.name}</option>
                        ))}
                      </select>
                    </div>
                    {connFormData.institution_id === '0' && (
                      <div className="intg-field">
                        <label>ID da Instituição (manual)</label>
                        <input
                          type="number"
                          placeholder="ex: 341"
                          value={connFormData.institution_id_manual ?? ''}
                          onChange={e => setConnFormData(d => ({ ...d, institution_id: e.target.value, institution_id_manual: e.target.value }))}
                        />
                      </div>
                    )}
                    <div className="intg-field">
                      <label>CPF do titular (opcional)</label>
                      <input
                        type="text"
                        placeholder="000.000.000-00"
                        value={connFormData.cpf ?? ''}
                        onChange={e => setConnFormData(d => ({ ...d, cpf: e.target.value }))}
                      />
                    </div>
                    <div className="intg-field">
                      <label>CNPJ da empresa (opcional)</label>
                      <input
                        type="text"
                        placeholder="00.000.000/0000-00"
                        value={connFormData.cnpj ?? ''}
                        onChange={e => setConnFormData(d => ({ ...d, cnpj: e.target.value }))}
                      />
                    </div>
                    {connError && <div style={{ fontSize: 12, color: 'var(--urg)', margin: '4px 0' }}>{connError}</div>}
                    <div className="modal-acts">
                      <button className="btn bg" onClick={() => setModalIntgId(null)}>Cancelar</button>
                      <button
                        className="btn bp"
                        disabled={connSaving || !connFormData.institution_id}
                        onClick={doConnect}
                      >
                        {connSaving ? 'Conectando…' : 'Conectar banco →'}
                      </button>
                    </div>
                  </>
                ) : (modalCatalogIntg.provider === 'slack' || modalCatalogIntg.provider === 'monday' ||
                     modalCatalogIntg.provider === 'notion' || modalCatalogIntg.provider === 'asana' ||
                     modalCatalogIntg.provider === 'clickup' || modalCatalogIntg.provider === 'linear') ? (
                  <>
                    <div className="msub">
                      {modalCatalogIntg.provider === 'slack'
                        ? 'Cole o Bot Token do Slack (começa com xoxb-). Crie em api.slack.com/apps → OAuth & Permissions.'
                        : modalCatalogIntg.provider === 'monday'
                        ? 'Cole o API Token do Monday.com. Crie em monday.com → Avatar → Admin → API.'
                        : modalCatalogIntg.provider === 'notion'
                        ? 'Cole o token de integração do Notion (começa com secret_). Crie em notion.so/my-integrations.'
                        : modalCatalogIntg.provider === 'asana'
                        ? 'Cole o Personal Access Token do Asana. Crie em app.asana.com/0/my-apps.'
                        : modalCatalogIntg.provider === 'clickup'
                        ? 'Cole a API Key do ClickUp (começa com pk_). Crie em clickup.com → Settings → Apps.'
                        : 'Cole a API Key do Linear (começa com lin_api_). Crie em linear.app → Settings → API.'}
                    </div>
                    <div className="intg-field">
                      <label>{modalCatalogIntg.provider === 'slack' ? 'Bot Token (xoxb-…)' : 'API Token'}</label>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'stretch' }}>
                        <input
                          type="password"
                          placeholder={
                            modalCatalogIntg.provider === 'slack' ? 'xoxb-…'
                            : modalCatalogIntg.provider === 'monday' ? 'eyJhbG...NiJ9…'
                            : modalCatalogIntg.provider === 'notion' ? 'secret_…'
                            : modalCatalogIntg.provider === 'asana' ? '1/…'
                            : modalCatalogIntg.provider === 'clickup' ? 'pk_…'
                            : 'lin_api_…'
                          }
                          value={connFormData.api_token ?? ''}
                          onChange={e => setConnFormData(d => ({ ...d, api_token: e.target.value }))}
                          autoComplete="new-password"
                          style={{ flex: 1 }}
                        />
                        <button
                          className="btn bg"
                          style={{ whiteSpace: 'nowrap', fontSize: 11, padding: '0 10px' }}
                          onClick={async () => {
                            try {
                              const text = await navigator.clipboard.readText()
                              setConnFormData(d => ({ ...d, api_token: text.trim() }))
                            } catch {
                              // clipboard permission denied — user must paste manually
                            }
                          }}
                        >
                          Colar
                        </button>
                      </div>
                      {connFormData.api_token && (
                        <div style={{ fontSize: 10, color: 'var(--fg2)', marginTop: 3 }}>
                          {connFormData.api_token.length} caracteres · termina em …{connFormData.api_token.slice(-6)}
                        </div>
                      )}
                    </div>
                    {connError && <div style={{ fontSize: 12, color: 'var(--urg)', margin: '4px 0' }}>{connError}</div>}
                    <div className="modal-acts">
                      <button className="btn bg" onClick={() => setModalIntgId(null)}>Cancelar</button>
                      <button
                        className="btn bp"
                        disabled={connSaving || !connFormData.api_token}
                        onClick={doConnect}
                      >
                        {connSaving ? 'Conectando…' : 'Conectar'}
                      </button>
                    </div>
                  </>
                ) : null}
              </>
            ) : (
              <>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: 6 }}>{getProviderIcon(modalCatalogIntg.provider, 16)} {modalCatalogIntg.name} — Configuração</h3>
                <div className="msub">Conectado e sincronizando normalmente.</div>
                {modalDbIntg?.connection_detail && (
                  <div className="intg-field"><label>Conexão</label><input value={modalDbIntg.connection_detail} readOnly style={{ opacity: .7 }} /></div>
                )}
                {modalDbIntg?.last_synced_at && (
                  <div className="intg-field"><label>Última sincronização</label><input value={new Date(modalDbIntg.last_synced_at).toLocaleString('pt-BR')} readOnly style={{ opacity: .7 }} /></div>
                )}
                <hr className="modal-sep" />
                <div className="modal-acts">
                  <button className="btn brd" disabled={disconnect.isPending} onClick={doDisconnect}>
                    {disconnect.isPending ? 'Desconectando…' : 'Desconectar'}
                  </button>
                  <button className="btn bp" onClick={() => setModalIntgId(null)}>Fechar</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
