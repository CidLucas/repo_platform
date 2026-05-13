import { useState } from 'react'
import { useAppStore } from '../../store/appStore'
import { useIntegrations, useDisconnectIntegration, useAuditLog, useRequestDataExport, useRequestDataDeletion, useTeamMembers, useUpdateUserPermissions, useInviteUser } from '../../hooks/useAdmin'
import { useStartSync } from '../../hooks/useConnectorStatus'
import { useNotificationPreferences, useSaveNotificationPreferences } from '../../hooks/useNotifications'
import { connectGoogleCalendar } from '../../api/agenda'
import { createCredential } from '../../api/connectors'
import { supabase } from '@blu/auth'
import type { Integration, AuditEntry } from '../../api/admin'

type AdminTab = 'integracoes' | 'usuarios' | 'auditoria' | 'notificacoes' | 'faturamento' | 'lgpd' | 'contexto' | 'rotinas'

// ── Static catalogs ──────────────────────────────────────────────────────────

interface CatalogIntegration {
  id: string
  icon: string
  name: string
  desc: string
  provider: string // matches credencial_servico_externo.tipo normalized
}

const LANES: { label: string; integrations: CatalogIntegration[] }[] = [
  {
    label: 'ERPs & Gestão',
    integrations: [
      { id: 'ic-conta-azul', icon: '📋', name: 'Conta Azul', desc: 'NF-e e financeiro', provider: 'conta_azul' },
    ],
  },
  {
    label: 'Agenda',
    integrations: [
      { id: 'ic-gcal', icon: '📅', name: 'Google Calendar', desc: 'Agenda', provider: 'google_calendar' },
    ],
  },
  {
    label: 'Dados & Analytics',
    integrations: [
      { id: 'ic-bigquery', icon: '🗄️', name: 'BigQuery',   desc: 'Data warehouse',  provider: 'bigquery' },
      { id: 'ic-postgres', icon: '🐘', name: 'PostgreSQL', desc: 'Banco relacional', provider: 'postgresql' },
    ],
  },
]

// Providers that use OAuth redirect instead of API key forms
const OAUTH_PROVIDERS = new Set(['google_calendar'])

function getDbIntegration(provider: string, dbList: Integration[]): Integration | undefined {
  return dbList.find(i => i.provider === provider)
}

function isConnected(provider: string, dbList: Integration[]): boolean {
  return getDbIntegration(provider, dbList)?.status === 'connected'
}

function agentReadiness(dbList: Integration[]): { icon: string; name: string; status: string; st: string }[] {
  const AGENT_PROVIDERS: Record<string, string[]> = {
    financeiro: ['conta_azul'],
    estrategia: ['bigquery', 'postgresql'],
    clientes:   ['conta_azul'],
    compras:    ['conta_azul'],
    documentos: ['google_calendar'],
    agenda:     ['google_calendar'],
  }
  const ICONS: Record<string, string> = { financeiro: '📊', estrategia: '🎯', clientes: '👥', compras: '🛒', documentos: '✍️', agenda: '📅' }
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
  const MAP: Record<string, string> = { compras: '#818cf8', financeiro: '#34d399', agenda: '#fb923c', documentos: '#f472b6', estrategia: '#fbbf24', clientes: '#2dd4bf' }
  return (slug && MAP[slug]) ? MAP[slug] : '#94a3b8'
}

// Static catalog mirrors cross_agent_routines seed data
const ROUTINE_CATALOG = [
  { id: 'new_event_confirmed', name: 'Novo Evento Confirmado', domain: 'operacoes', trigger: 'Contrato de venda assinado' },
  { id: 'project_wrap',        name: 'Encerramento de Projeto', domain: 'agenda',    trigger: 'Cronograma do evento concluído' },
  { id: 'churn_prevention',    name: 'Prevenção de Churn',      domain: 'operacoes', trigger: '45 dias sem compra' },
  { id: 'price_spike_response',name: 'Resposta a Alta de Preço',domain: 'operacoes', trigger: 'Alta de preço > 15%' },
  { id: 'monthly_close',       name: 'Fechamento Mensal',       domain: 'system',    trigger: 'Último dia do mês (cron)' },
]



