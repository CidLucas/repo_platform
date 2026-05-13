import { useState, useCallback, useRef } from 'react'
import { streamChat } from '../api/atendente'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: Date
}

interface UseAtendenteChat {
  messages: ChatMessage[]
  streamBuffer: string
  activeToolName: string | null
  isStreaming: boolean
  error: string | null
  sendMessage: (content: string, currentPage?: string) => Promise<void>
  cancelStream: () => void
  clearMessages: () => void
}

function getOrCreateSessionId(): string {
  const key = 'atendente_session_id'
  const existing = sessionStorage.getItem(key)
  if (existing) return existing
  const id = crypto.randomUUID()
  sessionStorage.setItem(key, id)
  return id
}

export function useAtendenteChat(): UseAtendenteChat {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streamBuffer, setStreamBuffer] = useState('')
  const [activeToolName, setActiveToolName] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const sessionId = useRef(getOrCreateSessionId())

  const cancelStream = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setIsStreaming(false)
    setStreamBuffer('')
    setActiveToolName(null)
  }, [])

  const sendMessage = useCallback(async (content: string, currentPage?: string) => {
    if (isStreaming) return

    setError(null)
    setStreamBuffer('')
    setActiveToolName(null)

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      createdAt: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])

    setIsStreaming(true)
    abortRef.current = new AbortController()

    let fullText = ''

    await streamChat({
      message: content,
      sessionId: sessionId.current,
      currentPage,
      signal: abortRef.current.signal,
      onToken: (token) => {
        fullText += token
        setStreamBuffer(fullText)
      },
      onToolStart: (name) => {
        setActiveToolName(name)
      },
      onDone: (text) => {
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: text,
          createdAt: new Date(),
        }
        setMessages((prev) => [...prev, assistantMsg])
        setStreamBuffer('')
        setActiveToolName(null)
        setIsStreaming(false)
        abortRef.current = null
      },
      onError: (message) => {
        setError(message)
        setStreamBuffer('')
        setActiveToolName(null)
        setIsStreaming(false)
        abortRef.current = null
      },
    }).catch((e: unknown) => {
      if (e instanceof Error && e.name === 'AbortError') return
      setError('O agente não respondeu. Tente novamente.')
      setIsStreaming(false)
      setStreamBuffer('')
      setActiveToolName(null)
      abortRef.current = null
    })
  }, [isStreaming])

  const clearMessages = useCallback(() => {
    cancelStream()
    setMessages([])
    setError(null)
  }, [cancelStream])

  return {
    messages,
    streamBuffer,
    activeToolName,
    isStreaming,
    error,
    sendMessage,
    cancelStream,
    clearMessages,
  }
}
