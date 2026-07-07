import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import {
  fetchAgentSessions,
  fetchSessionMessages,
  fetchSyncJobs,
  retryJob,
  fetchCredentials,
  toggleCredential,
  type AgentSession,
  type SyncJob,
  type Credential,
} from '../../api/agentOps'
import EmptyState from '../../components/shared/EmptyState'
import LoadingState from '../../components/shared/LoadingState'

// ── helpers ────────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtDuration(sec: number | null) {
  if (sec == null) return '—'
  if (sec < 60) return `${Math.round(sec)}s`
  return `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s`
}

function shortId(id: string) {
  return id.split('-')[0]
}

// ── status pills ───────────────────────────────────────────────────────────────

function StatusPill({ value }: { value: string | null }) {
  if (!value) return <span style={{ color: 'var(--mu)', fontSize: 10 }}>—</span>

  const map: Record<string, { bg: string; color: string }> = {
    completed:  { bg: 'var(--odim)',  color: 'var(--ok)' },
    success:    { bg: 'var(--odim)',  color: 'var(--ok)' },
    ready:      { bg: 'var(--odim)',  color: 'var(--ok)' },
    active:     { bg: 'var(--odim)',  color: 'var(--ok)' },
    pending:    { bg: 'var(--adm2)', color: 'var(--att)' },
    running:    { bg: 'var(--adm2)', color: 'var(--att)' },
    configuring:{ bg: 'var(--adm2)', color: 'var(--att)' },
    failed:     { bg: 'var(--udim)', color: 'var(--urg)' },
    error:      { bg: 'var(--udim)', color: 'var(--urg)' },
    inactive:   { bg: 'var(--glass)', color: 'var(--mu)' },
  }

  const style = map[value.toLowerCase()] ?? { bg: 'var(--glass)', color: 'var(--mu)' }

  return (
    <span style={{
      fontSize: 9,
      fontWeight: 700,
      letterSpacing: '.04em',
      textTransform: 'uppercase',
      padding: '2px 6px',
      borderRadius: 3,
      background: style.bg,
      color: style.color,
      fontFamily: 'var(--mono)',
    }}>
      {value}
    </span>
  )
}

// ── progress bar ──────────────────────────────────────────────────────────────

function ProgressBar({ pct }: { pct: number | null }) {
  if (pct == null) return <span style={{ color: 'var(--mu)', fontSize: 10 }}>—</span>
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 60, height: 3, background: 'var(--gb)', borderRadius: 2, overflow: 'hidden', flexShrink: 0 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: 'var(--ok)', borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--mu)', flexShrink: 0 }}>{pct}%</span>
    </div>
  )
}

// ── table wrapper ─────────────────────────────────────────────────────────────

const thStyle: React.CSSProperties = {
  fontSize: 9,
  fontWeight: 700,
  letterSpacing: '.07em',
  textTransform: 'uppercase',
  color: 'var(--mu)',
  padding: '7px 12px',
  textAlign: 'left',
  borderBottom: '1px solid var(--gb)',
  whiteSpace: 'nowrap',
}

const tdStyle: React.CSSProperties = {
  padding: '7px 12px',
  fontSize: 11.5,
  borderBottom: '1px solid var(--gb)',
  verticalAlign: 'middle',
}

// ── sessions tab ──────────────────────────────────────────────────────────────

