import { useState } from 'react'
import { useAppStore } from '../../store/appStore'

type Tab = 'decisoes' | 'tarefas' | 'historico' | 'config'


export default function ComprasRoom() {
  const { go, approve, reject, snooze } = useAppStore()
  const [tab, setTab] = useState<Tab>('decisoes')
  const decisions = useAppStore(s => s.decisions)

  const toggleDc = useAppStore(s => s.toggleDc)

  const getStatus = (id: string) => decisions[id]?.status ?? 'pending'

  return (
    <div>
      <div className="rh">
        <div className="rav">🛒</div>
        <div><div className="rn">Compras</div><div className="rd">Cotações, fornecedores e estoque</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }}>+ Nova Missão</button>
        </div>
      </div>
      <div className="room-grid">

        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph"><span className="ph-ttl">Mesa de Trabalho</span><span className="ph-cnt" id="cCnt">3 pendentes</span></div>
          <div className="rtabs" id="cTabs">
            {(['decisoes','tarefas','historico','config'] as Tab[]).map(t => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>
                {t === 'decisoes' ? <>Decisões <span className="tbdg">3</span></> : t.charAt(0).toUpperCase() + t.slice(1)}
              </div>
            ))}
          </div>
          <div className="pb">

            {/* DECISÕES */}
            <div className={`tc${tab === 'decisoes' ? ' on' : ''}`} id="c-decisoes">
              <div className="dl">

                {/* rc1 */}
                <div
                  className={['dc urg', getStatus('rc1') === 'expanded' ? 'expanded' : '', getStatus('rc1') === 'done' || getStatus('rc1') === 'rejected' ? 'done' : ''].filter(Boolean).join(' ')}
                  id="rc1"
                  style={getStatus('rc1') === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
                >
                  <div className="dc-row" onClick={() => toggleDc('rc1')}>
                    <div className="ag"><div className="agd" style={{ background: '#818cf8' }} />Toner HP 107A</div>
                    <span className="bdg bu">Crítico</span>
                    <span className="dc-row-summary"><strong>Estoque: 1 dia</strong> — Silva R$ 420 vs. Gamma R$ 380</span>
                    <span className="dt">10:32</span>
                    <span className="dc-ok-inline"><svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado</span>
                    <span className="dc-chev">▶</span>
                  </div>
                  <div className="dc-expand">
                    <div className="db"><strong>Estoque: 1 dia.</strong> Silva: R$ 420, entrega 2 dias. Gamma: R$ 380, 4 dias.</div>
                    <ul className="dbl"><li>Silva: R$ 420, nota 5/5, 0 atrasos</li><li>Gamma: R$ 380, nota 3/5, 2 atrasos</li></ul>
                    <div className="dc-act">
                      <button className="btn bp" onClick={() => approve('rc1', 'Pedido com Fornecedor Silva autorizado.')}>👍 Aprovar Silva</button>
                      <button className="btn bs">✏️ Editar</button>
                      <button className="btn brd" onClick={() => reject('rc1')}>👎 Rejeitar</button>
                      <button className="btn bg" onClick={() => snooze('rc1')}>⏰ Depois</button>
                    </div>
                    <div className="dc-ins"><span>💡</span>Silva 10% mais caro mas 0 atrasos nos últimos 6 meses.</div>
                    <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado — Fornecedor Silva</div>
                  </div>
                </div>

                {/* rc2 */}
                <div
                  className={['dc warn', getStatus('rc2') === 'expanded' ? 'expanded' : '', getStatus('rc2') === 'done' ? 'done' : ''].filter(Boolean).join(' ')}
                  id="rc2"
                  style={getStatus('rc2') === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
                >
                  <div className="dc-row" onClick={() => toggleDc('rc2')}>
                    <div className="ag"><div className="agd" style={{ background: '#818cf8' }} />Papel A4</div>
                    <span className="bdg bw">5 dias</span>
                    <span className="dc-row-summary"><strong>Estoque baixo</strong> — Gamma: 10 resmas, R$ 378, entrega 4d</span>
                    <span className="dt">09:45</span>
                    <span className="dc-ok-inline"><svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado</span>
                    <span className="dc-chev">▶</span>
                  </div>
                  <div className="dc-expand">
                    <div className="db"><strong>Estoque baixo.</strong> Gamma: 10 resmas, R$ 378, entrega 4 dias.</div>
                    <div className="dc-act">
                      <button className="btn bp" onClick={() => approve('rc2', 'Papel A4 aprovado com Gamma.')}>👍 Aprovar</button>
                      <button className="btn bg" onClick={() => snooze('rc2')}>⏰ Depois</button>
                    </div>
                    <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado — Gamma</div>
                  </div>
                </div>

                {/* rc3 */}
                <div
                  className={['dc warn', getStatus('rc3') === 'expanded' ? 'expanded' : '', getStatus('rc3') === 'done' ? 'done' : ''].filter(Boolean).join(' ')}
                  id="rc3"
                  style={getStatus('rc3') === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
                >
                  <div className="dc-row" onClick={() => toggleDc('rc3')}>
                    <div className="ag"><div className="agd" style={{ background: '#818cf8' }} />Café</div>
                    <span className="bdg bw">2 dias</span>
                    <span className="dc-row-summary"><strong>Estoque acabando</strong> — Café do Sul: 3 kg, R$ 282</span>
                    <span className="dt">08:47</span>
                    <span className="dc-ok-inline"><svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado</span>
                    <span className="dc-chev">▶</span>
                  </div>
                  <div className="dc-expand">
                    <div className="db"><strong>Estoque acabando.</strong> Café do Sul: 3 kg, R$ 282 (★★★★☆).</div>
                    <div className="dc-act">
                      <button className="btn bp" onClick={() => approve('rc3', 'Café do Sul — 3 kg aprovado.')}>👍 Aprovar</button>
                      <button className="btn bs">✏️ Editar</button>
                      <button className="btn bg" onClick={() => snooze('rc3')}>⏰ Depois</button>
                    </div>
                    <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado — Café do Sul</div>
                  </div>
                </div>

              </div>
            </div>

            {/* TAREFAS */}
            <div className={`tc${tab === 'tarefas' ? ' on' : ''}`} id="c-tarefas">
              <div className="task-row"><span>🔄</span><div style={{ flex: 1 }}><div style={{ fontSize: 12.5, fontWeight: 500 }}>Monitoramento semanal de estoque</div><div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 1 }}>Seg 07/05 às 08:00</div></div><span className="pill on" style={{ pointerEvents: 'none' }}>Ativa</span></div>
              <div className="task-row"><span>📨</span><div style={{ flex: 1 }}><div style={{ fontSize: 12.5, fontWeight: 500 }}>Cotação mensal de suprimentos</div><div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 1 }}>Aguardando 2 respostas</div></div><span className="pill" style={{ background: 'var(--adm2)', borderColor: 'rgba(245,158,11,.3)', color: 'var(--att)', pointerEvents: 'none' }}>Pendente</span></div>
              <div className="task-row"><span>📊</span><div style={{ flex: 1 }}><div style={{ fontSize: 12.5, fontWeight: 500 }}>Análise de desempenho de fornecedores</div><div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 1 }}>Max e Gamma com alerta</div></div><span className="pill" style={{ pointerEvents: 'none' }}>Concluída</span></div>
            </div>

            {/* HISTÓRICO */}
            <div className={`tc${tab === 'historico' ? ' on' : ''}`} id="c-historico">
              <div className="hi"><div className="hi-n">Toner HP 107A × 2 — Silva</div><div className="hi-m"><span>22 Abr</span><span className="hi-a">R$ 840</span><span style={{ color: 'var(--ok)' }}>✓</span></div></div>
              <div className="hi"><div className="hi-n">Papel A4 × 10 — Gamma</div><div className="hi-m"><span>15 Abr</span><span className="hi-a">R$ 378</span><span style={{ color: 'var(--ok)' }}>✓</span></div></div>
              <div className="hi"><div className="hi-n">Café 5 kg — Café do Sul</div><div className="hi-m"><span>20 Abr</span><span className="hi-a">R$ 470</span><span style={{ color: 'var(--ok)' }}>✓</span></div></div>
              <div className="hi"><div className="hi-n">Material limpeza — Gamma</div><div className="hi-m"><span>10 Abr</span><span className="hi-a">R$ 234</span><span style={{ color: 'var(--ok)' }}>✓</span></div></div>
              <div className="hi"><div className="hi-n">Papel A4 × 5 — TechPaper</div><div className="hi-m"><span>02 Abr</span><span className="hi-a">R$ 205</span><span style={{ color: 'var(--urg)' }}>✗ Atraso 2d</span></div></div>
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`} id="c-config">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Limite para aprovação automática</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 8 }}>Compras com fornecedor preferido abaixo deste valor aprovadas automaticamente.</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <div style={{ background: 'rgba(0,0,0,.3)', border: '1px solid var(--gb)', borderRadius: 5, padding: '5px 10px', fontFamily: 'var(--mono)', fontSize: 12, flex: 1 }}>R$ 500</div>
                    <button className="btn bs" style={{ fontSize: 11 }}>Editar</button>
                  </div>
                </div>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Alerta de estoque baixo</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 7 }}>Notificar quando restar X dias de estoque.</div>
                  <div className="pills"><span className="pill on">3 dias</span><span className="pill">5 dias</span><span className="pill">7 dias</span></div>
                </div>
              </div>
            </div>

          </div>
        </div>

        <div className="rcol">
          <div className="panel">
            <div className="ph"><span className="ph-ico">📁</span><span className="ph-ttl">Fornecedores</span><button className="ph-add">＋</button></div>
            <div className="pb">
              <div className="dr-sec">
                <div className="pills"><span className="pill on">Todos</span><span className="pill">Escritório</span><span className="pill">Insumos</span></div>
                <div className="sup-row"><span>🏪</span><div><div className="sup-n">Fornecedor Silva</div><div className="sup-c">Suprimentos</div></div><span className="stars">★★★★★</span></div>
                <div className="sup-row"><span>🏪</span><div><div className="sup-n">Café do Sul</div><div className="sup-c">Alimentos</div></div><span className="stars">★★★★☆</span></div>
                <div className="sup-row"><span>🏪</span><div><div className="sup-n">Gamma</div><div className="sup-c">Escritório</div></div><span className="stars">★★★☆☆</span></div>
                <div className="sup-row"><span>🏪</span><div><div className="sup-n">Max Distribuidora</div><div className="sup-c" style={{ color: 'var(--urg)' }}>⚠ Prazo crescendo</div></div><span className="stars">★★★☆☆</span></div>
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Este mês</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11.5 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Total gasto</span><span style={{ fontFamily: 'var(--mono)' }}>R$ 8.420</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Aprovadas</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>24</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Economia IA</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>R$ 640</span></div>
                </div>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="ph"><span className="ph-ico">🕐</span><span className="ph-ttl">Histórico recente</span></div>
            <div className="pb">
              <div className="dr-sec">
                <div className="hi"><div className="hi-n">Toner HP 107A × 2</div><div className="hi-m"><span>22 Abr</span><span className="hi-a">R$ 840</span></div></div>
                <div className="hi"><div className="hi-n">Papel A4 × 10</div><div className="hi-m"><span>15 Abr</span><span className="hi-a">R$ 378</span></div></div>
                <div className="hi"><div className="hi-n">Café 5 kg</div><div className="hi-m"><span>20 Abr</span><span className="hi-a">R$ 470</span></div></div>
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Por categoria</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                  <div><div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--mu2)', marginBottom: 3 }}><span>Escritório</span><span style={{ fontFamily: 'var(--mono)' }}>R$ 1.218</span></div><div style={{ background: 'var(--gb)', borderRadius: 2, height: 3 }}><div style={{ background: 'var(--ac)', width: '58%', height: '100%', borderRadius: 2 }} /></div></div>
                  <div><div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--mu2)', marginBottom: 3 }}><span>Alimentação</span><span style={{ fontFamily: 'var(--mono)' }}>R$ 470</span></div><div style={{ background: 'var(--gb)', borderRadius: 2, height: 3 }}><div style={{ background: '#818cf8', width: '22%', height: '100%', borderRadius: 2 }} /></div></div>
                  <div><div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--mu2)', marginBottom: 3 }}><span>Limpeza</span><span style={{ fontFamily: 'var(--mono)' }}>R$ 234</span></div><div style={{ background: 'var(--gb)', borderRadius: 2, height: 3 }}><div style={{ background: '#34d399', width: '11%', height: '100%', borderRadius: 2 }} /></div></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bstrip">
          <div className="ich"><span className="ich-em">🔍</span><div className="ich-body"><span className="ich-tag tg-s">Insight</span><div className="ich-txt">Fornecedores de café na região com preço menor. Ver alternativas?</div></div></div>
          <div className="ich"><span className="ich-em">⚠️</span><div className="ich-body"><span className="ich-tag tg-s">Alerta</span><div className="ich-txt">Max Distribuidora: atraso em 40% dos pedidos. Criar política de substituição?</div></div></div>
          <div className="ich"><span className="ich-em">💡</span><div className="ich-body"><span className="ich-tag tg-f">Otimização</span><div className="ich-txt">Pedidos de escritório e limpeza são simultâneos — unificar gera desconto de volume</div></div></div>
          <div className="nums-chip">
            <div className="nums-head">⚙️ Rotinas ativas</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--ok)', flexShrink: 0 }} /><span style={{ color: 'var(--mu2)' }}>Estoque</span><span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>Seg 08:00</span></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--ok)', flexShrink: 0 }} /><span style={{ color: 'var(--mu2)' }}>Cotação mensal</span><span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>Dia 1</span></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--att)', flexShrink: 0 }} /><span style={{ color: 'var(--mu2)' }}>Alerta crítico</span><span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>Tempo real</span></div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
