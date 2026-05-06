import { useState } from 'react'
import { useAppStore } from '../../store/appStore'

type Tab = 'gantt' | 'hoje' | 'pendentes' | 'config'

export default function AgendaRoom() {
  const { go, approve, snooze } = useAppStore()
  const [tab, setTab] = useState<Tab>('gantt')
  const decisions = useAppStore(s => s.decisions)
const agd1Status = decisions['agd1']?.status ?? 'pending'

  return (
    <div>
      <div className="rh">
        <div className="rav">📅</div>
        <div><div className="rn">Agenda</div><div className="rd">Reuniões, rotinas e planejamento semanal</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }}>+ Novo evento</button>
        </div>
      </div>
      <div className="room-grid">

        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph"><span className="ph-ttl">Mesa de Trabalho</span><span className="ph-cnt">5 eventos hoje</span></div>
          <div className="rtabs" id="agTabs">
            {([['gantt','Visão Mensal'],['hoje','Hoje'],['pendentes','Pendentes'],['config','Config']] as [Tab, string][]).map(([t, label]) => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>{label}</div>
            ))}
          </div>
          <div className="pb">

            {/* GANTT */}
            <div className={`tc${tab === 'gantt' ? ' on' : ''}`} id="ag-gantt">
              <div className="gantt">
                <div className="gantt-header">
                  <div className="gantt-wk">6–12 Mai</div>
                  <div className="gantt-wk">13–19 Mai</div>
                  <div className="gantt-wk">20–26 Mai</div>
                  <div className="gantt-wk">27–5 Jun</div>
                </div>
                {[
                  { label: '🛒 Compras', blocks: [
                    { left: '0%', width: '20%', bg: '#818cf8', text: 'Cotação mensal' },
                    { left: '0%', width: '6%', bg: 'rgba(239,68,68,.7)', text: 'Toner' },
                  ]},
                  { label: '📊 Financeiro', blocks: [
                    { left: '3%', width: '4%', bg: 'var(--att)', text: 'Boleto' },
                    { left: '74%', width: '16%', bg: '#34d399', text: 'Fechamento' },
                  ]},
                  { label: '📅 Agenda', blocks: [
                    { left: '6%', width: '4%', bg: '#fb923c', text: 'NF-e' },
                    { left: '26%', width: '4%', bg: 'rgba(251,146,60,.6)', text: 'Fornec.' },
                    { left: '37%', width: '4%', bg: 'rgba(251,146,60,.6)', text: 'Fech. Qua' },
                  ]},
                  { label: '✍️ Docs', blocks: [
                    { left: '0%', width: '4%', bg: '#f472b6', text: 'Proposta Q2' },
                    { left: '0%', width: '30%', bg: 'rgba(244,114,182,.45)', text: 'Handover Alpha' },
                  ]},
                  { label: '🎯 Estratégia', blocks: [
                    { left: '0%', width: '13%', bg: '#fbbf24', text: 'Análise Y' },
                    { left: '47%', width: '22%', bg: 'rgba(251,191,36,.5)', text: 'Relatório Q2' },
                  ]},
                  { label: '👥 Clientes', blocks: [
                    { left: '0%', width: '6%', bg: '#2dd4bf', text: 'Máq. Pesada' },
                    { left: '6%', width: '4%', bg: 'rgba(45,212,191,.5)', text: 'TechFarm' },
                    { left: '50%', width: '10%', bg: 'rgba(45,212,191,.4)', text: 'Renovações' },
                  ]},
                ].map(row => (
                  <div key={row.label} className="gantt-row">
                    <div className="gantt-label">{row.label}</div>
                    <div className="gantt-track">
                      <div className="gantt-today" style={{ left: '0%' }} />
                      <div className="gantt-divider" style={{ left: '25%' }} />
                      <div className="gantt-divider" style={{ left: '50%' }} />
                      <div className="gantt-divider" style={{ left: '75%' }} />
                      {row.blocks.map((b, i) => (
                        <div key={i} className="gantt-block" style={{ left: b.left, width: b.width, background: b.bg }}>{b.text}</div>
                      ))}
                    </div>
                  </div>
                ))}
                <div style={{ marginTop: 9, display: 'flex', alignItems: 'center', gap: 10, fontSize: 10, color: 'var(--mu)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 2, background: 'var(--ac)', borderRadius: 1, display: 'inline-block' }} />Hoje (06/05)</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 8, background: '#818cf8', borderRadius: 2, display: 'inline-block' }} />Em andamento</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 8, background: 'var(--att)', borderRadius: 2, display: 'inline-block' }} />Urgente</span>
                </div>
              </div>
            </div>

            {/* HOJE */}
            <div className={`tc${tab === 'hoje' ? ' on' : ''}`} id="ag-hoje">
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <div className="ev-row"><span className="ev-time">08:00</span><div className="ev-dot" style={{ background: '#818cf8' }} /><div className="ev-body"><div className="ev-title">Revisar cotações de suprimentos</div><div className="ev-desc">Compras — 3 itens pendentes</div></div><span className="bdg bo" style={{ marginTop: 2 }}>Feito</span></div>
                <div className="ev-row"><span className="ev-time">10:00</span><div className="ev-dot" style={{ background: '#34d399' }} /><div className="ev-body"><div className="ev-title">Aprovar NF-e do mês anterior</div><div className="ev-desc">Financeiro — 4 notas para revisão</div></div><span className="bdg bw" style={{ marginTop: 2 }}>Pendente</span></div>
                <div className="ev-row"><span className="ev-time">11:30</span><div className="ev-dot" style={{ background: '#f472b6' }} /><div className="ev-body"><div className="ev-title">Assinar proposta — Cliente Central</div><div className="ev-desc">Documentos — contrato Q2</div></div><span className="bdg bw" style={{ marginTop: 2 }}>Pendente</span></div>
                <div className="ev-row"><span className="ev-time">14:00</span><div className="ev-dot" style={{ background: '#2dd4bf' }} /><div className="ev-body"><div className="ev-title">Follow-up clientes inadimplentes</div><div className="ev-desc">Clientes — 3 contatos</div></div><span className="bdg" style={{ background: 'var(--glass)', color: 'var(--mu2)', marginTop: 2 }}>A fazer</span></div>
                <div className="ev-row"><span className="ev-time">16:30</span><div className="ev-dot" style={{ background: '#fbbf24' }} /><div className="ev-body"><div className="ev-title">Análise de margem — Produto Y</div><div className="ev-desc">Estratégia — relatório semanal</div></div><span className="bdg" style={{ background: 'var(--glass)', color: 'var(--mu2)', marginTop: 2 }}>A fazer</span></div>
              </div>
            </div>

            {/* PENDENTES */}
            <div className={`tc${tab === 'pendentes' ? ' on' : ''}`} id="ag-pendentes">
              <div
                className={['dc warn', agd1Status === 'expanded' ? 'expanded' : '', agd1Status === 'done' ? 'done' : ''].filter(Boolean).join(' ')}
                id="agd1"
              >
                <div className="dcr"><div className="ag"><div className="agd" style={{ background: '#fb923c' }} />Agenda</div><span className="bdg bw">Hoje 10:00</span></div>
                <div className="db"><strong>Aprovar 4 NF-e</strong> do mês de Abril. Valor total: R$ 7.830.</div>
                <div className="dc-act">
                  <button className="btn bp" onClick={() => approve('agd1', 'NF-e aprovadas. Enviadas ao contador.')}>👍 Aprovar</button>
                  <button className="btn bg" onClick={() => snooze('agd1')}>⏰ Depois</button>
                </div>
                <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado — NF-e enviadas ao contador</div>
              </div>
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`} id="ag-config">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Planejamento semanal automático</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 7 }}>Preparar agenda toda:</div>
                  <div className="pills"><span className="pill on">Segunda 07:00</span><span className="pill">Domingo 20:00</span></div>
                </div>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Lembrete diário</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 7 }}>Resumo do dia às:</div>
                  <div className="pills"><span className="pill">06:30</span><span className="pill on">07:30</span><span className="pill">08:00</span></div>
                </div>
              </div>
            </div>

          </div>
        </div>

        <div className="rcol">
          <div className="panel">
            <div className="ph"><span className="ph-ico">📆</span><span className="ph-ttl">Calendários</span><button className="ph-add">＋</button></div>
            <div className="pb">
              <div className="dr-sec">
                <div className="dr-ttl">Hoje — 6 Mai</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginTop: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 5px', borderRadius: 5, opacity: 0.55 }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)', width: 34, flexShrink: 0 }}>08:00</span>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#818cf8', flexShrink: 0 }} />
                    <span style={{ fontSize: 11, color: 'var(--mu2)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Revisar cotações</span>
                    <span style={{ fontSize: 9, background: 'var(--odim)', color: 'var(--ok)', padding: '1px 5px', borderRadius: 3, flexShrink: 0 }}>Feito</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 5px', borderRadius: 5, background: 'rgba(245,158,11,.07)' }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 700, color: 'var(--att)', width: 34, flexShrink: 0 }}>10:00</span>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fb923c', flexShrink: 0 }} />
                    <span style={{ fontSize: 11, color: 'var(--fg)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Aprovar NF-e</span>
                    <span style={{ fontSize: 9, background: 'var(--adm2)', color: 'var(--att)', padding: '1px 5px', borderRadius: 3, flexShrink: 0 }}>Agora</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 5px', borderRadius: 5, background: 'rgba(239,68,68,.06)' }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu2)', width: 34, flexShrink: 0 }}>11:30</span>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#f472b6', flexShrink: 0 }} />
                    <span style={{ fontSize: 11, color: 'var(--fg)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Assinar proposta</span>
                    <span style={{ fontSize: 9, background: 'var(--udim)', color: 'var(--urg)', padding: '1px 5px', borderRadius: 3, flexShrink: 0 }}>Urgente</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 5px', borderRadius: 5 }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)', width: 34, flexShrink: 0 }}>14:00</span>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#34d399', flexShrink: 0 }} />
                    <span style={{ fontSize: 11, color: 'var(--mu2)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Follow-up clientes</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 5px', borderRadius: 5 }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)', width: 34, flexShrink: 0 }}>16:30</span>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fbbf24', flexShrink: 0 }} />
                    <span style={{ fontSize: 11, color: 'var(--mu2)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Análise de margem</span>
                  </div>
                </div>
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Fontes</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 5 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '3px 4px' }}><div style={{ width: 7, height: 7, borderRadius: 2, background: '#818cf8', flexShrink: 0 }} /><span style={{ fontSize: 11, color: 'var(--mu2)' }}>Google Calendar</span><span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--ok)' }}>●</span></div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '3px 4px' }}><div style={{ width: 7, height: 7, borderRadius: 2, background: '#34d399', flexShrink: 0 }} /><span style={{ fontSize: 11, color: 'var(--mu2)' }}>Calendário Empresa</span><span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--ok)' }}>●</span></div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '3px 4px' }}><div style={{ width: 7, height: 7, borderRadius: 2, background: '#f472b6', flexShrink: 0 }} /><span style={{ fontSize: 11, color: 'var(--mu2)' }}>Feriados BR</span><span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--ok)' }}>●</span></div>
                </div>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="ph"><span className="ph-ico">🕐</span><span className="ph-ttl">Próximos eventos</span></div>
            <div className="pb">
              <div className="dr-sec">
                <div className="hi"><div className="hi-n">Aprovar NF-e — 4 notas</div><div className="hi-m"><span>Hoje 10:00</span><span style={{ color: 'var(--att)' }}>Pendente</span></div></div>
                <div className="hi"><div className="hi-n">Assinar proposta Cliente Central</div><div className="hi-m"><span>Hoje 11:30</span><span style={{ color: 'var(--att)' }}>Pendente</span></div></div>
                <div className="hi"><div className="hi-n">Reunião com fornecedores</div><div className="hi-m"><span>Ter 10:00</span></div></div>
                <div className="hi"><div className="hi-n">Fechamento mensal</div><div className="hi-m"><span>Qua 09:00</span></div></div>
                <div className="hi"><div className="hi-n">Análise de margem</div><div className="hi-m"><span>Qui 14:00</span></div></div>
              </div>
            </div>
          </div>
        </div>

        <div className="bstrip">
          <div className="ich"><span className="ich-em">📅</span><div className="ich-body"><span className="ich-tag tg-a">Agenda</span><div className="ich-txt">Semana cheia — Ter e Qua têm decisões críticas. Revisar prioridades?</div></div></div>
          <div className="ich"><span className="ich-em">🤝</span><div className="ich-body"><span className="ich-tag tg-c">Clientes</span><div className="ich-txt">Reunião com fornecedores na Ter: 3 itens de cotação pendentes para apresentar</div></div></div>
          <div className="ich"><span className="ich-em">💡</span><div className="ich-body"><span className="ich-tag tg-f">Financeiro</span><div className="ich-txt">Fechamento Qua: DRE precisará de conciliação bancária — preparar dados antes</div></div></div>
          <div className="nums-chip">
            <div className="nums-head">⚙️ Rotinas ativas</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--ok)', flexShrink: 0 }} /><span style={{ color: 'var(--mu2)' }}>Planejamento semanal</span><span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>Seg 07:00</span></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--ok)', flexShrink: 0 }} /><span style={{ color: 'var(--mu2)' }}>Resumo diário</span><span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>07:30</span></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--ok)', flexShrink: 0 }} /><span style={{ color: 'var(--mu2)' }}>Relatório semanal</span><span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>Sex 08:00</span></div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
