import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useAppStore } from '../../store/appStore'
import { useAtendenteChat } from '../../hooks/useAtendenteChat'
import LoadingState from '../shared/LoadingState'
import Pagination from '../shared/Pagination'
import SmartRenderer from './SmartRenderer'
import { IconX } from '../shared/Icons'

function relTime(date: Date): string {
  const diff = (Date.now() - date.getTime()) / 1000
  if (diff < 60)  return 'agora'
  if (diff < 3600) return `${Math.floor(diff / 60)}min`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  return `${Math.floor(diff / 86400)}d`
}

let orbUid = 0

function BluOrb({ size = 24, working = false }: { size?: number; working?: boolean }) {
  const [uid] = useState(() => `orb${++orbUid}`)
  const h = Math.round(size * 26 / 30)
  return (
    <svg
      width={size}
      height={h}
      viewBox="0 0 30 26"
      fill="none"
      style={{ flexShrink: 0, animation: working ? 'chat-orb-pulse 1.4s ease-in-out infinite' : 'none' }}
    >
      <defs>
        <linearGradient id={uid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#9B72F5" />
            <stop offset="100%" stopColor="var(--blue2)" />
        </linearGradient>
        <clipPath id={`${uid}c`}>
          <path d="M5,0 H25 Q30,0 30,5 V14 Q30,19 25,19 H9 L4,25 L7,19 H5 Q0,19 0,14 V5 Q0,0 5,0 Z" />
        </clipPath>
      </defs>
      <path
        d="M5,0 H25 Q30,0 30,5 V14 Q30,19 25,19 H9 L4,25 L7,19 H5 Q0,19 0,14 V5 Q0,0 5,0 Z"
        fill={`url(#${uid})`}
      />
      <ellipse cx="13" cy="5" rx="11" ry="3.5" fill="rgba(255,255,255,0.18)" />
      <g clipPath={`url(#${uid}c)`}>
        <path d="M-2,11 Q7.5,8.5 15,11 Q22.5,13.5 32,11" stroke="white" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeOpacity={0.9} />
        <path d="M-2,15 Q7.5,12.5 15,15 Q22.5,17.5 32,15" stroke="white" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeOpacity={0.5} />
      </g>
    </svg>
  )
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2L11 13" /><path d="M22 2L15 22L11 13L2 9L22 2Z" />
    </svg>
  )
}

function StopIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><rect x="9" y="9" width="6" height="6" />
    </svg>
  )
}

function WrenchIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  )
}

