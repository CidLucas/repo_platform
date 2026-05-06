import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@blu/auth'

type Step = 'auth' | 'info' | 'data' | 'mapping' | 'launch'

const STEP_ORDER: Step[] = ['auth', 'info', 'data', 'mapping', 'launch']
const STEP_LABELS = ['Conta', 'Empresa', 'Dados', 'Mapeamento']

const SECTORS = ['🛍 Comércio', '⚙️ Serviços', '🏭 Indústria', '🌱 Agronegócio', '💊 Saúde', '📚 Educação']
const VERTICALS = ['Comércio', 'Serviços', 'Indústria', 'Saúde', 'Educação', 'Agronegócio', 'Financeiro', 'Outro']
const TEAM_SIZES = ['Só eu', '2–10 pessoas', '10–50 pessoas', '50+ pessoas']

const SYSTEMS = [
  { id: 'shopify', icon: '🛍', name: 'Shopify', sub: 'E-commerce' },
  { id: 'bling', icon: '📦', name: 'Bling', sub: 'ERP / NF-e' },
  { id: 'omie', icon: '⚙️', name: 'Omie', sub: 'ERP' },
  { id: 'bigquery', icon: '📊', name: 'BigQuery', sub: 'Data warehouse' },
  { id: 'postgresql', icon: '🐘', name: 'PostgreSQL', sub: 'Banco de dados' },
  { id: 'vtex', icon: '🔷', name: 'VTEX', sub: 'E-commerce' },
]

const AUTO_ROWS = [
  { col: 'nr_pedido', target: 'pedido_id', pct: 98 },
  { col: 'dt_emissao', target: 'data_emissao', pct: 97 },
  { col: 'cd_cliente', target: 'cliente_id', pct: 95 },
  { col: 'nm_cliente', target: 'cliente_nome', pct: 99 },
  { col: 'cnpj_cliente', target: 'cliente_cnpj', pct: 99 },
  { col: 'cd_produto', target: 'produto_id', pct: 91 },
  { col: 'ds_produto', target: 'produto_nome', pct: 94 },
  { col: 'qt_pedida', target: 'quantidade', pct: 97 },
  { col: 'vl_unitario', target: 'valor_unitario', pct: 96 },
  { col: 'vl_total', target: 'valor_total', pct: 99 },
  { col: 'cd_fornecedor', target: 'fornecedor_id', pct: 92 },
  { col: 'nm_fornecedor', target: 'fornecedor_nome', pct: 95 },
  { col: 'tp_pagamento', target: 'metodo_pagamento', pct: 89 },
  { col: 'chave_nfe', target: 'nf_chave', pct: 94 },
]

const WARN_ROWS = [
  { id: 'dtprev', col: 'dt_previsao', pct: 78, options: ['data_entrega', 'data_prevista', 'prazo_entrega'], default: 'data_entrega' },
  { id: 'refprod', col: 'ref_produto', pct: 72, options: ['sku', 'produto_cod_interno', 'referencia'], default: 'sku' },
  { id: 'descpct', col: 'desc_pct', pct: 81, options: ['desconto', 'desconto_pct'], default: 'desconto' },
  { id: 'sit', col: 'situacao', pct: 69, options: ['status_pedido', 'status_customizado'], default: 'status_pedido' },
]

const LAUNCH_LOG = [
  '▸ Configurando agente de Compras…',
  '▸ Configurando agente Financeiro…',
  '▸ Importando dados — 1.247 registros…',
  '▸ Detectando padrões iniciais…',
  '▸ Bureau pronto.',
]

function FlowTop({ step, onBack }: { step: Step; onBack?: () => void }) {
  const stepIdx = STEP_ORDER.indexOf(step)
  return (
    <div className="flow-top">
      <div className="flow-logo" onClick={onBack} style={{ cursor: onBack ? 'pointer' : 'default' }}>
        <div className="logo-mark">B</div>
        <span>blu</span>
      </div>
      <div className="progress-steps">
        {STEP_LABELS.map((label, i) => {
          const done = stepIdx > i
          const active = stepIdx === i
          return (
            <>
              {i > 0 && <div key={`sep-${i}`} className="ps-sep" />}
              <div key={label} className={`ps${done ? ' done' : active ? ' active' : ''}`}>
                <div className="ps-num">{done ? '✓' : i + 1}</div>
                {label}
              </div>
            </>
          )
        })}
      </div>
    </div>
  )
}

