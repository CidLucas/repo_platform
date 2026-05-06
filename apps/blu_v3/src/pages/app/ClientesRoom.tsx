import { useState } from 'react'
import { useAppStore } from '../../store/appStore'

type Tab = 'followup' | 'ativos' | 'historico' | 'config'

const CLIENTS = [
  { initials: 'MC', name: 'Grupo Máquina Central', val: 'R$ 42K/mês', dot: '#818cf8', health: 95 },
  { initials: 'CA', name: 'Construtora Alvo', val: 'R$ 28K/mês', dot: '#34d399', health: 78 },
  { initials: 'RS', name: 'Rede Supri', val: 'R$ 19K/mês', dot: '#fbbf24', health: 61 },
  { initials: 'FC', name: 'Farmácias Central', val: 'R$ 14K/mês', dot: '#f472b6', health: 88 },
  { initials: 'TL', name: 'TechLine Distribuidora', val: 'R$ 8K/mês', dot: '#2dd4bf', health: 45 },
]

export default function ClientesRoom() {
  const { go, approve, reject, snooze, toggleDc } = useAppStore()
  const decisions = useAppStore(s => s.decisions)
  const [tab, setTab] = useState<Tab>('followup')

  const getStatus = (id: string) => decisions[id]?.status ?? 'pending'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="rh">
        <div className="rav">👥</div>
        <div><div className="rn">Clientes</div><div className="rd">CRM, follow-up e relacionamento</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }}>+ Novo contato</button>
        </div>
      </div>
      <div className="room-grid">

        {/* MAIN PANEL */}
        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph"><span className="ph-ttl">Mesa de Trabalho</span></div>
          <div className="rtabs">
            {(['followup', 'ativos', 'historico', 'config'] as Tab[]).map(t => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>
                {t === 'followup' ? <>Follow-up <span className="tbdg">2</span></> :
                 t === 'ativos' ? 'Ativos' :
                 t === 'historico' ? 'Histórico' : 'Config'}
              </div>
            ))}
          </div>
          <div className="pb">

            {/* FOLLOW-UP */}
            <div className={`tc${tab === 'followup' ? ' on' : ''}`}>
              <div className="dl">

                <div
                  className={['dc urg', getStatus('cl1') === 'expanded' ? 'expanded' : '', getStatus('cl1') === 'done' || getStatus('cl1') === 'rejected' ? 'done' : ''].filter(Boolean).join(' ')}
                  style={getStatus('cl1') === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
                >
                  <div className="dc-row" onClick={() => toggleDc('cl1')}>
                    <div className="ag"><div className="agd" style={{ background: '#818cf8' }} />Clientes</div>
                    <span className="bdg bu">Risco</span>
                    <span className="dc-row-summary"><strong>Grupo Máquina Central</strong> — pedidos caíram 30% desde fev</span>
                    <span className="dt">10:15</span>
                    <span className="dc-ok-inline"><svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Resolvido</span>
                    <span className="dc-chev">▶</span>
                  </div>
                  <div className="dc-expand">
                    <div className="db"><strong>Grupo Máquina Central</strong> — pedidos caíram de R$ 55K para R$ 38K/mês. Último contato: 22 dias.</div>
                    <ul className="dbl">
                      <li>Contrato vence em 45 dias — sem renovação em curso</li>
                      <li>3 tickets de suporte abertos sem resposta</li>
                      <li>NPS caiu de 9 para 6 no último trimestre</li>
                    </ul>
                    <div className="dc-act">
                      <button className="btn bp" onClick={() => approve('cl1', 'Follow-up urgente agendado com Grupo Máquina Central.')}>📞 Agendar reunião</button>
                      <button className="btn bs">📋 Ver conta</button>
                      <button className="btn bg" onClick={() => snooze('cl1')}>⏰ Depois</button>
                    </div>
                    <div className="dc-ins"><span>💡</span>Clientes com queda de 30%+ têm 72% de probabilidade de churn nos próximos 60 dias.</div>
                    <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Follow-up agendado</div>
                  </div>
                </div>

                <div
                  className={['dc warn', getStatus('cl2') === 'expanded' ? 'expanded' : '', getStatus('cl2') === 'done' || getStatus('cl2') === 'rejected' ? 'done' : ''].filter(Boolean).join(' ')}
                  style={getStatus('cl2') === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
                >
                  <div className="dc-row" onClick={() => toggleDc('cl2')}>
                    <div className="ag"><div className="agd" style={{ background: '#2dd4bf' }} />Clientes</div>
                    <span className="bdg bw">Oportunidade</span>
                    <span className="dc-row-summary"><strong>Construtora Alvo</strong> +40% este mês — oferecer desconto fidelidade</span>
                    <span className="dt">09:30</span>
                    <span className="dc-ok-inline"><svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Aprovado</span>
                    <span className="dc-chev">▶</span>
                  </div>
                  <div className="dc-expand">
                    <div className="db"><strong>Construtora Alvo</strong> cresceu de R$ 20K para R$ 28K/mês. NPS 9,2. Momento ideal para fechar contrato anual.</div>
                    <ul className="dbl">
                      <li>Volume: +40% em 30 dias</li>
                      <li>Desconto 8% anual → economia de R$ 2.688 para eles</li>
                      <li>Previsão: R$ 336K ARR</li>
                    </ul>
                    <div className="dc-act">
                      <button className="btn bp" onClick={() => approve('cl2', 'Proposta de contrato anual enviada para Construtora Alvo.')}>📄 Enviar proposta</button>
                      <button className="btn bs">💬 Conversar</button>
                      <button className="btn bg" onClick={() => reject('cl2')}>Ignorar</button>
                    </div>
                    <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Proposta enviada</div>
                  </div>
                </div>

                {/* Em andamento */}
                <div style={{ padding: '10px 11px', borderTop: '1px solid var(--gb)', marginTop: 6 }}>
                  <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 8 }}>Em acompanhamento</div>
                  {[
                    { name: 'Rede Supri', action: 'Proposta enviada — aguardando resposta', days: '3 dias', color: 'var(--att)' },
                    { name: 'Farmácias Central', action: 'Renovação em negociação', days: '7 dias', color: 'var(--ok)' },
                    { name: 'TechLine', action: 'Risco de churn — contato amanhã', days: '1 dia', color: 'var(--urg)' },
                  ].map((f, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '6px 0', borderBottom: '1px solid var(--gb)', fontSize: 12 }}>
                      <span style={{ fontWeight: 600, flex: 1 }}>{f.name}</span>
                      <span style={{ color: 'var(--mu)', fontSize: 11.5, flex: 2 }}>{f.action}</span>
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: f.color, flexShrink: 0 }}>{f.days}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ATIVOS */}
            <div className={`tc${tab === 'ativos' ? ' on' : ''}`}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 7, marginBottom: 12 }}>
                <div className="kpi-cell"><div className="kpi-lbl">Clientes ativos</div><div className="kpi-val">313</div><div className="kpi-d up">↑ 23 este mês</div></div>
                <div className="kpi-cell"><div className="kpi-lbl">Receita mensal</div><div className="kpi-val">543K</div><div className="kpi-d up">↑ 12%</div></div>
                <div className="kpi-cell"><div className="kpi-lbl">NPS médio</div><div className="kpi-val">8,7</div><div className="kpi-d up">↑ 0,3</div></div>
              </div>
              <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 8 }}>Top 5 por receita</div>
              {CLIENTS.map((c, i) => (
                <div key={i} className="cli-row">
                  <div className="cli-av" style={{ background: `${c.dot}22`, color: c.dot }}>{c.initials}</div>
                  <span className="cli-name">{c.name}</span>
                  <span className="cli-val">{c.val}</span>
                  <div className="cli-dot" style={{ background: c.health >= 75 ? 'var(--ok)' : c.health >= 55 ? 'var(--att)' : 'var(--urg)' }} />
                </div>
              ))}
            </div>

            {/* HISTÓRICO */}
            <div className={`tc${tab === 'historico' ? ' on' : ''}`}>
              {[
                { name: 'Grupo Máquina Central', action: 'Reunião de kick-off', date: '22 Abr', status: 'Realizada', ok: true },
                { name: 'Construtora Alvo', action: 'Proposta Q2 enviada', date: '18 Abr', status: 'Aprovada', ok: true },
                { name: 'Rede Supri', action: 'Follow-up por e-mail', date: '15 Abr', status: 'Sem resposta', ok: false },
                { name: 'Farmácias Central', action: 'Negociação de renovação', date: '10 Abr', status: 'Em curso', ok: null },
                { name: 'TechLine', action: 'Alerta de churn disparado', date: '08 Abr', status: 'Pendente', ok: false },
                { name: 'Grupo Máquina Central', action: 'Suporte: ticket #1247', date: '05 Abr', status: 'Resolvido', ok: true },
              ].map((h, i) => (
                <div key={i} className="hi">
                  <div className="hi-n">{h.name} — {h.action}</div>
                  <div className="hi-m">
                    <span>{h.date}</span>
                    <span style={{ color: h.ok === true ? 'var(--ok)' : h.ok === false ? 'var(--urg)' : 'var(--att)' }}>{h.status}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Frequência de alertas de churn</div>
                  <div className="pills"><span className="pill on">Semanal</span><span className="pill">Quinzenal</span><span className="pill">Mensal</span></div>
                </div>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Integração CRM</div>
                  <div style={{ display: 'flex', gap: 7 }}>
                    <span className="pill on">HubSpot</span><span className="pill">Pipedrive</span><span className="pill">RD Station</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="rcol">
          <div className="panel">
            <div className="ph"><span className="ph-ico">📊</span><span className="ph-ttl">Segmentos</span></div>
            <div className="pb">
              <div className="dr-sec">
                {[
                  { name: 'Premium (>R$30K)', count: 12, pct: 71, color: '#818cf8' },
                  { name: 'Standard (R$10-30K)', count: 87, pct: 58, color: 'var(--ac)' },
                  { name: 'Básico (<R$10K)', count: 214, pct: 44, color: 'var(--mu)' },
                ].map((s, i) => (
                  <div key={i} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: 'var(--mu2)', marginBottom: 3 }}>
                      <span>{s.name}</span>
                      <span style={{ fontFamily: 'var(--mono)', color: 'var(--mu)' }}>{s.count} clientes</span>
                    </div>
                    <div style={{ background: 'var(--gb)', borderRadius: 2, height: 4 }}>
                      <div style={{ background: s.color, width: `${s.pct}%`, height: '100%', borderRadius: 2 }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Saúde da carteira</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11.5 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Saudável</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>74%</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Em risco</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--att)' }}>19%</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Crítico</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--urg)' }}>7%</span></div>
                </div>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="ph"><span className="ph-ico">📅</span><span className="ph-ttl">Próximos follow-ups</span></div>
            <div className="pb">
              <div className="dr-sec">
                {[
                  { name: 'TechLine', day: 'Amanhã', time: '10:00', color: 'var(--urg)' },
                  { name: 'Rede Supri', day: 'Qua', time: '14:30', color: 'var(--att)' },
                  { name: 'Farmácias Central', day: 'Sex', time: '09:00', color: 'var(--ok)' },
                ].map((f, i) => (
                  <div key={i} className="ev-row">
                    <div className="ev-time">{f.time}</div>
                    <div className="ev-dot" style={{ background: f.color }} />
                    <div className="ev-body">
                      <div className="ev-title">{f.name}</div>
                      <div className="ev-desc">{f.day}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip">
          <div className="ich"><span className="ich-em">⚠️</span><div className="ich-body"><span className="ich-tag tg-d">Clientes</span><div className="ich-txt">TechLine com probabilidade de churn 72% — intervir nos próximos 7 dias</div></div></div>
          <div className="ich"><span className="ich-em">📈</span><div className="ich-body"><span className="ich-tag tg-d">Oportunidade</span><div className="ich-txt">Construtora Alvo +40% — momento ideal para proposta de contrato anual</div></div></div>
          <div className="ich"><span className="ich-em">🔄</span><div className="ich-body"><span className="ich-tag tg-d">Renovações</span><div className="ich-txt">3 contratos vencem em 60 dias — iniciar negociações preventivas</div></div></div>
          <div className="nums-chip">
            <div className="nums-head">👥 Carteira</div>
            <div className="nums-row">
              <div className="nkpi"><span className="nv" style={{ fontSize: 18 }}>313</span><span className="nl">ativos</span></div>
              <div className="nkpi"><span className="nv" style={{ fontSize: 18, color: 'var(--ok)' }}>8,7</span><span className="nl">NPS</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