export default function ChatPanel() {
  const screen      = useAppStore(s => s.screen)
  const chatTrigger = useAppStore(s => s.chatTrigger)
  const [open, setOpen] = useState(false)

  const { messages, streamBuffer, activeToolName, isStreaming, error, sendMessage, cancelStream } =
    useAtendenteChat()

  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLTextAreaElement>(null)
  const panelRef  = useRef<HTMLDivElement>(null)
  const [page, setPage] = useState(1)
  const pageSize = 20

  // Open panel and send context when an insight triggers a chat
  useEffect(() => {
    if (!chatTrigger) return
    setOpen(true)
    // Slight delay so the panel is mounted before sending
    setTimeout(() => sendMessage(chatTrigger.context, screen), 120)
  }, [chatTrigger?.ts]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!(e.metaKey || e.ctrlKey) || e.code !== 'Backslash') return
      const t = e.target as HTMLElement | null
      const tag = t?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || t?.isContentEditable) return
      e.preventDefault()
      setOpen(v => !v)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, streamBuffer])

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 280)
  }, [open])

  function handleClose() {
    cancelStream()
    setOpen(false)
  }

  function handleSend() {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    setInput('')
    sendMessage(trimmed, screen)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
  const shortcut = isMac ? '⌘\\' : 'Ctrl+\\'

  const panel = (
    <>
      {!open && (
        <button
          className="chat-fab"
          aria-label="Abrir assistente"
          title={`Assistente · ${shortcut}`}
          onClick={() => setOpen(true)}
        >
          <svg width="34" height="32" viewBox="0 0 30 28" fill="none" aria-hidden="true">
            <defs>
              <clipPath id="fabClip">
                <path d="M7,0 H23 Q30,0 30,7 V15 Q30,22 23,22 H12 L4,28 L8,22 H7 Q0,22 0,15 V7 Q0,0 7,0 Z"/>
              </clipPath>
            </defs>
            <path d="M7,0 H23 Q30,0 30,7 V15 Q30,22 23,22 H12 L4,28 L8,22 H7 Q0,22 0,15 V7 Q0,0 7,0 Z" fill="rgba(255,255,255,0.18)"/>
            <g clipPath="url(#fabClip)">
              <path d="M-1,10 Q7.5,7 15,10 Q22.5,13 31,10" stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
              <path d="M-1,15 Q7.5,12 15,15 Q22.5,18 31,15" stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeOpacity="0.65"/>
              <path d="M-1,20 Q7.5,17 15,20 Q22.5,23 31,20" stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeOpacity="0.3"/>
            </g>
          </svg>
        </button>
      )}

      {open && (
        <div
          ref={panelRef}
          role="dialog"
          aria-label="Chat com o assistente"
          aria-modal="false"
          style={{
            position: 'fixed',
            bottom: 22,
            right: 20,
            width: 360,
            height: '70dvh',
            zIndex: 150,
            display: 'flex',
            flexDirection: 'column',
            background: 'radial-gradient(ellipse 100% 35% at 50% 0%, rgba(140,95,219,0.13) 0%, transparent 100%), rgba(6,10,26,0.97)',
            backdropFilter: 'blur(28px)',
            border: '1px solid color-mix(in srgb, var(--fg) 10%, transparent)',
            borderTop: '2px solid rgba(140,95,219,0.55)',
            borderRadius: 14,
            boxShadow: '0 24px 64px rgba(0,0,0,0.65), 0 0 0 0.5px rgba(140,95,219,0.18)',
            animation: 'chat-slide-up 0.18s ease-out',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 9,
            padding: '11px 13px 10px',
            borderBottom: '1px solid var(--gl2)',
            flexShrink: 0,
            background: 'linear-gradient(180deg, rgba(140,95,219,0.07) 0%, transparent 100%)',
          }}>
            <BluOrb size={26} working={isStreaming} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--fg)', letterSpacing: '-.2px', lineHeight: 1.2 }}>
                Conversar com Blu
              </div>
              {isStreaming && activeToolName ? (
                <div style={{ fontSize: 10, color: 'var(--ac)', display: 'flex', alignItems: 'center', gap: 3, marginTop: 2 }}>
                  <WrenchIcon />
                  {activeToolName}
                </div>
              ) : isStreaming ? (
                <div style={{ fontSize: 10, color: 'var(--ac)', marginTop: 2, animation: 'chat-orb-pulse 1.4s ease-in-out infinite' }}>
                  Processando...
                </div>
              ) : (
                <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 2 }}>bureau of AI agents · deepblue</div>
              )}
            </div>
            <button
              onClick={handleClose}
              className="ibtn"
              aria-label="Fechar chat"
            >
              <IconX size={16} />
            </button>
          </div>

          {/* Messages */}
          <div
            ref={scrollRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px 13px',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
              minHeight: 0,
              overscrollBehavior: 'contain',
            }}
          >
            {messages.length === 0 && !streamBuffer ? (
              <EmptyState onSuggest={(q) => sendMessage(q, screen)} />
            ) : (
              <>
                {(() => {
                  const totalPages = Math.max(1, Math.ceil(messages.length / pageSize))
                  const safePage = Math.min(page, totalPages)
                  const visible = messages.slice(
                    (safePage - 1) * pageSize,
                    safePage * pageSize
                  )
                  return (
                    <>
                      {visible.map(msg => (
                        <MessageBubble key={msg.id} role={msg.role} content={msg.content} createdAt={msg.createdAt} />
                      ))}
                      {totalPages > 1 && (
                        <Pagination
                          currentPage={safePage}
                          totalPages={totalPages}
                          totalItems={messages.length}
                          pageSize={pageSize}
                          onPageChange={setPage}
                        />
                      )}
                    </>
                  )
                })()}

                {isStreaming && !streamBuffer && (
                  <div style={{ padding: '4px 0' }}>
                    <LoadingState variant="row" rows={2} />
                  </div>
                )}

                {streamBuffer && (
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <div style={{ marginTop: 3, flexShrink: 0 }}>
                      <BluOrb size={18} working />
                    </div>
                    <div style={{
                      padding: '8px 11px',
                      borderRadius: '0 8px 8px 8px',
                      background: 'color-mix(in srgb, var(--fg) 5.5%, transparent)',
                      border: '1px solid rgba(255,255,255,0.09)',
                      fontSize: 12.5,
                      color: 'var(--mu2)',
                      lineHeight: 1.5,
                      maxWidth: '90%',
                    }}>
                      <SmartRenderer content={streamBuffer} />
                      <span style={{
                        display: 'inline-block',
                        width: 2,
                        height: 13,
                        background: 'var(--ac)',
                        marginLeft: 2,
                        verticalAlign: 'middle',
                        animation: 'chat-orb-pulse 1s ease-in-out infinite',
                      }} />
                    </div>
                  </div>
                )}
              </>
            )}

            {error && (
              <div style={{ fontSize: 11.5, color: 'var(--urg)', textAlign: 'center', padding: '6px 0' }}>
                {error}
              </div>
            )}
          </div>

          {/* Input area */}
          <div style={{ padding: '8px 12px 12px', borderTop: '1px solid var(--gl2)', flexShrink: 0 }}>
            <div style={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: 6,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.09)',
              borderRadius: 9,
            }}>
              <textarea
                ref={inputRef}
                className="chat-input"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Pergunte ao Blu..."
                rows={1}
                disabled={isStreaming}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  padding: '9px 11px',
                  fontSize: 12.5,
                  color: 'var(--fg)',
                  resize: 'none',
                  fontFamily: 'var(--body)',
                  lineHeight: 1.5,
                  maxHeight: 110,
                  opacity: isStreaming ? 0.5 : 1,
                }}
              />
              <div style={{ padding: '6px 7px 7px', flexShrink: 0 }}>
                {isStreaming ? (
                  <button onClick={cancelStream} aria-label="Cancelar resposta" style={{ padding: 6, borderRadius: 6, color: 'var(--urg)', display: 'flex' }}>
                    <StopIcon />
                  </button>
                ) : (
                  <button
                    onClick={handleSend}
                    disabled={!input.trim()}
                    aria-label="Enviar mensagem"
                    style={{
                      padding: 6,
                      borderRadius: 6,
                      color: input.trim() ? 'var(--ac)' : 'var(--mu)',
                      display: 'flex',
                      opacity: input.trim() ? 1 : 0.4,
                      transition: 'color .12s, opacity .12s',
                    }}
                  >
                    <SendIcon />
                  </button>
                )}
              </div>
            </div>
            <p style={{ fontSize: 10, color: 'var(--mu)', textAlign: 'center', marginTop: 5 }}>
              Enter para enviar · Shift+Enter para nova linha
            </p>
          </div>
        </div>
      )}
    </>
  )

  return createPortal(panel, document.body)
}

