import { useAppStore } from '../../store/appStore'

const EVENTS = [
  { ts: '06/05 10:32', agColor: '#818cf8', text: 'Compras — 3 cotações prontas para aprovação', user: 'Agente', status: 'Pendente', st: 'lwrn' },
  { ts: '06/05 09:15', agColor: '#34d399', text: 'Financeiro — boleto Claro detectado, vence amanhã', user: 'Agente', status: 'Pendente', st: 'lwrn' },
  { ts: '06/05 08:00', agColor: '#818cf8', text: 'Compras — verificação semanal de estoque executada', user: 'Agente', status: 'Concluído', st: 'lok' },
  { ts: '05/05 17:23', agColor: '#2dd4bf', text: 'Clientes — Cliente Central +40% detectado este mês', user: 'Agente', status: 'Insight', st: '' },
  { ts: '05/05 16:10', agColor: '#fbbf24', text: 'Estratégia — análise de margem Q1 concluída', user: 'Carlos Lima', status: 'Aprovado', st: 'lok' },
  { ts: '05/05 14:38', agColor: '#f472b6', text: 'Documentos — proposta Q2 gerada e enviada', user: 'Agente', status: 'Concluído', st: 'lok' },
  { ts: '05/05 11:20', agColor: '#34d399', text: 'Financeiro — DRE mensal gerado automaticamente', user: 'Agente', status: 'Concluído', st: 'lok' },
  { ts: '05/05 10:05', agColor: '#818cf8', text: 'Compras — pedido Silva R$ 840 entregue', user: 'Agente', status: 'Concluído', st: 'lok' },
  { ts: '04/05 16:45', agColor: '#fbbf24', text: 'Estratégia — alerta: 2 fornecedores com prazo crescente', user: 'Agente', status: 'Novo', st: 'lwrn' },
  { ts: '04/05 09:30', agColor: '#34d399', text: 'Financeiro — boleto Gamma R$ 234 aprovado por Carlos', user: 'Carlos Lima', status: 'Aprovado', st: 'lok' },
]

export default function AtividadeScreen() {
  const go = useAppStore(s => s.go)

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
            <span className="ph-cnt">Hoje · 10 eventos</span>
          </div>
          <div className="pb">
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {EVENTS.map((e, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, padding: '10px 13px', borderBottom: '1px solid var(--gb)', cursor: 'pointer', transition: 'background .1s' }}
                  onMouseEnter={el => (el.currentTarget.style.background = 'rgba(255,255,255,.025)')}
                  onMouseLeave={el => (el.currentTarget.style.background = '')}
                >
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)', minWidth: 104, paddingTop: 2, flexShrink: 0 }}>{e.ts}</span>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: e.agColor, marginTop: 5, flexShrink: 0 }} />
                  <div style={{ flex: 1, fontSize: 12.5, color: 'var(--mu2)' }}>{e.text}</div>
                  <span style={{ fontSize: 10.5, color: 'var(--mu)', marginRight: 8, flexShrink: 0 }}>{e.user}</span>
                  {e.st && (
                    <span className={`log-st ${e.st}`} style={{ flexShrink: 0 }}>{e.status}</span>
                  )}
                  {!e.st && (
                    <span style={{ fontSize: 9.5, fontWeight: 600, padding: '1.5px 5px', borderRadius: 3, background: 'var(--adim)', color: 'var(--ac)', flexShrink: 0 }}>{e.status}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="rcol">
          <div className="panel">
            <div className="ph"><span className="ph-ico">🤖</span><span className="ph-ttl">Agentes ativos</span></div>
            <div className="pb">
              <div style={{ padding: '7px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  { icon: '🛒', name: 'Compras', count: 3, color: '#818cf8', status: 'Aguardando aprovação' },
                  { icon: '📊', name: 'Financeiro', count: 1, color: '#34d399', status: 'Monitorando' },
                  { icon: '📅', name: 'Agenda', count: 0, color: '#fb923c', status: 'Nada urgente' },
                  { icon: '✍️', name: 'Documentos', count: 0, color: '#f472b6', status: 'Nada urgente' },
                  { icon: '🎯', name: 'Estratégia', count: 2, color: '#fbbf24', status: 'Análise em curso' },
                  { icon: '👥', name: 'Clientes', count: 2, color: '#2dd4bf', status: 'Follow-up pendente' },
                ].map((a, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: '1px solid var(--gb)', cursor: 'pointer' }}
                    onClick={() => go(a.name.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '') as any, a.name)}
                  >
                    <span style={{ fontSize: 14 }}>{a.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, fontWeight: 500 }}>{a.name}</div>
                      <div style={{ fontSize: 10.5, color: 'var(--mu)' }}>{a.status}</div>
                    </div>
                    {a.count > 0 && (
                      <span style={{ background: 'var(--urg)', color: '#fff', fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 8 }}>{a.count}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="ph"><span className="ph-ico">📊</span><span className="ph-ttl">Resumo do dia</span></div>
            <div className="pb">
              <div style={{ padding: '7px 12px', display: 'flex', flexDirection: 'column', gap: 7, fontSize: 11.5 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Decisões pendentes</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--att)' }}>8</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Aprovadas hoje</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>5</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Ações do agente</span><span style={{ fontFamily: 'var(--mono)' }}>23</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Economia IA</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>R$ 640</span></div>
              </div>
            </div>
          </div>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip" style={{ gridColumn: '1/-1', gridRow: 2 }}>
          <div className="ich"><span className="ich-em">🔴</span><div className="ich-body"><span className="ich-tag" style={{ color: 'var(--urg)' }}>Urgente</span><div className="ich-txt">3 decisões de Compras aguardando há mais de 2 horas</div></div></div>
          <div className="ich"><span className="ich-em">🟡</span><div className="ich-body"><span className="ich-tag" style={{ color: 'var(--att)' }}>Atenção</span><div className="ich-txt">Boleto Claro vence amanhã — agendamento pendente</div></div></div>
          <div className="ich"><span className="ich-em">🟢</span><div className="ich-body"><span className="ich-tag" style={{ color: 'var(--ok)' }}>Concluído</span><div className="ich-txt">Estoque verificado — sem rupturas críticas hoje</div></div></div>
          <div className="nums-chip">
            <div className="nums-head">🔔 Hoje</div>
            <div className="nums-row">
              <div className="nkpi"><span className="nv" style={{ fontSize: 18, color: 'var(--att)' }}>8</span><span className="nl">pendentes</span></div>
              <div className="nkpi"><span className="nv" style={{ fontSize: 18, color: 'var(--ok)' }}>5</span><span className="nl">aprovadas</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
