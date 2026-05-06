import { useState } from 'react'
import { useAppStore } from '../../store/appStore'

type Tab = 'decisoes' | 'tarefas' | 'relatorios' | 'config'

export default function FinanceiroRoom() {
  const { go, approve, snooze } = useAppStore()
  const [tab, setTab] = useState<Tab>('decisoes')
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const decisions = useAppStore(s => s.decisions)
  const toggleDc = useAppStore(s => s.toggleDc)

  const fd1Status = decisions['fd1']?.status ?? 'pending'

  return (
    <div>
      <div className="rh">
        <div className="rav">📊</div>
        <div><div className="rn">Financeiro</div><div className="rd">Fluxo de caixa, pagamentos e relatórios</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }}>+ Nova Missão</button>
        </div>
      </div>
      <div className="room-grid">

        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph"><span className="ph-ttl">Mesa de Trabalho</span><span className="ph-cnt">1 pendente</span></div>
          <div className="rtabs" id="fTabs">
            {(['decisoes','tarefas','relatorios','config'] as Tab[]).map(t => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>
                {t === 'decisoes' ? <>Decisões <span className="tbdg">1</span></> : t === 'relatorios' ? 'Relatórios' : t.charAt(0).toUpperCase() + t.slice(1)}
              </div>
            ))}
          </div>
          <div className="pb">

            {/* DECISÕES */}
            <div className={`tc${tab === 'decisoes' ? ' on' : ''}`} id="f-decisoes">
              <div className="dl">
                <div
                  className={['dc warn', fd1Status === 'expanded' ? 'expanded' : '', fd1Status === 'done' ? 'done' : ''].filter(Boolean).join(' ')}
                  id="fd1"
                  style={fd1Status === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
                >
                  <div className="dc-row" onClick={() => toggleDc('fd1')}>
                    <div className="ag"><div className="agd" style={{ background: '#34d399' }} />Boleto</div>
                    <span className="bdg bw">Amanhã</span>
                    <span className="dc-row-summary"><strong>Boleto Claro Empresas</strong> — R$ 847,50 vence 06/05</span>
                    <span className="dt">09:15</span>
                    <span className="dc-ok-inline"><svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Agendado</span>
                    <span className="dc-chev">▶</span>
                  </div>
                  <div className="dc-expand">
                    <div className="db"><strong>Boleto Claro Empresas</strong> vence amanhã. <strong>R$ 847,50</strong>. Itaú: R$ 12.340 disponível.</div>
                    <ul className="dbl"><li>Vencimento: 06/05 · Conta Itaú 0001 / CC 12345-6</li><li>Saldo atual cobre o pagamento com folga</li></ul>
                    <div className="dc-act">
                      <button className="btn bp" onClick={() => approve('fd1', 'Pagamento agendado. R$ 847,50 para 06/05.')}>👍 Agendar</button>
                      <button className="btn bs">✏️ Editar</button>
                      <button className="btn bg" onClick={() => snooze('fd1')}>⏰ Depois</button>
                    </div>
                    <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Agendado — Itaú · 06/05</div>
                  </div>
                </div>
              </div>

              {/* ANALYTICS EXPANDABLE CARD */}
              <div className="anl-card" id="anlCard">
                <div className="anl-hd" onClick={() => setAnalyticsOpen(o => !o)}>
                  <span className="anl-ttl">📊 Analytics</span>
                  <div className="anl-nums">
                    <div className="anl-kpi"><span className="anl-v">543,8K</span><span className="anl-l">Faturamento</span></div>
                    <div className="anl-kpi"><span className="anl-v" style={{ color: 'var(--ok)' }}>42,5%</span><span className="anl-l">Margem</span></div>
                    <div className="anl-kpi"><span className="anl-v">R$ 18,4K</span><span className="anl-l">Caixa</span></div>
                  </div>
                  <span className={`anl-chev${analyticsOpen ? ' open' : ''}`} id="anlChev">▶</span>
                </div>
                <div className={`anl-body${analyticsOpen ? ' open' : ''}`} id="anlBody">
                  <div className="anl-kpi-grid">
                    <div className="anl-kc"><div className="anl-kl">Faturamento</div><div className="anl-kv">543,8K</div><div className="anl-kd up">↑ 12% vs. abr</div></div>
                    <div className="anl-kc"><div className="anl-kl">Despesas</div><div className="anl-kv">312,4K</div><div className="anl-kd dn">↑ 7%</div></div>
                    <div className="anl-kc"><div className="anl-kl">Margem bruta</div><div className="anl-kv" style={{ color: 'var(--ok)' }}>42,5%</div><div className="anl-kd up">↑ 2,1pp</div></div>
                    <div className="anl-kc"><div className="anl-kl">Caixa consolidado</div><div className="anl-kv">R$ 18,4K</div><div className="anl-kd up">↑ 8%</div></div>
                    <div className="anl-kc"><div className="anl-kl">Ticket médio</div><div className="anl-kv">R$ 509</div><div className="anl-kd up">↑ 3,5%</div></div>
                    <div className="anl-kc"><div className="anl-kl">Pedidos</div><div className="anl-kv">1.067</div><div className="anl-kd up">↑ 8%</div></div>
                  </div>
                  <div style={{ marginBottom: 11 }}>
                    <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--mu)', marginBottom: 7 }}>Despesas por categoria</div>
                    <div className="bar-label"><span>Folha</span><span style={{ fontFamily: 'var(--mono)' }}>R$ 148K · 47%</span></div>
                    <div className="bar-track"><div className="bar-fill" style={{ width: '47%', background: '#818cf8' }} /></div>
                    <div className="bar-label"><span>Fornecedores</span><span style={{ fontFamily: 'var(--mono)' }}>R$ 72K · 23%</span></div>
                    <div className="bar-track"><div className="bar-fill" style={{ width: '23%', background: 'var(--ac)' }} /></div>
                    <div className="bar-label"><span>Aluguel</span><span style={{ fontFamily: 'var(--mono)' }}>R$ 38K · 12%</span></div>
                    <div className="bar-track"><div className="bar-fill" style={{ width: '12%', background: '#34d399' }} /></div>
                    <div className="bar-label"><span>Operacional</span><span style={{ fontFamily: 'var(--mono)' }}>R$ 54K · 17%</span></div>
                    <div className="bar-track" style={{ marginBottom: 0 }}><div className="bar-fill" style={{ width: '17%', background: 'var(--att)' }} /></div>
                  </div>
                  <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--mu)', marginBottom: 5 }}>Tendência faturamento — 8 meses</div>
                  <svg viewBox="0 0 280 44" width="100%" height="44" style={{ display: 'block', overflow: 'visible' }}>
                    <defs><linearGradient id="spGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="rgba(140,95,219,.25)" /><stop offset="100%" stopColor="rgba(140,95,219,0)" /></linearGradient></defs>
                    <path d="M0,40 L40,36 L80,32 L120,28 L160,22 L200,16 L240,10 L280,6" stroke="var(--ac)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
                    <path d="M0,40 L40,36 L80,32 L120,28 L160,22 L200,16 L240,10 L280,6 L280,44 L0,44Z" fill="url(#spGrad)" />
                    <circle cx="280" cy="6" r="2.5" fill="var(--ac)" />
                  </svg>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--mu)', fontFamily: 'var(--mono)', marginTop: 3 }}>
                    <span>Out</span><span>Nov</span><span>Dez</span><span>Jan</span><span>Fev</span><span>Mar</span><span>Abr</span><span>Mai</span>
                  </div>
                  <div className="pills" style={{ marginTop: 9, marginBottom: 0 }}>
                    <span className="pill on">30d</span>
                    <span className="pill">90d</span>
                    <span className="pill">1 ano</span>
                  </div>
                </div>
              </div>
            </div>

            {/* TAREFAS */}
            <div className={`tc${tab === 'tarefas' ? ' on' : ''}`} id="f-tarefas">
              <div className="task-row"><span>📅</span><div style={{ flex: 1 }}><div style={{ fontSize: 12.5, fontWeight: 500 }}>Fechamento mensal automático</div><div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 1 }}>Agendado para 31/05</div></div><span className="pill on" style={{ pointerEvents: 'none' }}>Ativa</span></div>
              <div className="task-row"><span>📊</span><div style={{ flex: 1 }}><div style={{ fontSize: 12.5, fontWeight: 500 }}>DRE mensal — geração automática</div><div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 1 }}>Gerado em 01/05, enviado ao contador</div></div><span className="pill" style={{ pointerEvents: 'none' }}>Concluída</span></div>
              <div className="task-row"><span>🔔</span><div style={{ flex: 1 }}><div style={{ fontSize: 12.5, fontWeight: 500 }}>Alerta de variação de custos</div><div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 1 }}>Dispara se variação {'>'} 10%</div></div><span className="pill on" style={{ pointerEvents: 'none' }}>Ativa</span></div>
            </div>

            {/* RELATÓRIOS */}
            <div className={`tc${tab === 'relatorios' ? ' on' : ''}`} id="f-relatorios">
              <div className="hi"><div className="hi-n">DRE Abril 2026</div><div className="hi-m"><span>01 Mai</span><span className="hi-a" style={{ color: 'var(--ok)' }}>✓ Enviado</span></div></div>
              <div className="hi"><div className="hi-n">Fluxo de Caixa — Abr</div><div className="hi-m"><span>01 Mai</span><span className="hi-a">PDF</span></div></div>
              <div className="hi"><div className="hi-n">Análise de Margem Q1</div><div className="hi-m"><span>03 Abr</span><span className="hi-a">PDF</span></div></div>
              <div className="hi"><div className="hi-n">DRE Março 2026</div><div className="hi-m"><span>01 Abr</span><span className="hi-a" style={{ color: 'var(--ok)' }}>✓ Enviado</span></div></div>
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`} id="f-config">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Alerta de variação de custos</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 7 }}>Notificar quando uma categoria variar mais que:</div>
                  <div className="pills"><span className="pill on">10%</span><span className="pill">15%</span><span className="pill">20%</span></div>
                </div>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Geração automática de DRE</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 7 }}>Gerar e enviar ao contador no dia:</div>
                  <div className="pills"><span className="pill">1</span><span className="pill on">2</span><span className="pill">5</span><span className="pill">10</span></div>
                </div>
              </div>
            </div>

          </div>
        </div>

        <div className="rcol">
          <div className="panel">
            <div className="ph"><span className="ph-ico">🏦</span><span className="ph-ttl">Contas</span><button className="ph-add">＋</button></div>
            <div className="pb">
              <div className="dr-sec">
                <div className="acc-row"><span style={{ fontSize: 13 }}>🏦</span><div className="acc-name"><div style={{ fontSize: 12, fontWeight: 500 }}>Itaú Empresas</div><div style={{ fontSize: 10, color: 'var(--mu)' }}>CC 12345-6</div></div><div><div className="acc-val">R$ 12.340</div><div style={{ fontSize: 9.5, color: 'var(--ok)', fontFamily: 'var(--mono)' }}>↑ sincronizado</div></div></div>
                <div className="acc-row"><span style={{ fontSize: 13 }}>🏦</span><div className="acc-name"><div style={{ fontSize: 12, fontWeight: 500 }}>Bradesco</div><div style={{ fontSize: 10, color: 'var(--mu)' }}>CC 98765-4</div></div><div><div className="acc-val">R$ 8.210</div><div style={{ fontSize: 9.5, color: 'var(--ok)', fontFamily: 'var(--mono)' }}>↑ sincronizado</div></div></div>
                <div className="acc-row"><span style={{ fontSize: 13 }}>💳</span><div className="acc-name"><div style={{ fontSize: 12, fontWeight: 500 }}>Cartão Corp.</div><div style={{ fontSize: 10, color: 'var(--mu)' }}>Itaú Visa</div></div><div><div className="acc-val" style={{ color: 'var(--urg)' }}>−R$ 2.180</div><div style={{ fontSize: 9.5, color: 'var(--att)', fontFamily: 'var(--mono)' }}>Fatura 12/05</div></div></div>
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Saldo consolidado</div>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--mono)', fontVariantNumeric: 'tabular-nums', color: 'var(--fg)' }}>R$ 18.370</div>
                <div style={{ fontSize: 10, color: 'var(--ok)', marginTop: 2 }}>↑ 8% vs mês anterior</div>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="ph"><span className="ph-ico">📄</span><span className="ph-ttl">Próximos pagamentos</span></div>
            <div className="pb">
              <div className="dr-sec">
                <div className="hi"><div className="hi-n">Claro Empresas</div><div className="hi-m"><span>06/05</span><span className="hi-a" style={{ color: 'var(--att)' }}>R$ 847,50</span><span style={{ color: 'var(--att)' }}>Amanhã</span></div></div>
                <div className="hi"><div className="hi-n">Aluguel sala</div><div className="hi-m"><span>10/05</span><span className="hi-a">R$ 3.200</span></div></div>
                <div className="hi"><div className="hi-n">Fornecedor Silva</div><div className="hi-m"><span>15/05</span><span className="hi-a">R$ 1.240</span></div></div>
                <div className="hi"><div className="hi-n">Folha de pagamento</div><div className="hi-m"><span>20/05</span><span className="hi-a">R$ 18.400</span></div></div>
                <div className="hi"><div className="hi-n">Cartão corporativo</div><div className="hi-m"><span>12/05</span><span className="hi-a">R$ 2.180</span></div></div>
              </div>
            </div>
          </div>
        </div>

        <div className="bstrip">
          <div className="ich"><span className="ich-em">📈</span><div className="ich-body"><span className="ich-tag tg-f">Tendência</span><div className="ich-txt">Receita em crescimento consistente: +8%, +10%, +12% nos últimos 3 meses</div></div></div>
          <div className="ich"><span className="ich-em">💡</span><div className="ich-body"><span className="ich-tag tg-f">Insight</span><div className="ich-txt">Internet +15% em 3 meses — contrato vence em 90 dias, boa janela para renegociar</div></div></div>
          <div className="ich"><span className="ich-em">⚠️</span><div className="ich-body"><span className="ich-tag tg-s">Atenção</span><div className="ich-txt">Despesas crescendo 7% vs. receita 12% — margem em melhora mas custo fixo subindo</div></div></div>
          <div className="nums-chip" onClick={() => setTab('relatorios')}>
            <div className="nums-head">📊 KPIs do mês</div>
            <div className="nums-row">
              <div className="nkpi"><span className="nv">543,8K</span><span className="nl">Faturamento</span><span className="nd up">↑ 12%</span></div>
              <div className="nkpi"><span className="nv">42,5%</span><span className="nl">Margem</span><span className="nd up">↑ 2,1pp</span></div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