function MessageBubble({ role, content, createdAt }: { role: string; content: string; createdAt: Date }) {
  if (role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <div style={{ maxWidth: '82%' }}>
          <div style={{
            padding: '8px 11px',
            borderRadius: '8px 0 8px 8px',
            background: 'rgba(140,95,219,0.18)',
            border: '1px solid rgba(140,95,219,0.30)',
            fontSize: 12.5,
            color: 'var(--fg)',
            lineHeight: 1.5,
          }}>
            {content}
          </div>
          <div style={{ fontSize: 10, color: 'var(--mu)', textAlign: 'right', marginTop: 3 }}>
            {relTime(createdAt)}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
      <div style={{ marginTop: 3, flexShrink: 0 }}>
        <BluOrb size={18} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          display: 'inline-block',
          padding: '8px 11px',
          borderRadius: '0 8px 8px 8px',
          background: 'color-mix(in srgb, var(--fg) 5.5%, transparent)',
          border: '1px solid rgba(255,255,255,0.09)',
          fontSize: 12.5,
          color: 'var(--mu2)',
          lineHeight: 1.5,
          maxWidth: '90%',
        }}>
          <SmartRenderer content={content} />
        </div>
        <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 3 }}>
          {relTime(createdAt)}
        </div>
      </div>
    </div>
  )
}

const SUGGESTIONS = [
  'Resuma as decisões pendentes',
  'Quais agentes estão ativos?',
  'O que devo priorizar hoje?',
]

function EmptyState({ onSuggest }: { onSuggest: (q: string) => void }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      gap: 11,
      textAlign: 'center',
      padding: '0 20px',
    }}>
      <svg width="80" height="70" viewBox="0 0 30 26" fill="none">
        <defs>
          <linearGradient id="es-g" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#9B72F5" />
            <stop offset="100%" stopColor="var(--blue2)" />
          </linearGradient>
          <clipPath id="es-c">
            <path d="M5,0 H25 Q30,0 30,5 V14 Q30,19 25,19 H9 L4,25 L7,19 H5 Q0,19 0,14 V5 Q0,0 5,0 Z" />
          </clipPath>
        </defs>
        <path d="M5,0 H25 Q30,0 30,5 V14 Q30,19 25,19 H9 L4,25 L7,19 H5 Q0,19 0,14 V5 Q0,0 5,0 Z" fill="url(#es-g)" />
        <ellipse cx="13" cy="5" rx="11" ry="4" fill="rgba(255,255,255,0.2)" />
        <g clipPath="url(#es-c)">
          <path d="M-2,9  Q7.5,6.5 15,9  Q22.5,11.5 32,9"  stroke="white" strokeWidth="1.4" fill="none" strokeLinecap="round" strokeOpacity={0.95} />
          <path d="M-2,13 Q7.5,10.5 15,13 Q22.5,15.5 32,13" stroke="white" strokeWidth="1.4" fill="none" strokeLinecap="round" strokeOpacity={0.6} />
          <path d="M-2,17 Q7.5,14.5 15,17 Q22.5,19.5 32,17" stroke="white" strokeWidth="1.4" fill="none" strokeLinecap="round" strokeOpacity={0.28} />
        </g>
      </svg>
      <div>
        <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--fg)', letterSpacing: '-.2px', marginBottom: 4 }}>Olá! Sou o Blu</p>
        <p style={{ fontSize: 11.5, color: 'var(--mu)', lineHeight: 1.6, maxWidth: 210 }}>
          Peça análises, explique decisões ou tire dúvidas sobre o seu negócio.
        </p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5, width: '100%' }}>
        {SUGGESTIONS.map(q => (
          <button key={q} className="chat-suggest-btn" onClick={() => onSuggest(q)}>
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
