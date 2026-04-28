import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';

interface ChatContextType {
  isChatOpen: boolean;
  /**
   * Optional initial message to seed the chat input. When set, ChatPanel
   * pre-fills the textarea on next open. Consumers should call
   * `consumeInitialMessage()` once they've read it so it is not re-applied.
   */
  initialMessage: string | null;
  openChat: (initialMessage?: string, returnFocusElement?: HTMLElement | null) => void;
  closeChat: () => void;
  toggleChat: () => void;
  consumeInitialMessage: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [initialMessage, setInitialMessage] = useState<string | null>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);

  const restoreFocus = useCallback(() => {
    const target = returnFocusRef.current;
    returnFocusRef.current = null;
    if (!target) {
      return;
    }

    window.requestAnimationFrame(() => {
      if (target.isConnected) {
        target.focus();
      }
    });
  }, []);

  const openChat = useCallback((message?: string, returnFocusElement?: HTMLElement | null) => {
    if (message && message.trim()) {
      setInitialMessage(message);
    }
    if (returnFocusElement) {
      returnFocusRef.current = returnFocusElement;
    }
    setIsChatOpen(true);
  }, []);
  const closeChat = useCallback(() => {
    setIsChatOpen(false);
    restoreFocus();
  }, [restoreFocus]);
  const toggleChat = useCallback(() => {
    setIsChatOpen((prev) => {
      if (prev) {
        restoreFocus();
      }
      return !prev;
    });
  }, [restoreFocus]);
  const consumeInitialMessage = useCallback(() => setInitialMessage(null), []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const isShortcut = (event.metaKey || event.ctrlKey) && event.code === 'Backslash';
      if (!isShortcut) {
        return;
      }

      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName?.toLowerCase();
      const isTypingContext = tagName === 'input' || tagName === 'textarea' || Boolean(target?.isContentEditable);
      if (isTypingContext) {
        return;
      }

      event.preventDefault();
      setIsChatOpen((prev) => !prev);
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

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
