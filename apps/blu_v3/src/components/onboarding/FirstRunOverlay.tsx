import { useState, useEffect, useRef } from 'react'
import { useAuth } from '@blu/auth'
import { useAppStore } from '../../store/appStore'

type ChatMsg = { from: 'bot' | 'user'; text: string }

const STEPS: { bot: string; pills: string[]; spotlight?: string }[] = [
  {
    bot: 'Oi! Acabei de analisar os dados do seu cadastro. Você é o dono aqui, certo? Quem toma as decisões do dia a dia?',
    pills: ['Só eu', 'Eu e um sócio', 'Tenho uma equipe'],
  },
  {
    bot: 'Entendido. Veja ali no menu — escolha qual área você quer que eu monitore primeiro.',
    pills: ['Compras e fornecedores', 'Financeiro e boletos', 'Clientes e vendas'],
    spotlight: 'sidebar',
  },
  {
    bot: 'Ótimo. Quer que eu conecte seus dados automaticamente para começar a monitorar essa área?',
    pills: ['Sim, conectar agora', 'Talvez depois'],
  },
  {
    bot: 'Perfeito, anotei tudo. Seu escritório está pronto. Pode explorar — estarei aqui quando precisar.',
    pills: [],
  },
]

const CONNECTIONS_PILL = 'Sim, conectar agora'
const CONNECTIONS_STEP = 2

interface Props {
  onOpenConnections?: () => void
}

export default function FirstRunOverlay({ onOpenConnections }: Props) {
  const dismissFirstRun = useAppStore(s => s.dismissFirstRun)
  const { user, clientId } = useAuth()
  const dismiss = () => dismissFirstRun(clientId ?? '')
  const [step, setStep] = useState(0)
  const [msgs, setMsgs] = useState<ChatMsg[]>([])
  const [inputVal, setInputVal] = useState('')
  const [done, setDone] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)

  const firstName = user?.email?.split('@')[0]?.split('.')[0] ?? ''
  const displayName = firstName ? firstName.charAt(0).toUpperCase() + firstName.slice(1) : 'você'

  useEffect(() => {
    const greeting = `Oi, ${displayName}! Sou seu agente. Vou te ajudar a configurar seu escritório. Pode ser rápido?`
    setTimeout(() => setMsgs([{ from: 'bot', text: greeting }]), 400)
  }, [displayName])

  useEffect(() => {
    if (step === 0) return
    const nextBot = STEPS[step]
    if (nextBot) {
      setTimeout(() => {
        setMsgs(prev => [...prev, { from: 'bot', text: nextBot.bot }])
        if (nextBot.pills.length === 0) setDone(true)
      }, 600)
    }
  }, [step])

  // Spotlight: activate via body dataset
  useEffect(() => {
    const target = STEPS[step]?.spotlight
    if (target) {
      document.body.dataset.spotlight = target
    } else {
      delete document.body.dataset.spotlight
    }
    return () => { delete document.body.dataset.spotlight }
  }, [step])

  useEffect(() => {
    return () => { delete document.body.dataset.spotlight }
  }, [])

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [msgs])

  function handlePill(text: string) {
    setMsgs(prev => [...prev, { from: 'user', text }])
    if (step === CONNECTIONS_STEP && text === CONNECTIONS_PILL) {
      onOpenConnections?.()
    }
    setStep(s => s + 1)
  }

  function handleSend() {
    const t = inputVal.trim()
    if (!t) return
    setInputVal('')
    setMsgs(prev => [...prev, { from: 'user', text: t }])
    setStep(s => s + 1)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') handleSend()
  }

  const activePills = STEPS[step]?.pills ?? []

  return (
    <>
      {/* Backdrop over main content only — sidebar and topbar remain interactive */}
      <div
        style={{
          position: 'fixed',
          top: 'var(--th, 68px)',
          left: 'var(--sw, 90px)',
          right: 0,
          bottom: 0,
          background: 'rgba(3,8,24,0.55)',
          backdropFilter: 'blur(3px)',
          zIndex: 80,
          cursor: 'default',
        }}
        onClick={dismiss}
      />

      {/* Chat card — bottom-right, above backdrop */}
      <div
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          width: 360,
          maxHeight: '60vh',
          background: 'rgba(8,18,48,0.92)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 16,
          backdropFilter: 'blur(20px)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 90,
          animation: 'frSlideUp .45s cubic-bezier(.22,1,.36,1)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--gb)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--ac), var(--blue2))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 15,
          }}>🤖</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#E8EDF8' }}>Agente blu</div>
            <div style={{ fontSize: 11, color: 'rgba(232,237,248,0.5)' }}>Configuração inicial</div>
          </div>
          <button
            onClick={dismiss}
            style={{
              marginLeft: 'auto', fontSize: 16, color: 'rgba(232,237,248,0.4)',
              background: 'none', border: 'none', cursor: 'pointer', lineHeight: 1,
              padding: '2px 6px', borderRadius: 6,
            }}
            title="Fechar"
          >✕</button>
        </div>

        {/* Messages */}
        <div
          ref={bodyRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '14px 18px',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          {msgs.map((m, i) => (
            <div
              key={i}
              style={{
                maxWidth: '85%',
                padding: '9px 13px',
                borderRadius: 12,
                fontSize: 13,
                lineHeight: 1.45,
                alignSelf: m.from === 'bot' ? 'flex-start' : 'flex-end',
                background: m.from === 'bot'
                  ? 'var(--gl2)'
                  : 'rgba(140,95,219,0.22)',
                border: m.from === 'bot'
                  ? '1px solid rgba(255,255,255,0.09)'
                  : '1px solid rgba(140,95,219,0.35)',
                color: '#E8EDF8',
                borderBottomLeftRadius: m.from === 'bot' ? 3 : 12,
                borderBottomRightRadius: m.from === 'user' ? 3 : 12,
                animation: 'frMsgIn .25s ease',
              }}
            >
              {m.text}
            </div>
          ))}

          {!done && activePills.length > 0 && (
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 4 }}>
              {activePills.map(p => (
                <button
                  key={p}
                  className="btn btn-sm btn-ghost"
                  onClick={() => handlePill(p)}
                  style={{ borderRadius: 12 }}
                >
                  {p}
                </button>
              ))}
            </div>
          )}

          {done && (
            <button
              className="btn btn-primary"
              onClick={dismiss}
              style={{ width: '100%', marginTop: 8, fontSize: 13 }}
            >
              Entrar no escritório →
            </button>
          )}
        </div>

        {/* Input */}
        {!done && (
          <div style={{
            padding: '10px 14px 14px',
            borderTop: '1px solid var(--gb)',
            display: 'flex',
            gap: 8,
          }}>
            <input
              value={inputVal}
              onChange={e => setInputVal(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Responda ou escolha acima…"
              style={{
                flex: 1,
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 20,
                padding: '8px 14px',
                fontSize: 13,
                color: '#E8EDF8',
                outline: 'none',
                fontFamily: 'inherit',
              }}
            />
            <button
              onClick={handleSend}
              style={{
                width: 32, height: 32, borderRadius: '50%',
                background: 'var(--ac)', color: '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, border: 'none', cursor: 'pointer', flexShrink: 0,
              }}
            >➤</button>
          </div>
        )}
      </div>

      <style>{`
        @keyframes frSlideUp {
          from { opacity: 0; transform: translateY(24px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes frMsgIn {
          from { opacity: 0; transform: translateY(5px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </>
  )
}