function SessionsTab({ clientId }: { clientId: string }) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ['ops-sessions', clientId],
    queryFn: () => fetchAgentSessions(clientId),
    staleTime: 30_000,
  })

  const { data: messages = [], isFetching: msgLoading } = useQuery({
    queryKey: ['ops-messages', expandedId],
    queryFn: () => fetchSessionMessages(expandedId!, clientId),
    enabled: !!expandedId,
    staleTime: 15_000,
  })

  if (isLoading) return <LoadingState variant="row" rows={5} />

  if (sessions.length === 0) return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <EmptyState
        icon="🛰"
        title="Nenhuma sessão registrada ainda"
        description="Sessões de agentes aparecerão aqui assim que forem iniciadas."
      />
    </div>
  )

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead style={{ position: 'sticky', top: 0, background: 'var(--bg)', zIndex: 2 }}>
          <tr>
            <th style={thStyle}>Session ID</th>
            <th style={thStyle}>Catalog ID</th>
            <th style={thStyle}>Status</th>
            <th style={thStyle}>Criado</th>
            <th style={thStyle}>Atualizado</th>
            <th style={thStyle} />
          </tr>
        </thead>
        <tbody>
          {sessions.map((s: AgentSession) => (
            <>
              <tr
                key={s.id}
                style={{ cursor: 'pointer', transition: 'background .1s' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--glass)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                onClick={() => setExpandedId(expandedId === s.id ? null : s.id)}
              >
                <td style={tdStyle}>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--fg)' }}>
                    {shortId(s.session_id)}…
                  </span>
                </td>
                <td style={tdStyle}>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>
                    {shortId(s.agent_catalog_id)}…
                  </span>
                </td>
                <td style={tdStyle}><StatusPill value={s.config_status} /></td>
                <td style={{ ...tdStyle, color: 'var(--mu)', fontFamily: 'var(--mono)', fontSize: 10 }}>{fmtDate(s.created_at)}</td>
                <td style={{ ...tdStyle, color: 'var(--mu)', fontFamily: 'var(--mono)', fontSize: 10 }}>{fmtDate(s.updated_at)}</td>
                <td style={tdStyle}>
                  <span style={{ fontSize: 10, color: 'var(--mu)', transition: 'color .1s' }}>
                    {expandedId === s.id ? '▲' : '▼'}
                  </span>
                </td>
              </tr>
              {expandedId === s.id && (
                <tr key={`${s.id}-exp`}>
                  <td colSpan={6} style={{ padding: 0, background: 'var(--glass)' }}>
                    <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--gb)' }}>
                      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 8 }}>
                        Mensagens da sessão {msgLoading ? '· carregando…' : `· ${messages.length}`}
                      </div>
                      {messages.length === 0 && !msgLoading ? (
                        <EmptyState
                          icon="💬"
                          title="Nenhuma mensagem nesta sessão"
                          description="As mensagens trocadas com o agente aparecerão aqui."
                        />
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 220, overflowY: 'auto' }}>
                          {messages.map(m => (
                            <div key={m.id} style={{
                              display: 'flex', gap: 10, alignItems: 'flex-start',
                              padding: '5px 8px', borderRadius: 5,
                              background: m.role === 'assistant' ? 'var(--adim)' : 'transparent',
                            }}>
                              <span style={{
                                fontSize: 8.5, fontWeight: 700, letterSpacing: '.05em',
                                textTransform: 'uppercase', color: 'var(--mu)',
                                fontFamily: 'var(--mono)', width: 52, flexShrink: 0, paddingTop: 1,
                              }}>
                                {m.role ?? m.direction ?? '?'}
                              </span>
                              <span style={{ fontSize: 11.5, color: 'var(--mu2)', flex: 1, lineHeight: 1.45, wordBreak: 'break-word' }}>
                                {m.body ?? '—'}
                              </span>
                              <span style={{ fontSize: 9.5, color: 'var(--mu)', fontFamily: 'var(--mono)', flexShrink: 0 }}>
                                {new Date(m.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── jobs tab ──────────────────────────────────────────────────────────────────

function JobsTab() {
  const qc = useQueryClient()

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ['ops-jobs'],
    queryFn: fetchSyncJobs,
    staleTime: 20_000,
  })

  const retryMut = useMutation({
    mutationFn: (jobId: string) => retryJob(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ops-jobs'] }),
  })

  if (isLoading) return <LoadingState variant="row" rows={5} />

  if (jobs.length === 0) return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <EmptyState
        icon="⚙️"
        title="Nenhum job de sincronização encontrado"
        description="Jobs de sincronização aparecerão aqui assim que forem executados."
      />
    </div>
  )

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead style={{ position: 'sticky', top: 0, background: 'var(--bg)', zIndex: 2 }}>
          <tr>
            <th style={thStyle}>Job ID</th>
            <th style={thStyle}>Tipo</th>
            <th style={thStyle}>Recurso</th>
            <th style={thStyle}>Modo</th>
            <th style={thStyle}>Status</th>
            <th style={thStyle}>Progresso</th>
            <th style={thStyle}>Linhas</th>
            <th style={thStyle}>Duração</th>
            <th style={thStyle}>Tentativas</th>
            <th style={thStyle}>Criado</th>
            <th style={thStyle} />
          </tr>
        </thead>
        <tbody>
          {jobs.map((j: SyncJob) => {
            const isFailed = j.status === 'failed' || j.status === 'error'
            const isRetrying = retryMut.isPending && retryMut.variables === j.job_id
            return (
              <tr key={j.job_id} style={{ transition: 'background .1s' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--glass)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={tdStyle}>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>
                    {shortId(j.job_id)}…
                  </span>
                </td>
                <td style={{ ...tdStyle, fontFamily: 'var(--mono)', fontSize: 10.5 }}>{j.job_type}</td>
                <td style={{ ...tdStyle, color: 'var(--mu2)', fontSize: 10.5 }}>{j.resource_type ?? '—'}</td>
                <td style={{ ...tdStyle, color: 'var(--mu)', fontSize: 10, fontFamily: 'var(--mono)' }}>{j.sync_mode ?? '—'}</td>
                <td style={tdStyle}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <StatusPill value={j.status} />
                    {isFailed && j.error_message && (
                      <span style={{ fontSize: 9.5, color: 'var(--urg)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {j.error_message}
                      </span>
                    )}
                  </div>
                </td>
                <td style={tdStyle}><ProgressBar pct={j.progress_pct} /></td>
                <td style={{ ...tdStyle, fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--mu2)' }}>
                  {j.rows_inserted != null ? j.rows_inserted.toLocaleString() : '—'}
                </td>
                <td style={{ ...tdStyle, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>
                  {fmtDuration(j.duration_seconds)}
                </td>
                <td style={{ ...tdStyle, fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--mu)', textAlign: 'center' }}>
                  {j.retry_count}
                </td>
                <td style={{ ...tdStyle, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)', whiteSpace: 'nowrap' }}>
                  {fmtDate(j.created_at)}
                </td>
                <td style={tdStyle}>
                  {isFailed && (
                    <button
                      className="btn bs"
                      style={{ fontSize: 10, padding: '3px 8px', opacity: isRetrying ? 0.5 : 1 }}
                      disabled={isRetrying}
                      onClick={() => retryMut.mutate(j.job_id)}
                    >
                      {isRetrying ? '…' : 'Retry'}
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── credentials tab ────────────────────────────────────────────────────────────

function CredentialsTab({ clientId }: { clientId: string }) {
  const qc = useQueryClient()

  const { data: creds = [], isLoading } = useQuery({
    queryKey: ['ops-credentials', clientId],
    queryFn: () => fetchCredentials(clientId),
    staleTime: 60_000,
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, ativo }: { id: number; ativo: boolean }) => toggleCredential(id, ativo),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ops-credentials', clientId] }),
  })

  if (isLoading) return <LoadingState variant="row" rows={5} />

  if (creds.length === 0) return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <EmptyState
        icon="🔑"
        title="Nenhuma credencial configurada"
        description="Credenciais de APIs e integrações aparecerão aqui assim que forem configuradas."
      />
    </div>
  )

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead style={{ position: 'sticky', top: 0, background: 'var(--bg)', zIndex: 2 }}>
          <tr>
            <th style={thStyle}>Nome</th>
            <th style={thStyle}>Serviço</th>
            <th style={thStyle}>Tipo</th>
            <th style={thStyle}>Status</th>
            <th style={thStyle}>Ativo</th>
            <th style={thStyle}>Criado</th>
            <th style={thStyle}>Atualizado</th>
          </tr>
        </thead>
        <tbody>
          {creds.map((c: Credential) => {
            const isToggling = toggleMut.isPending && toggleMut.variables?.id === c.id
            return (
              <tr key={c.id} style={{ transition: 'background .1s' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--glass)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={tdStyle}>
                  <span style={{ fontWeight: 600 }}>{c.nome ?? c.nome_servico ?? `#${c.id}`}</span>
                </td>
                <td style={{ ...tdStyle, color: 'var(--mu2)', fontSize: 11 }}>{c.nome_servico ?? '—'}</td>
                <td style={{ ...tdStyle, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>
                  {c.tipo_servico ?? c.tipo ?? '—'}
                </td>
                <td style={tdStyle}><StatusPill value={c.status} /></td>
                <td style={tdStyle}>
                  <div
                    className={`ptog${c.ativo ? ' on' : ''}`}
                    style={{ opacity: isToggling ? 0.5 : 1 }}
                    onClick={() => !isToggling && toggleMut.mutate({ id: c.id, ativo: !c.ativo })}
                  />
                </td>
                <td style={{ ...tdStyle, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>{fmtDate(c.created_at)}</td>
                <td style={{ ...tdStyle, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>{fmtDate(c.updated_at)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── main screen ───────────────────────────────────────────────────────────────

type Tab = 'sessions' | 'jobs' | 'credentials'

const TABS: { id: Tab; label: string }[] = [
  { id: 'sessions',    label: 'Sessões' },
  { id: 'jobs',        label: 'Sync Jobs' },
  { id: 'credentials', label: 'Credenciais' },
]

export default function AgentOpsRoom() {
  const { clientId } = useAuth()
  const [tab, setTab] = useState<Tab>('sessions')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Room header */}
      <div className="rh">
        <div className="rav">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <path d="M8 21h8M12 17v4"/>
            <path d="M7 8h.01M12 8h.01M17 8h.01"/>
          </svg>
        </div>
        <div>
          <div className="rn">AgentOps</div>
          <div className="rd">Sessões, jobs de sincronização e credenciais</div>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--gb)',
        padding: '0 14px',
        flexShrink: 0,
        background: 'var(--glass)',
      }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              background: 'none',
              border: 'none',
              padding: '9px 14px',
              fontSize: 11.5,
              fontWeight: 500,
              color: tab === t.id ? 'var(--fg)' : 'var(--mu)',
              cursor: 'pointer',
              borderBottom: `2px solid ${tab === t.id ? 'var(--ac)' : 'transparent'}`,
              marginBottom: -1,
              transition: 'color .1s, border-color .1s',
              fontFamily: 'var(--body)',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {tab === 'sessions' && clientId && <SessionsTab clientId={clientId} />}
        {tab === 'jobs' && <JobsTab />}
        {tab === 'credentials' && clientId && <CredentialsTab clientId={clientId} />}
        {!clientId && (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--mu)', fontSize: 12 }}>
            Aguardando autenticação…
          </div>
        )}
      </div>
    </div>
  )
}
