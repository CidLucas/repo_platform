import { useState, useRef, useEffect } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, Send, StopCircle, Wrench } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useAtendenteChat } from '@/hooks/useAtendenteChat'
import { relativeTime } from '@/utils/format'

interface ChatOverlayProps {
  open: boolean
  onClose: () => void
  /** Current pathname — sent as context to the agent. */
  currentPage: string
}

const BLU_GLOW = 'rgba(59,130,246,0.4)'

function BluOrb({ size = 24, working = false }: { size?: number; working?: boolean }) {
  return (
    <div
      className={cn('rounded-full shrink-0', working && 'animate-pulse')}
      style={{
        width: size,
        height: size,
        background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
        boxShadow: `0 0 ${size / 2}px ${BLU_GLOW}`,
      }}
    />
  )
}

export function ChatOverlay({ open, onClose, currentPage }: ChatOverlayProps) {
  const { messages, streamBuffer, activeToolName, isStreaming, error, sendMessage, cancelStream } =
    useAtendenteChat()
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom on new messages / streaming
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, streamBuffer])

  // Focus input when overlay opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [open])

  function handleClose() {
    cancelStream()
    onClose()
  }

  function handleSend() {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    setInput('')
    sendMessage(trimmed, currentPage)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && handleClose()}>
      <Dialog.Portal>
        {/* No backdrop — user can read the page while chatting */}
        <Dialog.Overlay className="hidden" />

        {/* Slide-up panel — bottom-left corner on desktop */}
        <Dialog.Content
          aria-describedby={undefined}
          className={cn(
            // Mobile: bottom sheet full-width
            'fixed bottom-0 left-0 right-0 z-50 outline-none',
            'h-[80dvh] flex flex-col',
            'bg-surface border-t border-border rounded-t-lg shadow-xl',
            // Desktop: bottom-left anchored panel
            'md:bottom-6 md:left-6 md:right-auto md:top-auto',
            'md:w-96 md:h-[70dvh]',
            'md:rounded-lg md:border md:border-border',
            // Slide-up animation
            'data-[state=open]:animate-slide-up',
            'data-[state=closed]:translate-y-full',
            'transition-transform duration-slow ease-out'
          )}
          aria-label="Chat com o assistente"
        >
          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0">
            <BluOrb size={24} working={isStreaming} />
            <div className="flex-1 min-w-0">
              <Dialog.Title className="text-body font-medium text-white">
                Conversar com Blu
              </Dialog.Title>
              {isStreaming && activeToolName ? (
                <p className="text-caption-sm text-blu-300 flex items-center gap-1">
                  <Wrench size={10} className="shrink-0" />
                  {activeToolName}
                </p>
              ) : isStreaming ? (
                <p className="text-caption-sm text-blu-300 animate-pulse">Processando...</p>
              ) : null}
            </div>
            <Dialog.Close asChild>
              <button
                onClick={handleClose}
                className={cn(
                  'p-1.5 rounded text-gray-400 hover:text-white transition-colors cursor-pointer',
                  'focus-visible:ring-2 focus-visible:ring-blu-500 outline-none'
                )}
                aria-label="Fechar chat"
              >
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          {/* Messages area */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 space-y-4 overscroll-contain"
          >
            {messages.length === 0 && !streamBuffer ? (
              <EmptyChatState />
            ) : (
              <>
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}

                {/* Live streaming buffer */}
                {streamBuffer && (
                  <div className="flex gap-3 items-start">
                    <BluOrb size={20} working className="mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div
                        className={cn(
                          'inline-block px-4 py-2.5 rounded-md rounded-tl-none',
                          'bg-elevated border border-border',
                          'text-body-sm text-gray-200 leading-relaxed'
                        )}
                      >
                        {streamBuffer}
                        <span className="inline-block w-0.5 h-4 bg-blu-400 animate-pulse ml-0.5 align-middle" />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {error && (
              <div className="text-caption text-urgent text-center py-2">{error}</div>
            )}
          </div>

          {/* Input area */}
          <div className="px-4 pb-4 pt-2 border-t border-border shrink-0">
            <div
              className={cn(
                'flex items-end gap-2 bg-base border border-border rounded-md',
                'focus-within:border-blu-500 transition-colors duration-normal'
              )}
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Pergunte ao Blu..."
                rows={1}
                disabled={isStreaming}
                className={cn(
                  'flex-1 bg-transparent px-4 py-3 text-body-sm text-white',
                  'placeholder:text-gray-500 resize-none outline-none',
                  'max-h-32 leading-relaxed',
                  'disabled:opacity-50'
                )}
                style={{ fieldSizing: 'content' } as React.CSSProperties}
              />
              <div className="pr-2 pb-2 shrink-0">
                {isStreaming ? (
                  <button
                    onClick={cancelStream}
                    className={cn(
                      'p-2 rounded text-urgent hover:text-urgent-dark transition-colors cursor-pointer',
                      'focus-visible:ring-2 focus-visible:ring-urgent outline-none'
                    )}
                    aria-label="Cancelar resposta"
                    title="Cancelar"
                  >
                    <StopCircle size={18} />
                  </button>
                ) : (
                  <button
                    onClick={handleSend}
                    disabled={!input.trim()}
                    className={cn(
                      'p-2 rounded transition-colors cursor-pointer',
                      'text-gray-400 hover:text-blu-400',
                      'disabled:opacity-30 disabled:cursor-not-allowed',
                      'focus-visible:ring-2 focus-visible:ring-blu-500 outline-none'
                    )}
                    aria-label="Enviar mensagem"
                  >
                    <Send size={18} />
                  </button>
                )}
              </div>
            </div>
            <p className="text-caption-sm text-gray-500 mt-1.5 text-center">
              Enter para enviar · Shift+Enter para nova linha
            </p>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function MessageBubble({
  message,
}: {
  message: { role: string; content: string; createdAt: Date }
}) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%]">
          <div
            className={cn(
              'px-4 py-2.5 rounded-md rounded-tr-none',
              'bg-blu-500/20 border border-blu-500/30',
              'text-body-sm text-white leading-relaxed'
            )}
          >
            {message.content}
          </div>
          <p className="text-caption-sm text-gray-500 text-right mt-1 pr-0.5">
            {relativeTime(message.createdAt.toISOString())}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3 items-start">
      <BluOrb size={20} className="mt-0.5" />
      <div className="flex-1 min-w-0">
        <div
          className={cn(
            'inline-block px-4 py-2.5 rounded-md rounded-tl-none max-w-[90%]',
            'bg-elevated border border-border',
            'text-body-sm text-gray-200 leading-relaxed'
          )}
        >
          {message.content}
        </div>
        <p className="text-caption-sm text-gray-500 mt-1 ml-0.5">
          {relativeTime(message.createdAt.toISOString())}
        </p>
      </div>
    </div>
  )
}

function EmptyChatState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-6">
      <BluOrb size={48} />
      <p className="text-body-sm text-gray-300 font-medium">Conversar com Blu</p>
      <p className="text-caption text-gray-500">
        Tire dúvidas, peça análises ou solicite explicações sobre as decisões.
      </p>
    </div>
  )
}