function StepAuth({ onNext, mode }: { onNext: () => void; mode: 'login' | 'signup' }) {
  const { signInWithGoogle, signInWithEmail, signUp } = useAuth()
  const [sector, setSector] = useState(SECTORS[0])
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  async function handleGoogle() {
    setError(null)
    const { error } = await signInWithGoogle()
    if (error) setError(error.message)
    // OAuth redirect handles the rest — page will reload on return
  }

  async function handleSubmit() {
    setError(null)
    setSubmitting(true)
    try {
      if (mode === 'login') {
        const { error } = await signInWithEmail(email, password)
        if (error) { setError(error.message); return }
        navigate('/app', { replace: true })
      } else {
        const { error } = await signUp(email, password, { sector })
        if (error) { setError(error.message); return }
        onNext()
      }
    } finally {
      setSubmitting(false)
    }
  }

  const isLogin = mode === 'login'

  return (
    <div className="flow-page on">
      <FlowTop step="auth" />
      <div className="flow-body">
        <div className="flow-card">
          <div className="fc-h">{isLogin ? 'Bem-vindo de volta' : 'Boas-vindas ao blu'}</div>
          <div className="fc-sub">
            {isLogin
              ? 'Entre na sua conta para acessar o bureau.'
              : 'O seu escritório virtual com IA. Vamos configurar tudo em 3 minutos.'}
          </div>

          {!isLogin && (
            <>
              <div style={{ marginBottom: 12, fontSize: 12.5, color: 'var(--muted2)' }}>Em qual setor você atua?</div>
              <div className="persona-row">
                {SECTORS.map(s => (
                  <div key={s} className={`persona-pill${sector === s ? ' on' : ''}`} onClick={() => setSector(s)}>{s}</div>
                ))}
              </div>
            </>
          )}

          <button className="g-btn" onClick={handleGoogle} disabled={submitting}>
            <div className="g-icon" style={{ background: '#fff', color: '#333', fontSize: 11, fontWeight: 800 }}>G</div>
            {isLogin ? 'Entrar com Google' : 'Continuar com Google'}
          </button>

          <div className="auth-divider">— ou —</div>

          <div className="field">
            <label>Email</label>
            <input
              type="email"
              placeholder="carlos@suaempresa.com.br"
              value={email}
              onChange={e => setEmail(e.target.value)}
              disabled={submitting}
            />
          </div>
          <div className="field">
            <label>Senha</label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              disabled={submitting}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            />
          </div>

          {error && (
            <div style={{ fontSize: 12.5, color: 'var(--urg)', marginBottom: 4 }}>{error}</div>
          )}

          <button
            className="btn btn-blue"
            style={{ width: '100%' }}
            onClick={handleSubmit}
            disabled={submitting || !email || !password}
          >
            {submitting ? 'Aguarde…' : isLogin ? 'Entrar' : 'Criar conta'}
          </button>

          {isLogin ? (
            <div style={{ textAlign: 'center', marginTop: 14, fontSize: 12.5, color: 'var(--muted)' }}>
              Não tem uma conta?{' '}
              <span
                style={{ color: 'var(--blue3)', cursor: 'pointer' }}
                onClick={() => navigate('/onboarding')}
              >
                Criar conta grátis →
              </span>
            </div>
          ) : (
            <div style={{ textAlign: 'center', marginTop: 14, fontSize: 12.5, color: 'var(--muted)' }}>
              Ao criar conta você concorda com os{' '}
              <a href="#" style={{ color: 'var(--blue3)' }}>Termos de Uso</a> e a{' '}
              <a href="#" style={{ color: 'var(--blue3)' }}>Política de Privacidade</a>.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StepInfo({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const [vertical, setVertical] = useState('Comércio')
  const [teamSize, setTeamSize] = useState('Só eu')
  return (
    <div className="flow-page on">
      <FlowTop step="info" onBack={onBack} />
      <div className="flow-body">
        <div className="flow-card">
          <div className="fc-h">Sobre a sua empresa</div>
          <div className="fc-sub">O blu usa estas informações para calibrar os agentes ao seu setor.</div>
          <div className="row2">
            <div className="field"><label>Seu nome</label><input type="text" placeholder="Carlos Lima" /></div>
            <div className="field"><label>Nome da empresa *</label><input type="text" placeholder="Distribuidora Alvo" /></div>
          </div>
          <div className="field">
            <label>Website <span style={{ color: 'var(--muted)', fontWeight: 400 }}>(opcional)</span></label>
            <input type="url" placeholder="https://suaempresa.com.br" />
          </div>
          <div className="field">
            <label>Setor *</label>
            <div className="radio-pills">
              {VERTICALS.map(v => (
                <div key={v} className={`rp${vertical === v ? ' on' : ''}`} onClick={() => setVertical(v)}>{v}</div>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Tamanho da equipe *</label>
            <div className="radio-pills">
              {TEAM_SIZES.map(t => (
                <div key={t} className={`rp${teamSize === t ? ' on' : ''}`} onClick={() => setTeamSize(t)}>{t}</div>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button className="btn btn-ghost" onClick={onBack}>← Voltar</button>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={onNext}>Continuar →</button>
          </div>
        </div>
      </div>
    </div>
  )
}

function StepData({ onNext, onBack, onSkip }: { onNext: () => void; onBack: () => void; onSkip: () => void }) {
  const [connected, setConnected] = useState<Record<string, boolean>>({})
  return (
    <div className="flow-page on">
      <FlowTop step="data" onBack={onBack} />
      <div className="flow-body">
        <div className="flow-card" style={{ maxWidth: 600 }}>
          <div className="fc-h">Conecte seus dados</div>
          <div className="fc-sub">O blu aprende sobre seu negócio a partir dos seus dados. Escolha de onde vêm.</div>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: 10 }}>Sistemas</div>
          <div className="dsrc-grid">
            {SYSTEMS.map(s => (
              <div key={s.id} className={`dsrc${connected[s.id] ? ' connected' : ''}`} onClick={() => setConnected(p => ({ ...p, [s.id]: true }))}>
                <span className="dsrc-icon">{s.icon}</span>
                <div className="dsrc-name">{s.name}</div>
                <div className="dsrc-sub">{connected[s.id] ? '✓ Conectado' : s.sub}</div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)', margin: '18px 0 10px' }}>Arquivos</div>
          <div className="dsrc-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <div className={`dsrc${connected['gdrive'] ? ' connected' : ''}`} onClick={() => setConnected(p => ({ ...p, gdrive: true }))}>
              <span className="dsrc-icon">📁</span>
              <div className="dsrc-name">Google Drive</div>
              <div className="dsrc-sub">{connected['gdrive'] ? '✓ Conectado' : 'Planilhas'}</div>
            </div>
            <div className={`dsrc${connected['csv'] ? ' connected' : ''}`} onClick={() => setConnected(p => ({ ...p, csv: true }))}>
              <span className="dsrc-icon">📄</span>
              <div className="dsrc-name">Planilha CSV</div>
              <div className="dsrc-sub">{connected['csv'] ? '✓ Carregado' : 'Excel / CSV'}</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 22 }}>
            <button className="btn btn-ghost" onClick={onBack}>← Voltar</button>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={onNext}>Continuar → Mapear colunas</button>
          </div>
          <div style={{ textAlign: 'center', marginTop: 12, fontSize: 12, color: 'var(--muted)' }}>
            Prefere começar sem dados? <span style={{ color: 'var(--blue3)', cursor: 'pointer' }} onClick={onSkip}>Pular por agora →</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function StepMapping({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const [openGroup, setOpenGroup] = useState<'auto' | 'warn' | 'unknown' | null>(null)
  const [warnSelections, setWarnSelections] = useState<Record<string, string>>(
    Object.fromEntries(WARN_ROWS.map(r => [r.id, r.default]))
  )
  const [flagged, setFlagged] = useState<Record<string, boolean>>({ obs: true })

  const toggle = (g: 'auto' | 'warn' | 'unknown') => setOpenGroup(prev => prev === g ? null : g)

  return (
    <div className="flow-page map-page on">
      <FlowTop step="mapping" onBack={onBack} />
      <div className="map-body">
        <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-.03em', marginBottom: 5 }}>Revisão de mapeamento</div>
        <div style={{ fontSize: 14, color: 'var(--muted2)', marginBottom: 20 }}>
          O blu mapeou automaticamente as colunas do seu arquivo para o esquema interno. Revise, corrija ou sinalize qualquer erro.
        </div>
        <div className="map-summary">
          <div className="ms-chip ms-ok">✓ 14 mapeados automaticamente</div>
          <div className="ms-chip ms-warn">⚠ 4 precisam de confirmação</div>
          <div className="ms-chip ms-err">✗ 1 não reconhecido</div>
          <div className="ms-sep" />
          <button className="btn btn-primary ms-cta" onClick={onNext}>Confirmar e continuar →</button>
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--gb)', borderRadius: 'var(--rl)', overflow: 'hidden', backdropFilter: 'blur(12px)' }}>
          <table className="map-table">
            <thead>
              <tr>
                <th style={{ width: '22%' }}>Sua coluna</th>
                <th style={{ width: '6%', textAlign: 'center' }}>→</th>
                <th style={{ width: '24%' }}>Campo blu</th>
                <th style={{ width: '16%' }}>Confiança</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {/* Auto group */}
              <tr className="map-group-hd" onClick={() => toggle('auto')}>
                <td colSpan={6} className="map-section-hd">
                  <span className="mg-chevron" style={{ transform: openGroup === 'auto' ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                  <span>✅ Mapeados automaticamente</span>
                  <span className="mg-badge ok">14 campos</span>
                  <div className="map-section-line" />
                </td>
              </tr>
              {openGroup === 'auto' && AUTO_ROWS.map(r => (
                <tr key={r.col} className="map-row">
                  <td>{r.col}</td>
                  <td className="map-arrow">→</td>
                  <td className="map-target">{r.target}</td>
                  <td>
                    <div className="conf-bar">
                      <div className="cb-track"><div className="cb-fill cb-high" style={{ width: `${r.pct}%` }} /></div>
                      <span style={{ color: 'var(--ok)' }}>{r.pct}%</span>
                    </div>
                  </td>
                  <td className="map-status stat-ok">✓ Mapeado</td>
                  <td></td>
                </tr>
              ))}

              {/* Warn group */}
              <tr className="map-group-hd" onClick={() => toggle('warn')}>
                <td colSpan={6} className="map-section-hd">
                  <span className="mg-chevron" style={{ transform: openGroup === 'warn' ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                  <span>⚠ Precisam de confirmação</span>
                  <span className="mg-badge warn">4 campos</span>
                  <div className="map-section-line" />
                </td>
              </tr>
              {openGroup === 'warn' && WARN_ROWS.map(r => (
                <tr key={r.id} className="map-row">
                  <td>{r.col}</td>
                  <td className="map-arrow">→</td>
                  <td>
                    <select className="map-select" value={warnSelections[r.id]} onChange={e => setWarnSelections(p => ({ ...p, [r.id]: e.target.value }))}>
                      <option value="">Selecionar campo…</option>
                      {r.options.map(o => <option key={o} value={o}>{o}</option>)}
                      <option value="ignorar">— Ignorar esta coluna</option>
                    </select>
                  </td>
                  <td>
                    <div className="conf-bar">
                      <div className="cb-track"><div className="cb-fill cb-mid" style={{ width: `${r.pct}%` }} /></div>
                      <span style={{ color: 'var(--warn)' }}>{r.pct}%</span>
                    </div>
                  </td>
                  <td className="map-status stat-warn">⚠ Confirmar</td>
                  <td></td>
                </tr>
              ))}

              {/* Unknown group */}
              <tr className="map-group-hd" onClick={() => toggle('unknown')}>
                <td colSpan={6} className="map-section-hd">
                  <span className="mg-chevron" style={{ transform: openGroup === 'unknown' ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                  <span>✗ Não reconhecido</span>
                  <span className="mg-badge err">1 campo</span>
                  <div className="map-section-line" />
                </td>
              </tr>
              {openGroup === 'unknown' && (
                <tr className="map-row">
                  <td>obs_interna</td>
                  <td className="map-arrow" style={{ color: 'var(--urg)' }}>✗</td>
                  <td>
                    <select className="map-select">
                      <option value="">Mapear manualmente…</option>
                      <option value="observacoes">observacoes</option>
                      <option value="notas_internas">notas_internas</option>
                      <option value="campo_customizado">campo_customizado</option>
                      <option value="ignorar">— Ignorar esta coluna</option>
                    </select>
                  </td>
                  <td>
                    <div className="conf-bar">
                      <div className="cb-track"><div className="cb-fill" style={{ width: '0%', background: 'var(--urg)' }} /></div>
                      <span style={{ color: 'var(--urg)' }}>—</span>
                    </div>
                  </td>
                  <td className="map-status stat-err">✗ Desconhecido</td>
                  <td>
                    <button className={`map-flag${flagged['obs'] ? ' flagged' : ''}`} onClick={() => setFlagged(p => ({ ...p, obs: !p.obs }))}>
                      {flagged['obs'] ? 'Sinalizado' : 'Sinalizar erro'}
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 20, paddingBottom: 28 }}>
          <div style={{ fontSize: 13, color: 'var(--muted2)' }}>
            Dúvida em alguma coluna? <span style={{ color: 'var(--blue3)', cursor: 'pointer' }}>Ver documentação do esquema blu →</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost" onClick={onBack}>← Voltar</button>
            <button className="btn btn-primary" onClick={onNext}>Confirmar mapeamento →</button>
          </div>
        </div>
      </div>
    </div>
  )
}

function StepLaunch() {
  const navigate = useNavigate()
  const [progress, setProgress] = useState(0)
  const [visibleLogs, setVisibleLogs] = useState(0)
  const [done, setDone] = useState(false)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true

    const totalMs = 3200
    const start = Date.now()
    const tick = () => {
      const pct = Math.min(100, ((Date.now() - start) / totalMs) * 100)
      setProgress(pct)
      setVisibleLogs(Math.floor((pct / 100) * LAUNCH_LOG.length))
      if (pct < 100) requestAnimationFrame(tick)
      else { setDone(true); setVisibleLogs(LAUNCH_LOG.length) }
    }
    requestAnimationFrame(tick)
  }, [])

  return (
    <div className="flow-page on">
      <FlowTop step="launch" />
      <div className="launch-body">
        <div className="launch-icon">{done ? '✅' : '🚀'}</div>
        <div className="launch-h">{done ? 'Bureau pronto!' : 'Iniciando seu bureau'}</div>
        <div className="launch-sub">
          {done ? 'Seus agentes estão prontos. Bem-vindo ao blu.' : 'Os agentes estão aprendendo sobre o seu negócio. Isso leva alguns segundos.'}
        </div>
        <div className="launch-progress">
          <div className="lp-bar" style={{ width: `${progress}%` }} />
        </div>
        <div className="launch-log">
          {LAUNCH_LOG.map((line, i) => (
            <div key={i} className={`ll${i < visibleLogs ? ' show' : ''}`}>{line}</div>
          ))}
        </div>
        {done && (
          <button className="btn btn-primary btn-lg" style={{ marginTop: 28 }} onClick={() => navigate('/app')}>
            Entrar no blu →
          </button>
        )}
      </div>
    </div>
  )
}

export default function OnboardingApp() {
  const [step, setStep] = useState<Step>('auth')
  const [searchParams] = useSearchParams()
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  const mode = searchParams.get('mode') === 'login' ? 'login' : 'signup'

  // Already authenticated in login mode → go to app
  useEffect(() => {
    if (!loading && user && mode === 'login') {
      navigate('/app', { replace: true })
    }
  }, [user, loading, mode, navigate])

  const go = (s: Step) => setStep(s)

  if (loading) return null

  if (step === 'auth') return <StepAuth onNext={() => go('info')} mode={mode} />
  if (step === 'info') return <StepInfo onNext={() => go('data')} onBack={() => go('auth')} />
  if (step === 'data') return <StepData onNext={() => go('mapping')} onBack={() => go('info')} onSkip={() => go('launch')} />
  if (step === 'mapping') return <StepMapping onNext={() => go('launch')} onBack={() => go('data')} />
  return <StepLaunch />
}
