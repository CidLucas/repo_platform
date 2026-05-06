import { useState } from 'react'
import { useAppStore } from '../../store/appStore'

type Tab = 'ativos' | 'rascunhos' | 'arquivados' | 'modelos'

interface DocumentosRoomProps {
  openEditor: (docName: string) => void
}

export default function DocumentosRoom({ openEditor }: DocumentosRoomProps) {
  const { go, approve, snooze } = useAppStore()
  const [tab, setTab] = useState<Tab>('ativos')
  const decisions = useAppStore(s => s.decisions)
  const dd1Status = decisions['dd1']?.status ?? 'pending'

  return (
    <div>
      <div className="rh">
        <div className="rav">✍️</div>
        <div><div className="rn">Documentos</div><div className="rd">Rascunhos, modelos e aprovações</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }}>+ Novo documento</button>
        </div>
      </div>
      <div className="room-grid">

        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph"><span className="ph-ttl">Mesa de Trabalho</span><span className="ph-cnt">1 para assinar</span></div>
          <div className="rtabs" id="dTabs">
            {([['ativos','Ativos'],['rascunhos','Rascunhos'],['arquivados','Arquivados'],['modelos','Modelos']] as [Tab,string][]).map(([t,label]) => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>{label}</div>
            ))}
          </div>
          <div className="pb">

            <div className={`tc${tab === 'ativos' ? ' on' : ''}`} id="d-ativos">
              <div
                className={['dc warn', dd1Status === 'expanded' ? 'expanded' : '', dd1Status === 'done' ? 'done' : ''].filter(Boolean).join(' ')}
                id="dd1"
                style={dd1Status === 'snoozed' ? { opacity: 0.28, pointerEvents: 'none' } : undefined}
              >
                <div className="dcr"><div className="ag"><div className="agd" style={{ background: '#f472b6' }} />Documentos</div><span className="bdg bw">Hoje 11:30</span></div>
                <div className="db"><strong>Proposta Q2 — Cliente Central</strong> aguarda sua assinatura. Valor: <strong>R$ 48.000/mês</strong>.</div>
                <ul className="dbl"><li>Contrato de prestação de serviços — 12 meses</li><li>Desconto de fidelidade incluído (+40% volume)</li></ul>
                <div className="dc-act">
                  <button className="btn bp" onClick={() => approve('dd1', 'Proposta assinada. Cliente Central notificado.')}>✍️ Assinar</button>
                  <button className="btn bs" onClick={() => openEditor('Proposta Q2 — Cliente Central')}>✏️ Editar</button>
                  <button className="btn bg" onClick={() => snooze('dd1')}>⏰ Depois</button>
                </div>
                <div className="dc-ins"><span>💡</span>Cliente Central representa 28% da receita mensal. Renovar o contrato consolida a base.</div>
                <div className="dc-ok"><svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>Assinado — Cliente Central notificado</div>
              </div>
              <div style={{ marginTop: 9, display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div className="doc-row"><span className="doc-icon">📋</span><div className="doc-name">Handover Projeto Alpha</div><span className="doc-date">Em edição</span><span className="doc-status" style={{ background: 'var(--adm2)', color: 'var(--att)' }}>Rascunho</span></div>
                <div className="doc-row"><span className="doc-icon">📝</span><div className="doc-name">Ata reunião fornecedores</div><span className="doc-date">03/05</span><span className="doc-status" style={{ background: 'var(--odim)', color: 'var(--ok)' }}>Aprovado</span></div>
              </div>
            </div>

            <div className={`tc${tab === 'rascunhos' ? ' on' : ''}`} id="d-rascunhos">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div className="doc-row"><span className="doc-icon">✏️</span><div className="doc-name">Handover Projeto Alpha</div><span className="doc-date">Editado hoje</span></div>
                <div className="doc-row"><span className="doc-icon">✏️</span><div className="doc-name">Proposta Fornecedor Novo</div><span className="doc-date">Editado 02/05</span></div>
                <div className="doc-row"><span className="doc-icon">✏️</span><div className="doc-name">Política de Compras v2</div><span className="doc-date">Editado 28/04</span></div>
              </div>
            </div>

            <div className={`tc${tab === 'arquivados' ? ' on' : ''}`} id="d-arquivados">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div className="doc-row"><span className="doc-icon">📁</span><div className="doc-name">Contrato Cliente Central Q1</div><span className="doc-date">Abr 2026</span><span className="doc-status" style={{ background: 'var(--odim)', color: 'var(--ok)' }}>Finalizado</span></div>
                <div className="doc-row"><span className="doc-icon">📁</span><div className="doc-name">Proposta Supplier Beta</div><span className="doc-date">Mar 2026</span><span className="doc-status" style={{ background: 'var(--udim)', color: 'var(--urg)' }}>Recusado</span></div>
                <div className="doc-row"><span className="doc-icon">📁</span><div className="doc-name">Ata reunião anual</div><span className="doc-date">Jan 2026</span><span className="doc-status" style={{ background: 'var(--odim)', color: 'var(--ok)' }}>Finalizado</span></div>
                <div className="doc-row"><span className="doc-icon">📁</span><div className="doc-name">Política de Compras v1</div><span className="doc-date">Dez 2025</span><span className="doc-status" style={{ background: 'var(--glass)', color: 'var(--mu2)' }}>Substituído</span></div>
              </div>
            </div>

            <div className={`tc${tab === 'modelos' ? ' on' : ''}`} id="d-modelos">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div className="doc-row"><span className="doc-icon">🗂️</span><div className="doc-name">Handover de Projeto</div><span className="doc-date">Usado 4×</span><button className="btn bs" style={{ fontSize: 10, padding: '3px 7px' }}>Usar</button></div>
                <div className="doc-row"><span className="doc-icon">🗂️</span><div className="doc-name">Proposta Comercial</div><span className="doc-date">Usado 3×</span><button className="btn bs" style={{ fontSize: 10, padding: '3px 7px' }}>Usar</button></div>
                <div className="doc-row"><span className="doc-icon">🗂️</span><div className="doc-name">Ata de Reunião</div><span className="doc-date">Usado 7×</span><button className="btn bs" style={{ fontSize: 10, padding: '3px 7px' }}>Usar</button></div>
                <div className="doc-row"><span className="doc-icon">🗂️</span><div className="doc-name">Relatório de Entrega</div><span className="doc-date">Usado 2×</span><button className="btn bs" style={{ fontSize: 10, padding: '3px 7px' }}>Usar</button></div>
              </div>
            </div>

          </div>
        </div>

        <div className="rcol">
          <div className="panel">
            <div className="ph"><span className="ph-ico">🗂️</span><span className="ph-ttl">Modelos</span><button className="ph-add">＋</button></div>
            <div className="pb">
              <div className="dr-sec">
                <div className="hi"><div className="hi-n">Handover de Projeto</div><div className="hi-m"><span>Usado 4×</span><span style={{ color: 'var(--ok)' }}>★ Favorito</span></div></div>
                <div className="hi"><div className="hi-n">Proposta Comercial</div><div className="hi-m"><span>Usado 3×</span></div></div>
                <div className="hi"><div className="hi-n">Ata de Reunião</div><div className="hi-m"><span>Usado 7×</span><span style={{ color: 'var(--ok)' }}>★ Favorito</span></div></div>
                <div className="hi"><div className="hi-n">Relatório de Entrega</div><div className="hi-m"><span>Usado 2×</span></div></div>
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Este mês</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11.5 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Documentos criados</span><span style={{ fontFamily: 'var(--mono)' }}>8</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Aprovados</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>6</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--mu)' }}>Taxa aprovação</span><span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>75%</span></div>
                </div>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="ph"><span className="ph-ico">📂</span><span className="ph-ttl">Arquivados recentes</span></div>
            <div className="pb">
              <div className="dr-sec">
                <div className="hi"><div className="hi-n">Contrato Cliente Central Q1</div><div className="hi-m"><span>Abr 2026</span><span style={{ color: 'var(--ok)' }}>Finalizado</span></div></div>
                <div className="hi"><div className="hi-n">Ata reunião anual</div><div className="hi-m"><span>Jan 2026</span><span style={{ color: 'var(--ok)' }}>Finalizado</span></div></div>
                <div className="hi"><div className="hi-n">Proposta Supplier Beta</div><div className="hi-m"><span>Mar 2026</span><span style={{ color: 'var(--urg)' }}>Recusado</span></div></div>
              </div>
            </div>
          </div>
        </div>

        <div className="bstrip">
          <div className="ich"><span className="ich-em">💡</span><div className="ich-body"><span className="ich-tag tg-a">Insight</span><div className="ich-txt">Handover e Relatório de Entrega são 80% similares — unificar em um modelo economiza tempo</div></div></div>
          <div className="ich"><span className="ich-em">📈</span><div className="ich-body"><span className="ich-tag tg-c">Clientes</span><div className="ich-txt">3 propostas este mês, 100% de aprovação — modelo atual está funcionando bem</div></div></div>
          <div className="ich"><span className="ich-em">🔄</span><div className="ich-body"><span className="ich-tag tg-a">Sugestão</span><div className="ich-txt">Auto-salvar rascunhos a cada 30 segundos está ativo — nenhum conteúdo perdido hoje</div></div></div>
          <div className="nums-chip">
            <div className="nums-head">⚙️ Rotinas ativas</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--ok)', flexShrink: 0 }} /><span style={{ color: 'var(--mu2)' }}>Auto-salvar rascunhos</span><span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>30s</span></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--ok)', flexShrink: 0 }} /><span style={{ color: 'var(--mu2)' }}>Backup semanal</span><span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>Seg</span></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}><div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--ok)', flexShrink: 0 }} /><span style={{ color: 'var(--mu2)' }}>Fluxo de aprovação</span><span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)' }}>Ativo</span></div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
