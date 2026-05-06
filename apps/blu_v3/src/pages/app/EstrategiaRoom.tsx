import { useState } from 'react'
import { useAppStore } from '../../store/appStore'

type Tab = 'decisoes' | 'analises' | 'docs' | 'historico'

export default function EstrategiaRoom() {
  const { go, approve, reject, snooze, toggleDc } = useAppStore()
  const decisions = useAppStore(s => s.decisions)
  const [tab, setTab] = useState<Tab>('decisoes')
  const [docsOpen, setDocsOpen] = useState<string | null>(null)

  const getStatus = (id: string) => decisions[id]?.status ?? 'pending'

  const docs = [
    { id: 'd1', icon: '📋', name: 'Planejamento Estratégico 2026', date: '12 Jan', status: 'Revisão', statusColor: 'var(--att)' },
    { id: 'd2', icon: '🗺️', name: 'Mapeamento de Processos — Comercial', date: '03 Mar', status: 'Ativo', statusColor: 'var(--ok)' },
    { id: 'd3', icon: '🎯', name: 'OKRs Q2 2026', date: '01 Abr', status: 'Em andamento', statusColor: 'var(--ac)' },
    { id: 'd4', icon: '🔍', name: 'Análise SWOT', date: '15 Fev', status: 'Finalizado', statusColor: 'var(--mu)' },
    { id: 'd5', icon: '💼', name: 'Canvas de Modelo de Negócio', date: '10 Jan', status: 'Finalizado', statusColor: 'var(--mu)' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="rh">
        <div className="rav">🎯</div>
        <div><div className="rn">Estratégia</div><div className="rd">Análises, KPIs e planejamento</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }}>+ Nova Análise</button>
        </div>
      </div>
      <div className="room-grid">

        {/* MAIN PANEL */}
        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph"><span className="ph-ttl">Mesa de Trabalho</span></div>
          <div className="rtabs">
            {(['decisoes', 'analises', 'docs', 'historico'] as Tab[]).map(t => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>
                {t === 'decisoes' ? <>Decisões <span className="tbdg">2</span></> :
                 t === 'analises' ? 'Análises' :
                 t === 'docs' ? 'Documentos' : 'Histórico'}
              </div>
            ))}
          </div>
          <div className="pb">

            {/* DECISÕES */}
            <div className={`tc${tab === 'decisoes' ? ' on' : ''}`}>
              <div className="dl">
                <div
                  className={['dc warn', getStatus('es1') === 'expanded' ? 'expanded' : '', getStatus('es1') === 'done' || getStatus('es1') === 'rejected' ? 'done' : ''].filter(Boolean).join(' ')}
                  style={getStatus('es1') === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
                >
                  <div className="dc-row" onClick={() => toggleDc('es1')}>
                    <div className="ag"><div className="agd" style={{ background: '#fbbf24' }} />Estratégia</div>
                    <span className="bdg bw">Atenção</span>
                    <span className="dc-row-summary"><strong>Margem Produto Y</strong> acima da média do setor — oportunidade de repricing</span>
                    <span className="dt">09:20</span>
                    <span className="dc-ok-inline"><svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado</span>
                    <span className="dc-chev">▶</span>
                  </div>
                  <div className="dc-expand">
                    <div className="db"><strong>Margem do Produto Y: 58%</strong> vs. média do setor 41%. Janela de repricing identificada.</div>
                    <ul className="dbl">
                      <li>Margem atual: 58% · Setor: 41%</li>
                      <li>Preço sugerido: +12% sem perda de volume (elasticidade 0.3)</li>
                      <li>Receita adicional estimada: R$ 38K/mês</li>
                    </ul>
                    <div className="dc-act">
                      <button className="btn bp" onClick={() => approve('es1', 'Análise de repricing aprovada. Ajuste programado.')}>👍 Aprovar análise</button>
                      <button className="btn bs">📊 Ver dados</button>
                      <button className="btn bg" onClick={() => snooze('es1')}>⏰ Depois</button>
                    </div>
                    <div className="dc-ins"><span>💡</span>Baseado em 90 dias de dados comparativos com 12 concorrentes diretos.</div>
                    <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Análise aprovada — repricing agendado</div>
                  </div>
                </div>

                <div
                  className={['dc warn', getStatus('es2') === 'expanded' ? 'expanded' : '', getStatus('es2') === 'done' || getStatus('es2') === 'rejected' ? 'done' : ''].filter(Boolean).join(' ')}
                  style={getStatus('es2') === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
                >
                  <div className="dc-row" onClick={() => toggleDc('es2')}>
                    <div className="ag"><div className="agd" style={{ background: '#fbbf24' }} />Estratégia</div>
                    <span className="bdg bw">Alerta</span>
                    <span className="dc-row-summary"><strong>2 fornecedores</strong> com prazo crescente — risco de ruptura Q3</span>
                    <span className="dt">08:55</span>
                    <span className="dc-ok-inline"><svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado</span>
                    <span className="dc-chev">▶</span>
                  </div>
                  <div className="dc-expand">
                    <div className="db"><strong>Max (+3 dias) e Gamma (+2 dias)</strong> mostram tendência de atraso. Risco de ruptura em Q3 se continuar.</div>
                    <ul className="dbl">
                      <li>Max: prazo médio subiu de 3d para 6d nos últimos 45 dias</li>
                      <li>Gamma: 2 atrasos no mês — queda de nota 4→3</li>
                      <li>Diversificação recomendada: adicionar 1 fornecedor alternativo</li>
                    </ul>
                    <div className="dc-act">
                      <button className="btn bp" onClick={() => approve('es2', 'Plano de diversificação aprovado.')}>👍 Diversificar</button>
                      <button className="btn bs">📋 Ver histórico</button>
                      <button className="btn bg" onClick={() => reject('es2')}>Ignorar</button>
                    </div>
                    <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Plano aprovado — Compras notificado</div>
                  </div>
                </div>
              </div>
            </div>

            {/* ANÁLISES */}
            <div className={`tc${tab === 'analises' ? ' on' : ''}`}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  { icon: '📈', name: 'Análise de margem — Produto Y', period: 'Q1 2026', status: 'Concluída', ok: true },
                  { icon: '🔄', name: 'Tendência de churn — Clientes B2B', period: 'Abr 2026', status: 'Em andamento', ok: false },
                  { icon: '📊', name: 'Benchmark setorial — Suprimentos', period: 'Mar 2026', status: 'Concluída', ok: true },
                  { icon: '🌡️', name: 'Monitoramento de preços — Concorrentes', period: 'Contínuo', status: 'Ativa', ok: true },
                ].map((a, i) => (
                  <div key={i} className="task-row" style={{ cursor: 'pointer' }}>
                    <span style={{ fontSize: 16 }}>{a.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12.5, fontWeight: 500 }}>{a.name}</div>
                      <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 1 }}>{a.period}</div>
                    </div>
                    <span className="pill" style={{ pointerEvents: 'none', background: a.ok ? 'var(--odim)' : 'var(--adim2)', borderColor: a.ok ? 'rgba(16,185,129,.3)' : 'rgba(245,158,11,.3)', color: a.ok ? 'var(--ok)' : 'var(--att)' }}>{a.status}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* DOCUMENTOS ESTRATÉGICOS */}
            <div className={`tc${tab === 'docs' ? ' on' : ''}`}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                {docs.map(d => (
                  <div key={d.id} className="task-row" style={{ cursor: 'pointer' }} onClick={() => setDocsOpen(docsOpen === d.id ? null : d.id)}>
                    <span style={{ fontSize: 16 }}>{d.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12.5, fontWeight: 500 }}>{d.name}</div>
                      <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 1 }}>Atualizado em {d.date}</div>
                    </div>
                    <span className="pill" style={{ pointerEvents: 'none', fontSize: 10, background: 'var(--glass)', borderColor: 'var(--gb)', color: d.statusColor }}>{d.status}</span>
                    <span style={{ color: 'var(--mu)', fontSize: 10, marginLeft: 4 }}>{docsOpen === d.id ? '▼' : '▶'}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* HISTÓRICO */}
            <div className={`tc${tab === 'historico' ? ' on' : ''}`}>
              <div className="hi"><div className="hi-n">Análise de margem Q4 2025</div><div className="hi-m"><span>10 Jan</span><span style={{ color: 'var(--ok)' }}>Aprovada</span></div></div>
              <div className="hi"><div className="hi-n">OKRs Q1 2026 definidos</div><div className="hi-m"><span>02 Jan</span><span style={{ color: 'var(--ok)' }}>Aprovados</span></div></div>
              <div className="hi"><div className="hi-n">Benchmark suprimentos</div><div className="hi-m"><span>15 Mar</span><span style={{ color: 'var(--ok)' }}>Concluído</span></div></div>
              <div className="hi"><div className="hi-n">Análise SWOT 2026</div><div className="hi-m"><span>20 Fev</span><span style={{ color: 'var(--mu)' }}>Arquivada</span></div></div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="rcol">
          <div className="panel">
            <div className="ph"><span className="ph-ico">📐</span><span className="ph-ttl">Métricas monitoradas</span></div>
            <div className="pb">
              <div className="dr-sec">
                <div className="dr-ttl">KPIs ativos</div>
                {[
                  { name: 'Margem bruta', val: '42,5%', delta: '+2,1pp', up: true },
                  { name: 'Churn mensal', val: '2,1%', delta: '-0,4pp', up: true },
                  { name: 'LTV médio', val: 'R$ 4.820', delta: '+8%', up: true },
                  { name: 'CAC', val: 'R$ 380', delta: '+12%', up: false },
                ].map((k, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--gb)', fontSize: 12 }}>
                    <span style={{ flex: 1, color: 'var(--mu2)' }}>{k.name}</span>
                    <span style={{ fontFamily: 'var(--mono)', fontVariantNumeric: 'tabular-nums' }}>{k.val}</span>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: k.up ? 'var(--ok)' : 'var(--urg)', marginLeft: 8, minWidth: 36, textAlign: 'right' }}>{k.delta}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="ph"><span className="ph-ico">🎯</span><span className="ph-ttl">OKRs Q2</span></div>
            <div className="pb">
              <div className="dr-sec">
                {[
                  { name: 'Receita +20%', pct: 62 },
                  { name: 'Churn < 1,5%', pct: 45 },
                  { name: '300 novos clientes', pct: 78 },
                  { name: 'Margem > 45%', pct: 55 },
                ].map((o, i) => (
                  <div key={i} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: 'var(--mu2)', marginBottom: 4 }}>
                      <span>{o.name}</span>
                      <span style={{ fontFamily: 'var(--mono)', color: o.pct >= 70 ? 'var(--ok)' : 'var(--att)' }}>{o.pct}%</span>
                    </div>
                    <div style={{ background: 'var(--gb)', borderRadius: 2, height: 4 }}>
                      <div style={{ background: o.pct >= 70 ? 'var(--ok)' : 'var(--att)', width: `${o.pct}%`, height: '100%', borderRadius: 2 }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip">
          <div className="ich"><span className="ich-em">📈</span><div className="ich-body"><span className="ich-tag tg-e">Estratégia</span><div className="ich-txt">Produto Y com margem 58% vs. setor 41% — janela de repricing aberta</div></div></div>
          <div className="ich"><span className="ich-em">⚡</span><div className="ich-body"><span className="ich-tag tg-s">Alerta</span><div className="ich-txt">2 fornecedores com prazo crescente — risco de ruptura em Q3</div></div></div>
          <div className="ich"><span className="ich-em">🔮</span><div className="ich-body"><span className="ich-tag tg-e">Previsão</span><div className="ich-txt">Tendência positiva de crescimento: +18% esperado em Q2 vs. Q1</div></div></div>
          <div className="nums-chip">
            <div className="nums-head">📊 Análises ativas</div>
            <div className="nums-row">
              <div className="nkpi"><span className="nv" style={{ fontSize: 18 }}>4</span><span className="nl">em andamento</span></div>
              <div className="nkpi"><span className="nv" style={{ fontSize: 18, color: 'var(--ok)' }}>12</span><span className="nl">concluídas</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
