import { useState } from 'react'
import { useAppStore } from '../../store/appStore'

type AdminTab = 'integracoes' | 'usuarios' | 'auditoria' | 'lgpd' | 'contexto'

interface Integration {
  id: string
  icon: string
  name: string
  desc: string
  connected: boolean
}

const LANES: { label: string; integrations: Integration[] }[] = [
  {
    label: 'Bancos & Financeiro',
    integrations: [
      { id: 'ic-itau', icon: '🏦', name: 'Itaú Empresas', desc: 'Open Banking', connected: true },
      { id: 'ic-bradesco', icon: '🏦', name: 'Bradesco PJ', desc: 'Open Banking', connected: false },
      { id: 'ic-nubank', icon: '💜', name: 'Nubank PJ', desc: 'API nativa', connected: false },
    ],
  },
  {
    label: 'ERPs & Gestão',
    integrations: [
      { id: 'ic-bling', icon: '📦', name: 'Bling', desc: 'ERP completo', connected: true },
      { id: 'ic-omie', icon: '📊', name: 'Omie', desc: 'ERP completo', connected: false },
      { id: 'ic-tiny', icon: '📋', name: 'Tiny', desc: 'ERP completo', connected: false },
    ],
  },
  {
    label: 'Agenda & Comunicação',
    integrations: [
      { id: 'ic-gcal', icon: '📅', name: 'Google Calendar', desc: 'Agenda', connected: true },
      { id: 'ic-outlook', icon: '📧', name: 'Outlook', desc: 'Agenda + e-mail', connected: false },
      { id: 'ic-whatsapp', icon: '💬', name: 'WhatsApp Business', desc: 'Mensagens', connected: false },
    ],
  },
  {
    label: 'Dados & Analytics',
    integrations: [
      { id: 'ic-sheets', icon: '📊', name: 'Google Sheets', desc: 'Planilhas', connected: true },
      { id: 'ic-bigquery', icon: '🗄️', name: 'BigQuery', desc: 'Data warehouse', connected: false },
      { id: 'ic-postgres', icon: '🐘', name: 'PostgreSQL', desc: 'Banco relacional', connected: false },
    ],
  },
]

const LOGS = [
  { ts: '06/05 10:32', agColor: '#818cf8', text: 'Aprovar compra — Toner HP 107A, R$ 420, Fornecedor Silva', user: 'Carlos Lima', status: 'Aprovado', st: 'lok' },
  { ts: '06/05 09:15', agColor: '#34d399', text: 'Agendar pagamento — Boleto Claro, R$ 847,50', user: 'Carlos Lima', status: 'Aprovado', st: 'lok' },
  { ts: '05/05 16:10', agColor: '#fbbf24', text: 'Análise de margem Q1 — Produto Y, +17pp vs. setor', user: 'Carlos Lima', status: 'Aprovado', st: 'lok' },
  { ts: '05/05 14:38', agColor: '#f472b6', text: 'Gerar proposta — Construtora Alvo, R$ 28K/mês', user: 'Carlos Lima', status: 'Gerado', st: 'lok' },
  { ts: '05/05 11:20', agColor: '#34d399', text: 'DRE mensal automático — Abr 2026', user: 'Sistema', status: 'Automático', st: '' },
  { ts: '04/05 16:45', agColor: '#fbbf24', text: 'Alerta: 2 fornecedores com prazo crescente', user: 'Sistema', status: 'Alerta', st: 'lwrn' },
  { ts: '04/05 09:30', agColor: '#34d399', text: 'Aprovar pagamento — Gamma Suprimentos, R$ 234', user: 'Carlos Lima', status: 'Aprovado', st: 'lok' },
  { ts: '03/05 15:00', agColor: '#2dd4bf', text: 'Follow-up enviado — Grupo Máquina Central', user: 'Sistema', status: 'Enviado', st: 'lok' },
]

