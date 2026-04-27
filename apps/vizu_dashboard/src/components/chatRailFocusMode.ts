export const CHAT_RAIL_FOCUS_MODE_STORAGE_KEY = 'vizu.chatRail.focusMode';
export const CHAT_RAIL_FOCUS_MODE_EVENT = 'vizu:chat-rail-focus-mode-changed';

export const getChatRailFocusMode = (): boolean => {
  if (typeof window === 'undefined') return false;
  return window.localStorage.getItem(CHAT_RAIL_FOCUS_MODE_STORAGE_KEY) === '1';
};

export const setChatRailFocusMode = (value: boolean): void => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(CHAT_RAIL_FOCUS_MODE_STORAGE_KEY, value ? '1' : '0');
  window.dispatchEvent(new CustomEvent(CHAT_RAIL_FOCUS_MODE_EVENT, { detail: { value } }));
};