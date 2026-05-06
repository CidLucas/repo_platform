import { useAppStore } from '../../store/appStore'

function DecisionCard({
  id,
  className,
  children,
}: {
  id: string
  className: string
  children: React.ReactNode
}) {
  const status = useAppStore(s => s.decisions[id]?.status ?? 'pending')
  const dcClass = [
    'dc',
    className,
    status === 'expanded' ? 'expanded' : '',
    status === 'done' ? 'done' : '',
    status === 'rejected' ? 'done' : '',
    status === 'snoozed' ? '' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div
      className={dcClass}
      id={id}
      style={status === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
    >
      {children}
    </div>
  )
}

export default function HomePage() {
  const { toggleDc, approve, snooze, go, pendingCount } = useAppStore()
  const decisions = useAppStore(s => s.decisions)

  const cntText =
    pendingCount === 0 ? 'Tudo resolvido ✓' : `${pendingCount} pendentes`

  return (
    <div className="home-grid">

      <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
        <div className="ph">
          <span className="ph-ico">⚡</span>
          <span className="ph-ttl">Decidir Agora</span>
          <span className="ph-cnt" id="cnt">{cntText}</span>
          <span className="ph-lnk" onClick={() => go('compras', 'Compras')}>Ver todas →</span>
        </div>
        <div className="pb">
          <div className="dl">

            {/* DC1 */}
            <DecisionCard id="dc1" className="urg">
              <div className="dc-row" onClick={() => toggleDc('dc1')}>
                <div className="ag"><div className="agd" style={{ background: '#818cf8' }} />Compras</div>
                <span className="bdg bu">Urgente</span>
                <span className="dc-row-summary"><strong>3 cotações prontas</strong> — Fornecedor Silva, R$ 1.240</span>
                <span className="dt">10:32</span>
                <span className="dc-ok-inline">
                  <svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>
                  Aprovado
                </span>
                <span className="dc-chev">▶</span>
              </div>
              <div className="dc-expand">
                <div className="db"><strong>3 cotações prontas.</strong> Recomendação: Fornecedor Silva, entrega 2 dias, <strong>R$ 1.240</strong>.</div>
                <ul className="dbl">
                  <li>Toner HP 107A — estoque crítico (1 dia)</li>
                  <li>Papel A4 — estoque baixo (5 dias)</li>
                  <li>Café — estoque baixo (2 dias)</li>
                </ul>
                <div className="dc-act">
                  <button className="btn bp" onClick={() => approve('dc1', 'Compras aprovadas. Pedido com Fornecedor Silva.')}>👍 Aprovar</button>
                  <button className="btn bs" onClick={() => go('compras', 'Compras')}>👁 Ver</button>
                  <button className="btn bg" onClick={() => snooze('dc1')}>⏰ Depois</button>
                </div>
                <div className="dc-ins"><span>💡</span>Silva 15% mais caro, mas 0 atrasos em 6 meses vs. Gamma (2 atrasos).</div>
                <div className="dc-ok">
                  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>
                  {decisions['dc1']?.status === 'rejected'
                    ? 'Rejeitado — Blu não vai sugerir novamente'
                    : 'Aprovado — pedido com Fornecedor Silva'}
                </div>
              </div>
            </DecisionCard>

            {/* DC2 */}
            <DecisionCard id="dc2" className="warn">
              <div className="dc-row" onClick={() => toggleDc('dc2')}>
                <div className="ag"><div className="agd" style={{ background: '#34d399' }} />Financeiro</div>
                <span className="bdg bw">Amanhã</span>
                <span className="dc-row-summary"><strong>Boleto Claro Empresas</strong> — R$ 847,50 vence amanhã</span>
                <span className="dt">09:15</span>
                <span className="dc-ok-inline">
                  <svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>
                  Agendado
                </span>
                <span className="dc-chev">▶</span>
              </div>
              <div className="dc-expand">
                <div className="db"><strong>Boleto Claro Empresas</strong> vence amanhã. <strong>R$ 847,50</strong>. Itaú: R$ 12.340 disponível.</div>
                <ul className="dbl">
                  <li>Vencimento: 06/05 · Conta Itaú 0001</li>
                </ul>
                <div className="dc-act">
                  <button className="btn bp" onClick={() => approve('dc2', 'Pagamento agendado. R$ 847,50 para 06/05.')}>👍 Agendar</button>
                  <button className="btn bg" onClick={() => snooze('dc2')}>⏰ Depois</button>
                </div>
                <div className="dc-ok">
                  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>
                  Agendado — Itaú · 06/05
                </div>
              </div>
            </DecisionCard>

            {/* DC3 */}
            <DecisionCard id="dc3" className="warn">
              <div className="dc-row" onClick={() => toggleDc('dc3')}>
                <div className="ag"><div className="agd" style={{ background: '#818cf8' }} />Compras</div>
                <span className="bdg bw">2 dias</span>
                <span className="dc-row-summary"><strong>Estoque de café</strong> crítico — Café do Sul, 3 kg, R$ 282</span>
                <span className="dt">08:47</span>
                <span className="dc-ok-inline">
                  <svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>
                  Aprovado
                </span>
                <span className="dc-chev">▶</span>
              </div>
              <div className="dc-expand">
                <div className="db"><strong>Estoque de café</strong> crítico. Café do Sul: 3 kg, <strong>R$ 282</strong> (★★★★☆).</div>
                <div className="dc-act">
                  <button className="btn bp" onClick={() => approve('dc3', 'Café do Sul — 3 kg autorizado.')}>👍 Aprovar</button>
                  <button className="btn bg" onClick={() => snooze('dc3')}>⏰ Depois</button>
                </div>
                <div className="dc-ok">
                  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>
                  Aprovado — Café do Sul
                </div>
              </div>
            </DecisionCard>

          </div>
        </div>
      </div>

      <div className="rcol">
        <div className="panel">
          <div className="ph">
            <span className="ph-ico">📋</span>
            <span className="ph-ttl">Plano de Hoje</span>
            <span className="ph-lnk" onClick={() => go('agenda', 'Agenda')}>Agenda →</span>
          </div>
          <div className="pb">
            <div className="plano-list">
              <div className="pl-item"><span className="pl-t">08:00</span><div className="pl-d" style={{ background: '#818cf8' }} /><span className="pl-txt">Revisar cotações de suprimentos</span></div>
              <div className="pl-item"><span className="pl-t">10:00</span><div className="pl-d" style={{ background: '#34d399' }} /><span className="pl-txt">Aprovar NF-e</span></div>
              <div className="pl-item"><span className="pl-t">11:30</span><div className="pl-d" style={{ background: '#f472b6' }} /><span className="pl-txt">Assinar proposta — Cliente Central</span></div>
              <div className="pl-item"><span className="pl-t">14:00</span><div className="pl-d" style={{ background: '#2dd4bf' }} /><span className="pl-txt">Follow-up clientes</span></div>
              <div className="pl-item"><span className="pl-t">16:30</span><div className="pl-d" style={{ background: '#fbbf24' }} /><span className="pl-txt">Análise de margem</span></div>
            </div>
          </div>
        </div>
        <div className="panel">
          <div className="ph">
            <span className="ph-ico">🔮</span>
            <span className="ph-ttl">Visão da Semana</span>
          </div>
          <div className="pb">
            <div className="semana-list">
              <div className="sw-item"><span className="sw-day today">Seg</span><span className="sw-desc">Hoje — cotações + boleto</span><span className="sw-cnt sw-h">5</span></div>
              <div className="sw-item"><span className="sw-day">Ter</span><span className="sw-desc">Fornecedores — 3 pendentes</span><span className="sw-cnt sw-h">2</span></div>
              <div className="sw-item"><span className="sw-day">Qua</span><span className="sw-desc">Fechamento mensal</span><span className="sw-cnt sw-h">1</span></div>
              <div className="sw-item"><span className="sw-day">Qui</span><span className="sw-desc">Análise de margem</span><span className="sw-cnt sw-ok">✓</span></div>
              <div className="sw-item"><span className="sw-day">Sex</span><span className="sw-desc">Relatório semanal</span><span className="sw-cnt sw-ok">✓</span></div>
            </div>
          </div>
        </div>
      </div>

      <div className="bstrip">
        <div className="ich"><span className="ich-em">📈</span><div className="ich-body"><span className="ich-tag tg-c">Clientes</span><div className="ich-txt">Cliente Central +40% este mês — considere desconto de fidelidade</div></div></div>
        <div className="ich"><span className="ich-em">⏱️</span><div className="ich-body"><span className="ich-tag tg-s">Compras</span><div className="ich-txt">2 fornecedores com prazo crescendo: Max (+3d) e Gamma (+2d)</div></div></div>
        <div className="ich"><span className="ich-em">💰</span><div className="ich-body"><span className="ich-tag tg-f">Financeiro</span><div className="ich-txt">Internet +15% em 3 meses — contrato vence em 90 dias</div></div></div>
        <div className="nums-chip" onClick={() => go('financeiro', 'Financeiro')}>
          <div className="nums-head">📊 Números <span style={{ marginLeft: 'auto', opacity: 0.45 }}>→</span></div>
          <div className="nums-row">
            <div className="nkpi"><span className="nv">543,8K</span><span className="nl">Faturamento</span><span className="nd up">↑ 12%</span></div>
            <div className="nkpi"><span className="nv">42,5%</span><span className="nl">Margem</span><span className="nd up">↑ 2,1pp</span></div>
            <div className="nkpi"><span className="nv">313</span><span className="nl">Clientes</span><span className="nd up">↑ 23</span></div>
          </div>
        </div>
      </div>

    </div>
  )
}
