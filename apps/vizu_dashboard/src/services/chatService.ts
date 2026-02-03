import axios from 'axios';
import type { StructuredData } from '../components/SimpleDataTable';

// API Base URL - connects to analytics_api for chat
const CHAT_API_URL = 'http://localhost:8009/api/chat';

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

export interface ChatStreamChunk {
  content: string;
  done: boolean;
}

// --- Chat Service Functions ---

/**
 * Send a chat message and get a response
 */
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  try {
    const response = await axios.post<ChatResponse>(CHAT_API_URL, request, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 60000, // 60 second timeout for LLM responses
    });
    return response.data;
  } catch (error: any) {
    console.error('Chat API Error:', error);
    throw new Error(error.response?.data?.detail || 'Erro ao enviar mensagem. Tente novamente.');
  }
}

/**
 * Send a chat message with streaming response
 */
export async function sendChatMessageStream(
  request: ChatRequest,
  onChunk: (chunk: string) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): Promise<void> {
  try {
    const response = await fetch(`${CHAT_API_URL}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        onComplete();
        break;
      }

      const chunk = decoder.decode(value, { stream: true });

      // Parse SSE format
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            onComplete();
            return;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.content) {
              onChunk(parsed.content);
            }
          } catch {
            // If not JSON, treat as plain text
            onChunk(data);
          }
        }
      }
    }
  } catch (error: any) {
    console.error('Chat Stream Error:', error);
    onError(new Error(error.message || 'Erro na conexão de streaming'));
  }
}

/**
 * Get chat history for a session
 */
export async function getChatHistory(sessionId: string): Promise<ChatMessage[]> {
  try {
    const response = await axios.get<ChatMessage[]>(`${CHAT_API_URL}/history/${sessionId}`);
    return response.data;
  } catch (error: any) {
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
