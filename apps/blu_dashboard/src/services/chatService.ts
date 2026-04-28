import axios from 'axios';
import type { StructuredData } from '../components/SimpleDataTable';

// API Base URL - connects to atendente_core for chat
// Uses VITE_ATENDENTE_CORE if set, otherwise falls back to localhost
const CHAT_API_URL = import.meta.env.VITE_ATENDENTE_CORE || 'http://localhost:8003';

// --- Request Deduplication ---
// Tracks in-flight requests to prevent duplicate submissions
const inflightRequests = new Map<string, Promise<ChatResponse>>();
const inflightStreamRequests = new Set<string>();

/**
 * Generate a deduplication key from the request
 * Uses session_id + message hash to identify duplicate requests
 */
function getRequestKey(request: ChatRequest): string {
  return `${request.session_id || 'default'}_${request.message}`;
}

// --- Type Definitions ---
export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  structuredData?: StructuredData;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  context?: {
    current_page?: string;
    selected_filters?: Record<string, string>;
    /** Document IDs from vector_db uploaded via chat file attachment */
    attached_document_ids?: string[];
  };
}

export interface ChatResponse {
  response: string;
  session_id: string;
  suggestions?: string[];
  structured_data?: StructuredData;
  data_references?: {
    type: string;
    id: string;
    label: string;
  }[];
}

// --- SSE Event Types ---
export type StreamEventType = 'token' | 'tool_start' | 'tool_end' | 'done' | 'error';

export interface StreamEvent {
  event: StreamEventType;
  data: string | StreamToolEvent | StreamDoneData | StreamErrorData;
}

export interface StreamToolEvent {
  name: string;
  args?: Record<string, unknown>;
  output?: string;
}

export interface StreamDoneData {
  response: string;
  model: string;
  structured_data?: StructuredData;
}

export interface StreamErrorData {
  message: string;
}

export interface ChatStreamCallbacks {
  /** Called for each LLM token */
  onToken?: (token: string) => void;
  /** Called when a tool starts executing */
  onToolStart?: (tool: { name: string; args?: Record<string, unknown> }) => void;
  /** Called when a tool finishes */
  onToolEnd?: (tool: { name: string; output?: string }) => void;
  /** Called when streaming completes */
  onComplete?: (data: StreamDoneData) => void;
  /** Called on error */
  onError?: (error: Error) => void;
}

// --- Chat Service Functions ---

/**
 * Send a chat message and get a response (blocking).
 * Includes request deduplication to prevent duplicate submissions.
 */
export async function sendChatMessage(
  request: ChatRequest,
  authToken?: string
): Promise<ChatResponse> {
  const requestKey = getRequestKey(request);

  // Check if there's already an in-flight request with the same key
  const existingRequest = inflightRequests.get(requestKey);
  if (existingRequest) {
    console.debug('[ChatService] Deduplicating request:', requestKey);
    return existingRequest;
  }

  // Create the actual request promise
  const requestPromise = (async () => {
    try {
      const response = await axios.post<ChatResponse>(`${CHAT_API_URL}/chat`, request, {
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        timeout: 60000, // 60 second timeout for LLM responses
      });
      return response.data;
    } catch (error: unknown) {
      console.error('Chat API Error:', error);
      const axiosError = error as { response?: { data?: { detail?: string } } };
      throw new Error(axiosError.response?.data?.detail || 'Erro ao enviar mensagem. Tente novamente.');
    } finally {
      // Remove from in-flight map once complete (success or error)
      inflightRequests.delete(requestKey);
    }
  })();

  // Track the in-flight request
  inflightRequests.set(requestKey, requestPromise);

  return requestPromise;
}

/**
 * Send a chat message with streaming response (Server-Sent Events).
 * Streams tokens as they arrive for better perceived latency.
 * Includes request deduplication to prevent duplicate streams.
 */
export async function sendChatMessageStream(
  request: ChatRequest,
  callbacks: ChatStreamCallbacks,
  authToken?: string
): Promise<void> {
  const requestKey = getRequestKey(request);

  // Check if there's already an in-flight stream with the same key
  if (inflightStreamRequests.has(requestKey)) {
    console.debug('[ChatService] Ignoring duplicate stream request:', requestKey);
    return;
  }

  // Track the in-flight stream
  inflightStreamRequests.add(requestKey);

  try {
    const response = await fetch(`${CHAT_API_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE format - each event is "data: {...}\n\n"
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (!data) continue;

          try {
            const parsed = JSON.parse(data) as StreamEvent;
            const eventType = parsed.event;
            const eventData = parsed.data;

            switch (eventType) {
              case 'token':
                callbacks.onToken?.(eventData as string);
                break;

              case 'tool_start':
                callbacks.onToolStart?.(eventData as StreamToolEvent);
                break;

              case 'tool_end':
                callbacks.onToolEnd?.(eventData as StreamToolEvent);
                break;

              case 'done':
                callbacks.onComplete?.(eventData as StreamDoneData);
                return; // Exit on done

              case 'error':
                throw new Error((eventData as StreamErrorData).message);
            }
          } catch (parseError) {
            // If not valid JSON, log and continue
            console.warn('[ChatService] Failed to parse SSE event:', data, parseError);
          }
        }
      }
    }
  } catch (error: unknown) {
    console.error('Chat Stream Error:', error);
    const err = error instanceof Error ? error : new Error('Erro na conexão de streaming');
    callbacks.onError?.(err);
  } finally {
    // Remove from in-flight set once complete (success or error)
    inflightStreamRequests.delete(requestKey);
  }
}

/**
 * Get chat history for a session
 */
export async function getChatHistory(sessionId: string): Promise<ChatMessage[]> {
  try {
    const response = await axios.get<ChatMessage[]>(`${CHAT_API_URL}/history/${sessionId}`);
    return response.data;
  } catch (error: unknown) {
    console.error('Chat History Error:', error);
    return [];
  }
}

/**
 * Generate a unique session ID
 */
export function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
