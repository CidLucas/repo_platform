import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

type SimState = 'idle' | 'approved' | 'later'

export default function LandingPage() {
  const navigate = useNavigate()
  const pricingRef = useRef<HTMLElement>(null)
  const [simState, setSimState] = useState<SimState>('idle')

  function scrollToPricing() {
    if (pricingRef.current) {
      window.scrollTo({ top: pricingRef.current.offsetTop - 60, behavior: 'smooth' })
    }
  }

  return (
    <div className="lp-root">
      {/* NAV */}
      <nav className="lp-nav">
        <div className="lp-logo">
          <div className="lp-logo-mark">B</div>
          <span className="lp-logo-name">blu</span>
          <span className="lp-logo-sub">by deep blue</span>
        </div>
        <div className="lp-nav-links">
          <a
            href="#screens"
            onClick={e => {
              e.preventDefault()
              const el = document.getElementById('screens')
              if (el) window.scrollTo({ top: el.offsetTop - 60, behavior: 'smooth' })
            }}
          >
            Produto
          </a>
          <a
            href="#como-funciona"
            onClick={e => {
              e.preventDefault()
              const el = document.getElementById('como-funciona')
              if (el) window.scrollTo({ top: el.offsetTop - 60, behavior: 'smooth' })
            }}
          >
            Como funciona
          </a>
          <a href="#precos" onClick={scrollToPricing}>Preços</a>
        </div>
        <button className="lp-nav-cta" onClick={() => navigate('/onboarding?mode=login')}>
          Ir para o app
        </button>
      </nav>

      {/* HERO */}
      <section className="lp-hero">
        <div className="lp-eyebrow">Escritório virtual com IA para empresas brasileiras</div>
        <h1 className="lp-h1">
          Comece a semana <em>sabendo</em><br />o que importa
        </h1>
        <p className="lp-sub">
          Um bureau de agentes de IA que trabalha para você — cuida das cotações,
          dos boletos, dos clientes, da estratégia — e espera sua aprovação antes de agir.
        </p>
        <div className="lp-ctas">
          <button className="lp-cta-primary" onClick={() => navigate('/onboarding')}>
            Criar conta grátis
          </button>
          <button className="lp-cta-ghost" onClick={scrollToPricing}>
            Ver planos ↓
          </button>
        </div>

        {/* INTERACTIVE SIM CARD */}
        <div className="lp-sim-wrap" id="screens">
          <div className="lp-sim-card">
            <div className="lp-sim-top">
              <div className="lp-sim-agent">
                <span className="lp-sim-dot" />
                Agente de Compras
              </div>
              <span className="lp-sim-badge">Decidir agora</span>
            </div>
            <div className="lp-sim-body">
              <strong>3 cotações prontas.</strong> Fornecedor Silva, R$ 1.240 (2 unidades Toner HP 107A). Prazo: 2 dias. Alternativa Gamma: R$ 1.180, prazo 5 dias.
            </div>
            {simState === 'idle' && (
              <div className="lp-sim-actions">
                <button className="lp-sim-btn-p" onClick={() => setSimState('approved')}>👍 Aprovar Silva</button>
                <button className="lp-sim-btn-g" onClick={() => alert('Comparativo:\n\nSilva: R$ 1.240 · 2 dias · ★★★★★\nGamma: R$ 1.180 · 5 dias · ★★★☆☆\n\nRecomendação: Silva (menor risco de atraso)')}>👁 Ver comparativo</button>
                <button className="lp-sim-btn-g" onClick={() => setSimState('later')}>⏰ Depois</button>
              </div>
            )}
            {simState === 'approved' && (
              <div className="lp-sim-feedback">
                <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
                Pedido enviado. Silva confirmou recebimento. Agente anotou a preferência.
              </div>
            )}
            {simState === 'later' && (
              <div className="lp-sim-later">⏰ Adiado para amanhã, 08:00</div>
            )}
          </div>
        </div>
      </section>

      {/* COMO FUNCIONA */}
      <section className="lp-steps" id="como-funciona">
        <h2 className="lp-section-h">Do caos ao controle em três passos</h2>
        <div className="lp-steps-grid">
          <div className="lp-step">
            <div className="lp-step-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
              </svg>
            </div>
            <h3>Conecte suas fontes</h3>
            <p>ERP, banco, planilhas, agenda. Seus dados já existem — o Blu só precisa de acesso.</p>
          </div>
          <div className="lp-step">
            <div className="lp-step-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" />
              </svg>
            </div>
            <h3>Os agentes trabalham</h3>
            <p>Cada agente cuida do seu domínio — compras, finanças, clientes — e prepara as decisões para você.</p>
          </div>
          <div className="lp-step">
            <div className="lp-step-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <rect x="3" y="3" width="18" height="18" rx="3" />
                <polyline points="9 12 11 14 15 10" />
              </svg>
            </div>
            <h3>Você aprova e segue</h3>
            <p>Nada acontece sem seu aval. Uma aprovação, e o agente executa — com o contexto certo, no momento certo.</p>
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section className="lp-pricing" id="precos" ref={pricingRef}>
        <h2 className="lp-section-h">Planos simples, sem surpresas</h2>
        <div className="lp-pricing-grid">
          {[
            {
              name: 'Starter', price: 'R$ 297', period: '/mês',
              desc: 'Para quem está começando.',
              features: ['3 agentes ativos', '500 aprovações/mês', '2 integrações', 'Suporte por e-mail'],
              cta: 'Começar grátis', primary: false,
            },
            {
              name: 'Pro', price: 'R$ 697', period: '/mês',
              desc: 'Para negócios em crescimento.',
              features: ['Todos os agentes', 'Aprovações ilimitadas', '10 integrações', 'Suporte prioritário', 'Relatórios avançados'],
              cta: 'Começar grátis', primary: true,
            },
            {
              name: 'Enterprise', price: 'Sob consulta', period: '',
              desc: 'Para operações complexas.',
              features: ['Multi-empresa', 'Agentes customizados', 'Integrações ilimitadas', 'SLA dedicado', 'Onboarding guiado'],
              cta: 'Falar com vendas', primary: false,
            },
          ].map(p => (
            <div key={p.name} className={`lp-plan ${p.primary ? 'lp-plan-primary' : ''}`}>
              <div className="lp-plan-name">{p.name}</div>
              <div className="lp-plan-price">{p.price}<span>{p.period}</span></div>
              <div className="lp-plan-desc">{p.desc}</div>
              <ul className="lp-plan-features">
                {p.features.map(f => <li key={f}>✓ {f}</li>)}
              </ul>
              <button
                className={p.primary ? 'lp-cta-primary' : 'lp-cta-ghost'}
                onClick={() => navigate('/onboarding')}
              >
                {p.cta}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="lp-footer">
        <div className="lp-footer-logo">
          <div className="lp-logo-mark" style={{ width: 20, height: 20, fontSize: 10 }}>B</div>
          <span style={{ fontSize: 13, fontWeight: 600 }}>blu</span>
        </div>
        <div className="lp-footer-copy">© 2026 Deep Blue · blu é o escritório virtual com IA para empresas brasileiras</div>
        <div className="lp-footer-links">
          <a href="/privacidade">Privacidade</a>
          <a href="/termos">Termos</a>
          <a href="/lgpd">LGPD</a>
        </div>
      </footer>
    </div>
  )
}
