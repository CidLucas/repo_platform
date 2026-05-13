import { useAppStore } from '../../store/appStore'
import { useRecentActivity, useDayStats } from '../../hooks/useRecentActivity'
import { usePendingApprovals } from '../../hooks/useApprovals'
import { useAgentRunsToday, useNpsScore, usePendencias } from '../../hooks/useAnalytics'
import type { RecentActivityItem } from '../../api/activity'
import type { ApprovalRequest } from '../../api/approvals'
import RColResizeHandle from '../../components/shared/RColResizeHandle'

// ── Static agent catalog ────────────────────────────────────────────────────

const AGENT_CATALOG = [
  { slug: 'compras',    icon: '🛒', name: 'Compras',    color: '#818cf8' },
  { slug: 'financeiro', icon: '📊', name: 'Financeiro', color: '#34d399' },
  { slug: 'agenda',     icon: '📅', name: 'Agenda',     color: '#fb923c' },
  { slug: 'documentos', icon: '✍️', name: 'Documentos', color: '#f472b6' },
  { slug: 'estrategia', icon: '🎯', name: 'Estratégia', color: '#fbbf24' },
  { slug: 'clientes',   icon: '👥', name: 'Clientes',   color: '#2dd4bf' },
]

const KIND_COLOR: Record<string, string> = {
  agent_session: '#818cf8',
  ingestion:     '#34d399',
  rfq:           '#fbbf24',
  upload:        '#f472b6',
}

