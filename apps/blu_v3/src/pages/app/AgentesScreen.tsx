import { useState } from 'react'
import { useAgents, useAgentReadiness } from '../../hooks/useAgents'
import { useAppStore } from '../../store/appStore'
import { supabase } from '@blu/auth'
import { useAuth } from '@blu/auth'
import { useQueryClient } from '@tanstack/react-query'
import type { ClientEnabledAgent, AgentReadiness } from '../../api/agents'

// ── Catalog ───────────────────────────────────────────────────────────────────

const AGENT_META: Record<string, { icon: string; color: string; description: string }> = {
  financeiro: {
    icon: '📊',
    color: '#34d399',
    description: 'Monitora fluxo de caixa, conciliações bancárias e alertas financeiros. Conectado ao seu ERP e contas bancárias.',
  },
  compras: {
    icon: '🛒',
    color: '#818cf8',
    description: 'Gerencia pedidos de compra, aprovações de fornecedores e controle de estoque mínimo.',
  },
  clientes: {
    icon: '👥',
    color: '#2dd4bf',
    description: 'Analisa base de clientes, churn risk, oportunidades de upsell e NPS.',
  },
  estrategia: {
    icon: '🎯',
    color: '#fbbf24',
    description: 'Consolida KPIs estratégicos, tendências de mercado e análises comparativas (YoY, MoM).',
  },
  documentos: {
    icon: '✍️',
    color: '#f472b6',
    description: 'Cria, revisa e organiza documentos: propostas, contratos, relatórios e comunicações.',
  },
  agenda: {
    icon: '📅',
    color: '#fb923c',
    description: 'Gerencia compromissos, prepara briefings de reunião e acompanha follow-ups.',
  },
}

function getMeta(slug: string) {
  return AGENT_META[slug] ?? { icon: '🤖', color: '#94a3b8', description: 'Agente configurável para sua operação.' }
}

// ── Readiness badge ───────────────────────────────────────────────────────────

function readinessBadge(
  slug: string,
  readinessMap: Record<string, AgentReadiness>,
): { label: string; cls: string } {
  const r = readinessMap[slug]
  if (!r) return { label: 'Inativo', cls: 'sts-err' }
  if (r.is_ready) return { label: 'Pronto', cls: 'sts-ok' }
  if (r.readiness_score > 0) return { label: 'Parcial', cls: 'sts-par' }
  return { label: 'Inativo', cls: 'sts-blk' }
}

// ── Config drawer ─────────────────────────────────────────────────────────────

