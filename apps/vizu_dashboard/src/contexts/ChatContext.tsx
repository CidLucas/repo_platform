import React, { createContext, useContext, useState, useCallback } from 'react';

interface ChatContextType {
  isChatOpen: boolean;
  /**
   * Optional initial message to seed the chat input. When set, ChatPanel
   * pre-fills the textarea on next open. Consumers should call
   * `consumeInitialMessage()` once they've read it so it is not re-applied.
   */
  initialMessage: string | null;
  openChat: (initialMessage?: string) => void;
  closeChat: () => void;
  toggleChat: () => void;
  consumeInitialMessage: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [initialMessage, setInitialMessage] = useState<string | null>(null);

  const openChat = useCallback((message?: string) => {
    if (message && message.trim()) {
      setInitialMessage(message);
    }
    setIsChatOpen(true);
  }, []);
  const closeChat = useCallback(() => setIsChatOpen(false), []);
  const toggleChat = useCallback(() => setIsChatOpen((prev) => !prev), []);
  const consumeInitialMessage = useCallback(() => setInitialMessage(null), []);

  return (
    <ChatContext.Provider
      value={{ isChatOpen, initialMessage, openChat, closeChat, toggleChat, consumeInitialMessage }}
    >
      {children}
    </ChatContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components -- Context hook export is intentional
export const useChat = (): ChatContextType => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