export default function AdminScreen() {
  const go = useAppStore(s => s.go)
  const [tab, setTab] = useState<AdminTab>('integracoes')
  const [expandedLog, setExpandedLog] = useState<string | null>(null)
  const [expandedUser, setExpandedUser] = useState<string | null>(null)
  const [modalIntgId, setModalIntgId] = useState<string | null>(null) // catalog id
  const [modalMode, setModalMode] = useState<'connect' | 'config'>('connect')
  const [logSearch, setLogSearch] = useState('')
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteForm, setInviteForm] = useState({ name: '', email: '', role: 'member' })
  const [enqueuingRoutine, setEnqueuingRoutine] = useState<string | null>(null)
  const [routineResult, setRoutineResult] = useState<Record<string, 'ok' | 'err' | 'dup'>>({})


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

  // Notifications tab
  const { data: notifPrefs, isLoading: notifLoading } = useNotificationPreferences()
  const saveNotifPrefs = useSaveNotificationPreferences()
  const [savingKind, setSavingKind] = useState<string | null>(null)

  const auditEntries: AuditEntry[] = auditData?.entries ?? []
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
    }
    setModalIntgId(null)
  }

  async function doEnqueueRoutine(routineId: string) {
    setEnqueuingRoutine(routineId)
    try {
      const { data, error } = await supabase.rpc('enqueue_routine_for_me', { p_routine_id: routineId })
      if (error) throw error
      setRoutineResult(r => ({ ...r, [routineId]: data ? 'ok' : 'dup' }))
    } catch {
      setRoutineResult(r => ({ ...r, [routineId]: 'err' }))
    } finally {
      setEnqueuingRoutine(null)
    }
  }

  const TABS: { id: AdminTab; label: string }[] = [
    { id: 'integracoes',  label: '🔗 Integrações' },
    { id: 'usuarios',     label: '👥 Usuários' },
    { id: 'auditoria',   label: '📋 Auditoria' },
    { id: 'notificacoes', label: '🔔 Notificações' },
    { id: 'faturamento',  label: '💳 Faturamento' },
    { id: 'lgpd',         label: '🔒 LGPD' },
    { id: 'contexto',     label: '🗺️ Contexto' },
    { id: 'rotinas',      label: '⚡ Rotinas' },
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
        <div className="rav">⚙️</div>
        <div><div className="rn">Admin</div><div className="rd">Configurações, integrações e controles</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
        </div>
      </div>

      <div className="ad-tabs">
        {TABS.map(t => (
          <div key={t.id} className={`ad-tab${tab === t.id ? ' on' : ''}`} onClick={() => setTab(t.id)}>{t.label}</div>
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
                      {intg.icon}
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
                        <div
                          className={`ptog${enabled ? ' on' : ''}`}
                          onClick={() => updatePermissions.mutate({
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
                        <div
                          className={`ptog${enabled ? ' on' : ''}`}
                          onClick={() => updatePermissions.mutate({
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
        {showInviteModal && (
          <div
            style={{ position: 'fixed', inset: 0, background: '#0008', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            onClick={() => setShowInviteModal(false)}
          >
            <div
              style={{ background: 'var(--bg)', borderRadius: 14, padding: 24, width: 320, boxShadow: '0 8px 32px #0004' }}
              onClick={e => e.stopPropagation()}
            >
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Adicionar usuário</div>

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
                <button
                  style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid var(--gb)', background: 'transparent', color: 'var(--mu)', fontSize: 12, cursor: 'pointer' }}
                  onClick={() => setShowInviteModal(false)}
                >
                  Cancelar
                </button>
                <button
                  style={{ padding: '6px 14px', borderRadius: 8, border: 'none', background: 'var(--ac)', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer', opacity: inviteUser.isPending ? 0.6 : 1 }}
                  disabled={!inviteForm.email || inviteUser.isPending}
                  onClick={async () => {
                    await inviteUser.mutateAsync({ email: inviteForm.email, name: inviteForm.name || null, role: inviteForm.role })
                    setShowInviteModal(false)
                  }}
                >
                  {inviteUser.isPending ? 'Adicionando…' : 'Adicionar'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* AUDITORIA */}
      <div className={`ad-tc${tab === 'auditoria' ? ' on' : ''}`}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8, marginBottom: 14 }}>
          <div className="kpi-cell"><div className="kpi-lbl">Total de ações</div><div className="kpi-val">{auditTotal.toLocaleString('pt-BR')}</div><div className="kpi-d" style={{ color: 'var(--mu)' }}>histórico</div></div>
          <div className="kpi-cell"><div className="kpi-lbl">Taxa de aprovação</div><div className="kpi-val">{auditTotal > 0 ? `${approvalRate}%` : '—'}</div><div className="kpi-d" style={{ color: 'var(--mu)' }}>nesta página</div></div>
          <div className="kpi-cell"><div className="kpi-lbl">Economia gerada</div><div className="kpi-val">—</div><div className="kpi-d" style={{ color: 'var(--mu)' }}>em breve</div></div>
          <div className="kpi-cell"><div className="kpi-lbl">Anomalias</div><div className="kpi-val">—</div><div className="kpi-d" style={{ color: 'var(--mu)' }}>em breve</div></div>
        </div>
        <div className="aud-search">
          <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
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
            <span style={{ fontSize: 20 }}>✅</span>
            <div><div style={{ fontWeight: 600, fontSize: 13 }}>LGPD em conformidade</div><div style={{ fontSize: 11.5, color: 'var(--mu)', marginTop: 2 }}>Políticas ativas de retenção e portabilidade</div></div>
          </div>
          <div className="lgpd-sec">
            <div className="lgpd-ttl">Exportar dados</div>
            <div className="lgpd-desc">Baixe uma cópia de todos os dados processados pelo Blu para auditoria ou portabilidade.</div>
            <div className="lgpd-act">
              <button className="btn bs" style={{ fontSize: 11.5 }} disabled={exportData.isPending} onClick={() => exportData.mutate()}>
                {exportData.isPending ? 'Gerando…' : '📁 Exportar tudo (JSON)'}
              </button>
              <button className="btn bs" style={{ fontSize: 11.5 }}>📊 Por agente</button>
              <button className="btn bs" style={{ fontSize: 11.5 }}>📋 CSV resumido</button>
            </div>
          </div>
          <div className="lgpd-sec">
            <div className="lgpd-ttl">Exclusão e anonimização</div>
            <div className="lgpd-desc">Remova ou anonimize dados específicos conforme solicitações de titulares ou fins de retenção.</div>
            <div className="lgpd-act">
              <button className="btn bs" style={{ fontSize: 11.5 }}>🧹 Anonimizar usuários inativos</button>
              <button className="btn bs" style={{ fontSize: 11.5 }}>🗑️ Limpar logs antigos (&gt;2 anos)</button>
              <button className="btn brd" style={{ fontSize: 11.5 }} disabled={deleteData.isPending} onClick={() => deleteData.mutate()}>
                {deleteData.isPending ? 'Processando…' : '⚠️ Excluir conta'}
              </button>
            </div>
          </div>
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
                  <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(255,255,255,0.08)" strokeWidth="1.5" />
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
                  <span className="ctx-dom-icon">{d.icon}</span>
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
                  <div
                    className={`ptog${notifPrefs?.[ch.key] ? ' on' : ''}`}
                    onClick={async () => {
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
                    <div
                      className={`ptog${enabled ? ' on' : ''}${isSaving ? ' disabled' : ''}`}
                      style={{ opacity: isSaving ? 0.5 : 1 }}
                      onClick={async () => {
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
            { tier: 'Free',       price: 'R$ 0/mês',      color: '#4A90D9', features: ['1 agente', '20 aprovações/mês', 'Histórico 7 dias'] },
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
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke={p.color} strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
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

      {/* ROTINAS */}
      <div className={`ad-tc${tab === 'rotinas' ? ' on' : ''}`} style={{ maxWidth: 640 }}>
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Rotinas Automáticas</div>
          <div style={{ fontSize: 11.5, color: 'var(--mu)' }}>
            Rotinas multi-agente que geram tarefas na mesa de trabalho quando acionadas.
            Use "Disparar" para testar manualmente.
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {ROUTINE_CATALOG.map(r => {
            const result = routineResult[r.id]
            const isBusy = enqueuingRoutine === r.id
            return (
              <div
                key={r.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 14px', borderRadius: 'var(--r)',
                  background: 'var(--sb)', border: '1px solid var(--gb)',
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600 }}>{r.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginTop: 2 }}>
                    Gatilho: {r.trigger}
                  </div>
                </div>
                {result === 'ok'  && <span style={{ fontSize: 11, color: 'var(--ok)' }}>Disparado ✓</span>}
                {result === 'dup' && <span style={{ fontSize: 11, color: 'var(--mu)' }}>Já na fila</span>}
                {result === 'err' && <span style={{ fontSize: 11, color: 'var(--urg)' }}>Erro</span>}
                <button
                  className="btn bp"
                  style={{ fontSize: 11, padding: '4px 12px', whiteSpace: 'nowrap' }}
                  disabled={isBusy}
                  onClick={() => doEnqueueRoutine(r.id)}
                >
                  {isBusy ? '…' : '⚡ Disparar'}
                </button>
              </div>
            )
          })}
        </div>
        <div style={{ fontSize: 11, color: 'var(--mu)', marginTop: 14 }}>
          Após disparar, as tarefas aparecem na mesa de trabalho em até 1 minuto (processamento via cron).
        </div>
      </div>

      {/* MODAL */}
      {modalIntgId && modalCatalogIntg && (
        <div className="intg-modal open" onClick={() => setModalIntgId(null)}>
          <div className="intg-box" onClick={e => e.stopPropagation()}>
            {modalMode === 'connect' ? (
              <>
                <h3>{modalCatalogIntg.icon} Conectar {modalCatalogIntg.name}</h3>
                {OAUTH_PROVIDERS.has(modalCatalogIntg.provider) ? (
                  <>
                    <div className="msub">
                      {modalCatalogIntg.provider === 'google_calendar'
                        ? 'Autorize o acesso à sua conta Google para sincronizar a agenda. Você será redirecionado para o Google e voltará aqui automaticamente.'
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
                            void connectGoogleCalendar(window.location.href)
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
                ) : null}
              </>
            ) : (
              <>
                <h3>{modalCatalogIntg.icon} {modalCatalogIntg.name} — Configuração</h3>
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
