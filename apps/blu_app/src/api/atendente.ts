import { buildAuthHeaders } from './auth'

const BASE_URL = (import.meta.env.VITE_ATENDENTE_CORE as string | undefined) ?? ''

if (!BASE_URL) {
  console.warn('[atendente] VITE_ATENDENTE_CORE is not set')
}

export interface AtendenteSSEEvent {
  event: 'token' | 'tool_start' | 'tool_end' | 'done' | 'error'
  data: string | Record<string, unknown>
}

export interface StreamChatOptions {
  message: string
  sessionId: string
  currentPage?: string
  signal?: AbortSignal
  onToken: (token: string) => void
  onToolStart?: (name: string) => void
  onDone: (fullText: string) => void
  onError: (message: string) => void
}

/**
 * Stream a chat message to atendente_core via SSE.
 * Calls onToken for each token, onDone when the stream completes.
 */
export async function streamChat(opts: StreamChatOptions): Promise<void> {
  const { message, sessionId, currentPage, signal, onToken, onToolStart, onDone, onError } = opts

  const headers = await buildAuthHeaders()

  const response = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message,
      session_id: sessionId,
      metadata: currentPage ? { current_page: currentPage } : undefined,
    }),
    signal,
  })

  if (!response.ok) {
    onError(`Erro ${response.status}: não foi possível conectar ao agente.`)
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    onError('Resposta inválida do servidor.')
    return
  }

  const decoder = new TextDecoder()
  let fullText = ''
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    if (signal?.aborted) break

    buffer += decoder.decode(value, { stream: true })

    // Process all complete SSE lines in the buffer
    const lines = buffer.split('\n')
    // Keep the last (potentially incomplete) line in buffer
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (!raw || raw === '[DONE]') continue

      let evt: AtendenteSSEEvent
      try {
        evt = JSON.parse(raw)
      } catch {
        continue
      }

      if (evt.event === 'token') {
        const token = typeof evt.data === 'string' ? evt.data : ''
        fullText += token
        onToken(token)
      } else if (evt.event === 'tool_start') {
        const name = typeof evt.data === 'object' ? String((evt.data as Record<string, unknown>).name ?? '') : ''
        onToolStart?.(name)
      } else if (evt.event === 'done') {
        const finalText =
          typeof evt.data === 'object'
            ? String((evt.data as Record<string, unknown>).response ?? fullText)
            : fullText
        onDone(finalText)
        return
      } else if (evt.event === 'error') {
        const msg =
          typeof evt.data === 'object'
            ? String((evt.data as Record<string, unknown>).message ?? 'Erro desconhecido')
            : String(evt.data)
        onError(msg)
        return
      }
    }
  }

  // Stream ended without a `done` event — still resolve with what we have
  if (fullText) onDone(fullText)
}