const SEVERITY_BADGE: Record<string, { label: string; st: string }> = {
  error:   { label: 'Urgente',   st: 'lwrn' },
  warning: { label: 'Atenção',   st: 'lwrn' },
  info:    { label: 'Info',      st: 'lok'  },
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatTs(iso: string) {
  const d = new Date(iso)
  return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function agentStatus(count: number): string {
  if (count === 0) return 'Nada urgente'
  return count === 1 ? '1 pendente' : `${count} pendentes`
}

function pendingBySlug(approvals: ApprovalRequest[]): Record<string, number> {
  return approvals.reduce<Record<string, number>>((acc, a) => {
    acc[a.agent_slug] = (acc[a.agent_slug] ?? 0) + 1
    return acc
  }, {})
}

function urgentItems(approvals: ApprovalRequest[]): ApprovalRequest[] {
  const twoHoursAgo = Date.now() - 2 * 60 * 60 * 1000
  return approvals.filter(
    a => a.priority === 'urgent' && new Date(a.created_at).getTime() < twoHoursAgo
  )
}

function ActivityRow({ e }: { e: RecentActivityItem }) {
  const badge = SEVERITY_BADGE[e.severity] ?? { label: e.severity, st: '' }
  const color = KIND_COLOR[e.kind] ?? '#94a3b8'
  return (
    <div style={{ display: 'flex', gap: 10, padding: '10px 13px', borderBottom: '1px solid var(--gb)', cursor: 'pointer', transition: 'background .1s' }}
      onMouseEnter={el => (el.currentTarget.style.background = 'rgba(255,255,255,.025)')}
      onMouseLeave={el => (el.currentTarget.style.background = '')}
    >
      <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)', minWidth: 104, paddingTop: 2, flexShrink: 0 }}>{formatTs(e.occurredAt)}</span>
      <div style={{ width: 6, height: 6, borderRadius: '50%', background: color, marginTop: 5, flexShrink: 0 }} />
      <div style={{ flex: 1, fontSize: 12.5, color: 'var(--mu2)' }}>{e.title}{e.subtitle ? ` — ${e.subtitle}` : ''}</div>
      {badge.st
        ? <span className={`log-st ${badge.st}`} style={{ flexShrink: 0 }}>{badge.label}</span>
        : <span style={{ fontSize: 9.5, fontWeight: 600, padding: '1.5px 5px', borderRadius: 3, background: 'var(--adim)', color: 'var(--ac)', flexShrink: 0 }}>{badge.label}</span>
      }
    </div>
  )
}

// ── Screen ───────────────────────────────────────────────────────────────────

export default function AtividadeScreen() {
  const go = useAppStore(s => s.go)

  const { data: activity, isLoading: loadingActivity } = useRecentActivity(20)
  const { data: dayStats } = useDayStats()
  const { data: pendingApprovals } = usePendingApprovals()
  const { data: agentRunsData } = useAgentRunsToday()
  const { data: npsData } = useNpsScore()
  const { data: pendenciasData } = usePendencias()

  const events = activity ?? []
  const pending = pendingApprovals ?? []
  const countBySlug = pendingBySlug(pending)
  const urgents = urgentItems(pending)
  const pendencias = pendenciasData ?? []

  const pendingCount = pending.length
  const approvedToday = dayStats?.approvedToday ?? 0
  const agentActionsToday = agentRunsData?.total ?? dayStats?.agentActionsToday ?? 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="rh">
        <div className="rav">🔔</div>
        <div><div className="rn">Atividade</div><div className="rd">Log em tempo real de todos os agentes</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
        </div>
      </div>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 260px', gridTemplateRows: '1fr 106px', gap: 9, padding: 11, overflow: 'hidden' }}>

        {/* MAIN FEED */}
        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph">
            <span className="ph-ico">⚡</span>
            <span className="ph-ttl">Feed de atividades</span>
            <span className="ph-cnt">{loadingActivity ? 'Carregando…' : `${events.length} eventos`}</span>
          </div>
          <div className="pb">
            {loadingActivity ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>
            ) : events.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--mu)', fontSize: 12 }}>Nenhuma atividade registrada</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {events.map((e, i) => <ActivityRow key={i} e={e} />)}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="rcol">
          <RColResizeHandle />
          <div className="panel">
            <div className="ph"><span className="ph-ico">🤖</span><span className="ph-ttl">Agentes ativos</span></div>
            <div className="pb">
              <div style={{ padding: '7px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {AGENT_CATALOG.map((a, i) => {
                  const count = countBySlug[a.slug] ?? 0
                  return (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: '1px solid var(--gb)', cursor: 'pointer' }}
                      onClick={() => go(a.slug as any, a.name)}
                    >
                      <span style={{ fontSize: 14 }}>{a.icon}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 12, fontWeight: 500 }}>{a.name}</div>
                        <div style={{ fontSize: 10.5, color: 'var(--mu)' }}>{agentStatus(count)}</div>
                      </div>
                      {count > 0 && (
                        <span style={{ background: 'var(--urg)', color: '#fff', fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 8 }}>{count}</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="ph"><span className="ph-ico">📊</span><span className="ph-ttl">Resumo do dia</span></div>
            <div className="pb">
              <div style={{ padding: '7px 12px', display: 'flex', flexDirection: 'column', gap: 7, fontSize: 11.5 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Decisões pendentes</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--att)' }}>{pendingCount}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Aprovadas hoje</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>{approvedToday}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Ações do agente</span><span style={{ fontFamily: 'var(--mono)' }}>{agentActionsToday}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>NPS</span><span style={{ fontFamily: 'var(--mono)', color: npsData && npsData.score >= 50 ? 'var(--ok)' : npsData && npsData.score >= 0 ? 'var(--att)' : 'var(--urg)' }}>{npsData ? npsData.score : '—'}</span></div>
              </div>
            </div>
          </div>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip" style={{ gridColumn: '1/-1', gridRow: 2 }}>
          {urgents.length > 0 ? (
            <div className="ich"><span className="ich-em">🔴</span><div className="ich-body"><span className="ich-tag" style={{ color: 'var(--urg)' }}>Urgente</span><div className="ich-txt">{urgents.length} decisão{urgents.length > 1 ? 'ões' : ''} urgente{urgents.length > 1 ? 's' : ''} aguardando há mais de 2 horas</div></div></div>
          ) : (
            <div className="ich"><span className="ich-em">🟢</span><div className="ich-body"><span className="ich-tag" style={{ color: 'var(--ok)' }}>OK</span><div className="ich-txt">Nenhuma decisão urgente no momento</div></div></div>
          )}
          {pendencias.filter(p => p.severity === 'error' || p.severity === 'warning').slice(0, 2).map((p, i) => (
            <div key={i} className="ich">
              <span className="ich-em">{p.severity === 'error' ? '⚠️' : '💡'}</span>
              <div className="ich-body">
                <span className="ich-tag" style={{ color: p.severity === 'error' ? 'var(--urg)' : 'var(--att)' }}>Sistema</span>
                <div className="ich-txt">{p.title}</div>
              </div>
            </div>
          ))}
          {pendingCount > 0 && (
            <div className="ich"><span className="ich-em">🟡</span><div className="ich-body"><span className="ich-tag" style={{ color: 'var(--att)' }}>Atenção</span><div className="ich-txt">{pendingCount} decisão{pendingCount > 1 ? 'ões' : ''} pendente{pendingCount > 1 ? 's' : ''} aguardando revisão</div></div></div>
          )}
          <div className="ich"><span className="ich-em">🟢</span><div className="ich-body"><span className="ich-tag" style={{ color: 'var(--ok)' }}>Concluído</span><div className="ich-txt">{approvedToday} decisão{approvedToday !== 1 ? 'ões' : ''} aprovada{approvedToday !== 1 ? 's' : ''} hoje</div></div></div>
          <div className="nums-chip">
            <div className="nums-head">🔔 Hoje</div>
            <div className="nums-row">
              <div className="nkpi"><span className="nv" style={{ fontSize: 18, color: 'var(--att)' }}>{pendingCount}</span><span className="nl">pendentes</span></div>
              <div className="nkpi"><span className="nv" style={{ fontSize: 18, color: 'var(--ok)' }}>{approvedToday}</span><span className="nl">aprovadas</span></div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