function AgentDrawer({
  agent,
  readiness,
  onClose,
}: {
  agent: ClientEnabledAgent
  readiness: AgentReadiness | undefined
  onClose: () => void
}) {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const go = useAppStore(s => s.go)
  const meta = getMeta(agent.agent_slug)
  const [toggling, setToggling] = useState(false)
  const isEnabled = agent.current_status !== 'inactive'

  const toggleEnabled = async () => {
    if (!clientId || toggling) return
    setToggling(true)
    const nextStatus = isEnabled ? 'inactive' : 'active'
    await supabase
      .from('client_enabled_agents')
      .update({ current_status: nextStatus })
      .eq('client_id', clientId)
      .eq('agent_slug', agent.agent_slug)
    qc.invalidateQueries({ queryKey: ['agents', clientId] })
    setToggling(false)
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        display: 'flex',
        alignItems: 'stretch',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 320,
          background: 'var(--bg2)',
          borderLeft: '1px solid var(--gb)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'slideIn .18s ease',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--gb)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 22 }}>{meta.icon}</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13.5, fontWeight: 700 }}>
              {agent.agent_catalog?.name ?? agent.agent_slug}
            </div>
            <div style={{ fontSize: 10, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '.06em' }}>
              {agent.agent_slug}
            </div>
          </div>
          <button
            className="btn bg"
            style={{ fontSize: 10, padding: '3px 8px' }}
            onClick={onClose}
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Description */}
          <div style={{ fontSize: 12, color: 'var(--mu2)', lineHeight: 1.6 }}>{meta.description}</div>

          {/* Enabled toggle */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '10px 13px' }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600 }}>Agente ativo</div>
              <div style={{ fontSize: 10.5, color: 'var(--mu)' }}>Habilita ações e sugestões deste agente</div>
            </div>
            <div
              className={`ptog${isEnabled ? ' on' : ''}`}
              style={{ opacity: toggling ? 0.5 : 1 }}
              onClick={toggleEnabled}
            />
          </div>

          {/* Readiness info */}
          {readiness && !readiness.is_ready && readiness.missing_requirements.length > 0 && (
            <div style={{ background: 'var(--udim)', border: '1px solid rgba(248,113,113,.2)', borderRadius: 'var(--r)', padding: '10px 12px' }}>
              <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--urg)', marginBottom: 6 }}>Requisitos pendentes</div>
              {readiness.missing_requirements.map(r => (
                <div key={r} style={{ fontSize: 11, color: 'var(--mu2)', display: 'flex', gap: 5, marginBottom: 3 }}>
                  <span style={{ color: 'var(--urg)' }}>!</span> {r}
                </div>
              ))}
            </div>
          )}

          {/* Pending approvals */}
          {agent.pending_count > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--adim)', border: '1px solid rgba(251,146,60,.2)', borderRadius: 'var(--r)', padding: '10px 12px' }}>
              <div>
                <div style={{ fontSize: 11.5, fontWeight: 600 }}>{agent.pending_count} aprovação{agent.pending_count > 1 ? 'ões' : ''} pendente{agent.pending_count > 1 ? 's' : ''}</div>
                <div style={{ fontSize: 10.5, color: 'var(--mu)' }}>Aguardando sua decisão</div>
              </div>
            </div>
          )}

          {/* Last activity */}
          {agent.last_activity_at && (
            <div style={{ fontSize: 11, color: 'var(--mu)' }}>
              Última atividade: {new Date(agent.last_activity_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '10px 16px', borderTop: '1px solid var(--gb)' }}>
          <button
            className="btn bp"
            style={{ width: '100%', justifyContent: 'center', fontSize: 12 }}
            onClick={() => {
              go('home', 'Início')
              onClose()
            }}
          >
            Abrir chat com {agent.agent_catalog?.name ?? agent.agent_slug}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Agent card ────────────────────────────────────────────────────────────────

function AgentCard({
  agent,
  readinessMap,
  onConfigure,
}: {
  agent: ClientEnabledAgent
  readinessMap: Record<string, AgentReadiness>
  onConfigure: (agent: ClientEnabledAgent) => void
}) {
  const meta = getMeta(agent.agent_slug)
  const badge = readinessBadge(agent.agent_slug, readinessMap)

  return (
    <div
      style={{
        background: 'var(--glass)',
        border: '1px solid var(--gb)',
        borderRadius: 'var(--rl)',
        padding: '14px 15px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        backdropFilter: 'blur(10px)',
        transition: 'border-color .14s',
        cursor: 'default',
      }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = `${meta.color}44`)}
      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--gb)')}
    >
      {/* Icon + name row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: `${meta.color}1a`, border: `1px solid ${meta.color}33`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>
          {meta.icon}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {agent.agent_catalog?.name ?? agent.agent_slug}
          </div>
          <div style={{ fontSize: 10, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '.05em' }}>
            {agent.agent_slug}
          </div>
        </div>
        <span className={`ctx-agent-status ${badge.cls}`} style={{ fontSize: 9 }}>{badge.label}</span>
      </div>

      {/* Pending count */}
      {agent.pending_count > 0 && (
        <div style={{ fontSize: 11, color: 'var(--att)', display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--att)', flexShrink: 0 }} />
          {agent.pending_count} pendente{agent.pending_count > 1 ? 's' : ''}
        </div>
      )}

      {/* Configure button */}
      <button
        className="btn bg"
        style={{ fontSize: 10.5, justifyContent: 'center', cursor: 'pointer' }}
        onClick={() => onConfigure(agent)}
      >
        Configurar
      </button>
    </div>
  )
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function AgentesScreen() {
  const { data: agents = [], isLoading: agentsLoading } = useAgents()
  const { data: readinessList = [] } = useAgentReadiness()
  const [drawerAgent, setDrawerAgent] = useState<ClientEnabledAgent | null>(null)

  const readinessMap = Object.fromEntries(
    readinessList.map(r => [r.agent_slug, r])
  ) as Record<string, AgentReadiness>

  const activeCount = agents.filter(a => a.current_status !== 'inactive').length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div className="rh">
        <div className="rav">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/>
            <path d="M8 14a6 6 0 0 0-6 6h20a6 6 0 0 0-6-6"/>
          </svg>
        </div>
        <div>
          <div className="rn" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            Agentes
            {activeCount > 0 && (
              <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 10, background: 'var(--odim)', color: 'var(--ok)' }}>
                {activeCount} ativo{activeCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <div className="rd">Gerencie e configure seus agentes de IA</div>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px' }}>
        {agentsLoading ? (
          <div style={{ color: 'var(--mu)', fontSize: 12.5 }}>Carregando agentes…</div>
        ) : agents.length === 0 ? (
          <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--mu)', fontSize: 12.5 }}>
            Nenhum agente configurado ainda. Entre em contato com o suporte para ativá-los.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            {agents.map(agent => (
              <AgentCard
                key={agent.agent_slug}
                agent={agent}
                readinessMap={readinessMap}
                onConfigure={setDrawerAgent}
              />
            ))}
          </div>
        )}

        {/* Readiness summary */}
        {readinessList.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 8 }}>
              Resumo de prontidão
            </div>
            <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', overflow: 'hidden', backdropFilter: 'blur(10px)' }}>
              {readinessList.map((r, i) => {
                const meta = getMeta(r.agent_slug)
                const badge = readinessBadge(r.agent_slug, readinessMap)
                return (
                  <div
                    key={r.agent_slug}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '8px 12px',
                      borderBottom: i < readinessList.length - 1 ? '1px solid var(--gb)' : 'none',
                    }}
                  >
                    <span style={{ fontSize: 14, width: 20, textAlign: 'center' }}>{meta.icon}</span>
                    <span style={{ flex: 1, fontSize: 11.5, textTransform: 'capitalize' }}>{r.agent_slug}</span>
                    <div style={{ width: 100, height: 3, background: 'rgba(255,255,255,.08)', borderRadius: 2, overflow: 'hidden', flexShrink: 0 }}>
                      <div style={{ width: `${r.readiness_score}%`, height: '100%', background: meta.color, borderRadius: 2 }} />
                    </div>
                    <span style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--mu)', width: 28, textAlign: 'right' }}>
                      {r.readiness_score}%
                    </span>
                    <span className={`ctx-agent-status ${badge.cls}`} style={{ fontSize: 9 }}>{badge.label}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Config drawer */}
      {drawerAgent && (
        <AgentDrawer
          agent={drawerAgent}
          readiness={readinessMap[drawerAgent.agent_slug]}
          onClose={() => setDrawerAgent(null)}
        />
      )}
    </div>
  )
}