const LOG_DETAIL: Record<string, { agent: string; action: string; value: string; ip: string; justification: string }> = {
  '06/05 10:32': { agent: 'Compras', action: 'Aprovação de compra', value: 'R$ 420,00', ip: '192.168.1.10', justification: 'Estoque crítico (1 dia restante). Fornecedor Silva com melhor histórico de entrega (0 atrasos em 6 meses). Aprovação manual realizada por Carlos Lima.' },
  '06/05 09:15': { agent: 'Financeiro', action: 'Agendamento de pagamento', value: 'R$ 847,50', ip: '192.168.1.10', justification: 'Boleto com vencimento no dia seguinte. Saldo suficiente na conta Itaú (R$ 12.340). Aprovação realizada pelo proprietário.' },
}

export default function AdminScreen() {
  const go = useAppStore(s => s.go)
  const [tab, setTab] = useState<AdminTab>('integracoes')
  const [integrations, setIntegrations] = useState<Record<string, boolean>>(
    Object.fromEntries(LANES.flatMap(l => l.integrations.map(i => [i.id, i.connected])))
  )
  const [expandedLog, setExpandedLog] = useState<string | null>(null)
  const [expandedUser, setExpandedUser] = useState<string | null>(null)
  const [modalId, setModalId] = useState<string | null>(null)
  const [modalMode, setModalMode] = useState<'connect' | 'config'>('connect')
  const [logSearch, setLogSearch] = useState('')

  const openConnect = (id: string) => { setModalId(id); setModalMode('connect') }
  const openConfig = (id: string) => { setModalId(id); setModalMode('config') }
  const doConnect = () => { if (modalId) { setIntegrations(p => ({ ...p, [modalId]: true })); setModalId(null) } }
  const doDisconnect = () => { if (modalId) { setIntegrations(p => ({ ...p, [modalId]: false })); setModalId(null) } }

  const filteredLogs = LOGS.filter(l => logSearch === '' || l.text.toLowerCase().includes(logSearch.toLowerCase()) || l.user.toLowerCase().includes(logSearch.toLowerCase()))

  const TABS: { id: AdminTab; label: string }[] = [
    { id: 'integracoes', label: '🔗 Integrações' },
    { id: 'usuarios', label: '👥 Usuários' },
    { id: 'auditoria', label: '📋 Auditoria' },
    { id: 'lgpd', label: '🔒 LGPD' },
    { id: 'contexto', label: '🗺️ Contexto' },
  ]

  const USERS = [
    { id: 'u1', initials: 'CL', name: 'Carlos Lima', role: 'Proprietário', color: 'var(--ac)', agents: { compras: true, financeiro: true, agenda: true, documentos: true, estrategia: true, clientes: true }, actions: { aprovar: true, exportar: true, usuarios: true, config: true } },
    { id: 'u2', initials: 'AC', name: 'Ana Costa', role: 'Gerente', color: '#34d399', agents: { compras: true, financeiro: true, agenda: true, documentos: true, estrategia: false, clientes: true }, actions: { aprovar: true, exportar: true, usuarios: false, config: false } },
    { id: 'u3', initials: 'PS', name: 'Pedro Silva', role: 'Operacional', color: '#818cf8', agents: { compras: true, financeiro: false, agenda: true, documentos: true, estrategia: false, clientes: false }, actions: { aprovar: false, exportar: false, usuarios: false, config: false } },
  ]

  const DOMAIN_DATA = [
    { icon: '🏢', name: 'Identidade', pct: 80, color: 'var(--ok)' },
    { icon: '⚙️', name: 'Operações', pct: 62, color: 'var(--att)' },
    { icon: '👥', name: 'Pessoas', pct: 50, color: 'var(--att)' },
    { icon: '🌐', name: 'Externo', pct: 30, color: 'var(--urg)' },
    { icon: '🎯', name: 'Estratégia', pct: 80, color: 'var(--ok)' },
  ]

  const AGENT_READINESS = [
    { icon: '📊', name: 'Financeiro', status: 'Pronto', st: 'sts-ok' },
    { icon: '🎯', name: 'Estratégia', status: 'Pronto', st: 'sts-ok' },
    { icon: '👥', name: 'Clientes', status: 'Pronto', st: 'sts-ok' },
    { icon: '🛒', name: 'Compras', status: 'Parcial', st: 'sts-par' },
    { icon: '✍️', name: 'Documentos', status: 'Parcial', st: 'sts-par' },
    { icon: '📅', name: 'Agenda', status: 'Parcial', st: 'sts-par' },
  ]

  const modalIntg = LANES.flatMap(l => l.integrations).find(i => i.id === modalId)

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
              <span className="int-lane-ct">{lane.integrations.filter(i => integrations[i.id]).length} de {lane.integrations.length} conectadas</span>
            </div>
            <div className="int-carousel">
              {lane.integrations.map(intg => {
                const conn = integrations[intg.id]
                return (
                  <div key={intg.id} className={`int-card${conn ? ' conn' : ''}`}>
                    <div className="int-card-ico">
                      {intg.icon}
                      <div className="ic-dot">✓</div>
                    </div>
                    <div className="int-card-nm">{intg.name}</div>
                    <div className="int-card-dc">{intg.desc}</div>
                    <div className="int-card-ft">
                      {conn
                        ? <><span className="conn-pill">Ativo</span><button className="btn bg" style={{ fontSize: 10, padding: '3px 7px', marginLeft: 'auto' }} onClick={() => openConfig(intg.id)}>Config</button></>
                        : <button className="btn bp" style={{ fontSize: 10.5, padding: '4px 10px' }} onClick={() => openConnect(intg.id)}>Conectar</button>
                      }
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
        {USERS.map(u => (
          <div key={u.id}>
            <div className={`usr-row${expandedUser === u.id ? ' open' : ''}`} onClick={() => setExpandedUser(expandedUser === u.id ? null : u.id)}>
              <div className="usr-av" style={{ background: `${u.color}22`, color: u.color }}>{u.initials}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12.5, fontWeight: 600 }}>{u.name}</div>
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>{u.role}</div>
              </div>
              <span className="usr-perm">{expandedUser === u.id ? '▼' : '▶'}</span>
            </div>
            <div className={`perm-box${expandedUser === u.id ? ' open' : ''}`} onClick={e => e.stopPropagation()}>
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 7 }}>Acesso por agente</div>
                {Object.entries(u.agents).map(([agent, enabled]) => (
                  <div key={agent} className="perm-row">
                    <span className="perm-nm" style={{ textTransform: 'capitalize' }}>{agent}</span>
                    <div className={`ptog${enabled ? ' on' : ''}`} />
                  </div>
                ))}
              </div>
              <div>
                <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 7, marginTop: 8 }}>Permissões de ação</div>
                {Object.entries(u.actions).map(([action, enabled]) => (
                  <div key={action} className="perm-row">
                    <span className="perm-nm" style={{ textTransform: 'capitalize' }}>{action === 'usuarios' ? 'Gerenciar usuários' : action === 'config' ? 'Configurar agentes' : action === 'aprovar' ? 'Aprovar decisões' : 'Exportar dados'}</span>
                    <div className={`ptog${enabled ? ' on' : ''}`} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* AUDITORIA */}
      <div className={`ad-tc${tab === 'auditoria' ? ' on' : ''}`}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8, marginBottom: 14 }}>
          <div className="kpi-cell"><div className="kpi-lbl">Total de ações</div><div className="kpi-val">1.247</div><div className="kpi-d" style={{ color: 'var(--mu)' }}>este mês</div></div>
          <div className="kpi-cell"><div className="kpi-lbl">Taxa de aprovação</div><div className="kpi-val">87%</div><div className="kpi-d up">↑ 3pp</div></div>
          <div className="kpi-cell"><div className="kpi-lbl">Economia gerada</div><div className="kpi-val">8,4K</div><div className="kpi-d up">↑ 12%</div></div>
          <div className="kpi-cell"><div className="kpi-lbl">Anomalias</div><div className="kpi-val" style={{ color: 'var(--att)' }}>3</div><div className="kpi-d" style={{ color: 'var(--att)' }}>→ investigar</div></div>
        </div>
        <div className="aud-search">
          <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
          <input placeholder="Buscar nos logs…" value={logSearch} onChange={e => setLogSearch(e.target.value)} />
        </div>
        <div>
          {filteredLogs.map((l, i) => {
            const isOpen = expandedLog === l.ts
            const detail = LOG_DETAIL[l.ts]
            return (
              <div key={i} className="log-wrap">
                <div className={`log-row${isOpen ? ' expanded' : ''}`} onClick={() => setExpandedLog(isOpen ? null : l.ts)} style={{ border: 'none', borderBottom: isOpen ? '1px solid var(--gb)' : 'none' }}>
                  <span className="log-ts">{l.ts}</span>
                  <div className="log-ag" style={{ background: l.agColor }} />
                  <div className="log-act">{l.text}</div>
                  <span className="log-usr">{l.user}</span>
                  {l.st ? <span className={`log-st ${l.st}`}>{l.status}</span> : <span style={{ fontSize: 9.5, fontWeight: 600, padding: '1.5px 5px', borderRadius: 3, background: 'var(--adim)', color: 'var(--ac)' }}>{l.status}</span>}
                  <span style={{ color: 'var(--mu)', fontSize: 10, marginLeft: 6 }}>{isOpen ? '▼' : '▶'}</span>
                </div>
                {isOpen && detail && (
                  <div className="log-det open">
                    <div className="ld-grid">
                      <div><div className="ld-lbl">Agente</div><div className="ld-val">{detail.agent}</div></div>
                      <div><div className="ld-lbl">Usuário</div><div className="ld-val">{l.user}</div></div>
                      <div><div className="ld-lbl">Ação</div><div className="ld-val">{detail.action}</div></div>
                      <div><div className="ld-lbl">Valor</div><div className="ld-val" style={{ fontFamily: 'var(--mono)' }}>{detail.value}</div></div>
                      <div><div className="ld-lbl">Sessão</div><div className="ld-val" style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{detail.ip}</div></div>
                      <div><div className="ld-lbl">Status</div><div className="ld-val">{l.status}</div></div>
                    </div>
                    <div className="ld-lbl" style={{ marginBottom: 4 }}>Justificativa</div>
                    <div className="ld-just">{detail.justification}</div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* LGPD */}
      <div className={`ad-tc${tab === 'lgpd' ? ' on' : ''}`}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 640 }}>
          <div style={{ background: 'var(--odim)', border: '1px solid rgba(16,185,129,.3)', borderRadius: 'var(--r)', padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'center' }}>
            <span style={{ fontSize: 20 }}>✅</span>
            <div><div style={{ fontWeight: 600, fontSize: 13 }}>LGPD em conformidade</div><div style={{ fontSize: 11.5, color: 'var(--mu)', marginTop: 2 }}>Última verificação: 06/05/2026 às 08:00</div></div>
          </div>
          <div className="lgpd-sec">
            <div className="lgpd-ttl">Exportar dados</div>
            <div className="lgpd-desc">Baixe uma cópia de todos os dados processados pelo Blu para auditoria ou portabilidade.</div>
            <div className="lgpd-act">
              <button className="btn bs" style={{ fontSize: 11.5 }}>📁 Exportar tudo (JSON)</button>
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
              <button className="btn brd" style={{ fontSize: 11.5 }}>⚠️ Excluir conta</button>
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
      <div className={`ad-tc${tab === 'contexto' ? ' on' : ''}`} style={{ padding: 0 }}>
        <div className="ctx-grid" style={{ height: '100%' }}>
          <div className="ctx-map-wrap">
            <div className="ctx-svg-cont">
              <svg width="100%" height="100%" viewBox="0 0 540 380" style={{ display: 'block' }}>
                <defs>
                  <radialGradient id="cg" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="rgba(140,95,219,0.2)" />
                    <stop offset="100%" stopColor="rgba(140,95,219,0)" />
                  </radialGradient>
                </defs>
                <circle cx="270" cy="190" r="120" fill="url(#cg)" />
                {/* Connections */}
                {[[270,190,270,60],[270,190,400,130],[270,190,370,300],[270,190,140,300],[270,190,130,130]].map(([x1,y1,x2,y2],i) => (
                  <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(255,255,255,0.08)" strokeWidth="1.5" />
                ))}
                {/* Center */}
                <circle cx="270" cy="190" r="32" fill="rgba(140,95,219,0.2)" stroke="rgba(140,95,219,0.5)" strokeWidth="1.5" />
                <text x="270" y="185" textAnchor="middle" fill="white" fontSize="13" fontWeight="700">58%</text>
                <text x="270" y="200" textAnchor="middle" fill="rgba(223,227,238,0.6)" fontSize="9">NEGÓCIO</text>
                {/* Domain nodes */}
                {[
                  { x: 270, y: 60, icon: '🎯', name: 'Estratégia', pct: 80, color: '#10b981' },
                  { x: 400, y: 130, icon: '🏢', name: 'Identidade', pct: 80, color: '#10b981' },
                  { x: 370, y: 300, icon: '⚙️', name: 'Operações', pct: 62, color: '#f59e0b' },
                  { x: 140, y: 300, icon: '👥', name: 'Pessoas', pct: 50, color: '#f59e0b' },
                  { x: 130, y: 130, icon: '🌐', name: 'Externo', pct: 30, color: '#ef4444' },
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
              <div className="ctx-score" style={{ color: 'var(--att)' }}>58%</div>
              <div className="ctx-score-lbl">Cobertura de contexto</div>
            </div>
            <div className="ctx-cov-sec">
              <div className="ctx-cov-ttl">Por domínio</div>
              {DOMAIN_DATA.map((d, i) => (
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
              {AGENT_READINESS.map((a, i) => (
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

      {/* MODAL */}
      {modalId && modalIntg && (
        <div className="intg-modal open" onClick={() => setModalId(null)}>
          <div className="intg-box" onClick={e => e.stopPropagation()}>
            {modalMode === 'connect' ? (
              <>
                <h3>{modalIntg.icon} Conectar {modalIntg.name}</h3>
                <div className="msub">Insira as credenciais para autorizar o acesso.</div>
                <div className="intg-field"><label>Client ID / App Key</label><input placeholder="Insira o Client ID" /></div>
                <div className="intg-field"><label>Client Secret / Token</label><input type="password" placeholder="Insira o segredo" /></div>
                <div className="modal-acts">
                  <button className="btn bg" onClick={() => setModalId(null)}>Cancelar</button>
                  <button className="btn bp" onClick={doConnect}>Conectar</button>
                </div>
              </>
            ) : (
              <>
                <h3>{modalIntg.icon} {modalIntg.name} — Configuração</h3>
                <div className="msub">Conectado e sincronizando normalmente.</div>
                <div className="intg-field"><label>Client ID</label><input value="cli_••••••••••••••••" readOnly style={{ opacity: .7 }} /></div>
                <div className="intg-field"><label>Última sincronização</label><input value="06/05/2026 às 10:32" readOnly style={{ opacity: .7 }} /></div>
                <hr className="modal-sep" />
                <div className="modal-acts">
                  <button className="btn brd" onClick={doDisconnect}>Desconectar</button>
                  <button className="btn bp" onClick={() => setModalId(null)}>Sincronizar agora</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
