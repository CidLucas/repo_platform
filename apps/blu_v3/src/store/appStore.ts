import { create } from 'zustand'

export type Screen =
  | 'home'
  | 'compras'
  | 'financeiro'
  | 'agenda'
  | 'documentos'
  | 'estrategia'
  | 'clientes'
  | 'atividade'
  | 'admin'
  | 'biblioteca'
  | 'blu_ops'

export type ToastType = 'ok' | 'no' | 'sn'

export interface Toast {
  id: string
  type: ToastType
  title: string
  msg: string
}

// Local-only decision UI state (used by rooms not yet wired to the backend)
export type DecisionStatus = 'pending' | 'expanded' | 'done' | 'rejected' | 'snoozed'

export interface Decision {
  id: string
  status: DecisionStatus
}

export interface AppState {
  screen: Screen
  breadcrumb: string
  // expandedId: used by wired rooms (HomePage, FinanceiroRoom) via React Query
  expandedId: string | null
  // decisions: local-only UI state for rooms not yet wired to backend
  decisions: Record<string, Decision>
  toasts: Toast[]
  // chatTrigger: set by openChatWith(); ChatPanel watches and opens + sends context
  chatTrigger: { context: string; ts: number } | null
  // initialTab: consumed once by room on mount via goWithTab()
  initialTab: string | null
  // pendingDocId: consumed once by DocumentosRoom on mount to auto-open a document
  pendingDocId: string | null
  // firstRun: true until user completes or dismisses the guided onboarding tour
  firstRun: boolean

  // actions
  go: (s: Screen, label: string) => void
  goWithTab: (s: Screen, label: string, tab: string) => void
  clearInitialTab: () => void
  setPendingDocId: (id: string | null) => void
  openChatWith: (context: string) => void
  toggleDc: (id: string) => void
  // Local-only approve/reject/snooze for un-wired rooms (no DB writes)
  approve: (id: string, msg: string) => void
  reject: (id: string) => void
  snooze: (id: string) => void
  addToast: (type: ToastType, title: string, msg: string) => void
  removeToast: (id: string) => void
  dismissFirstRun: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  screen: 'home',
  breadcrumb: 'Bom dia ☀️',
  expandedId: null,
  decisions: {},
  toasts: [],
  chatTrigger: null,
  initialTab: null,
  pendingDocId: null,
  firstRun: (() => { try { return !localStorage.getItem('blu_first_run_done') } catch { return true } })(),

  go(s, label) {
    set({
      screen: s,
      breadcrumb: s === 'home' ? 'Bom dia ☀️' : label,
      expandedId: null,
    })
  },

  goWithTab(s, label, tab) {
    set({ initialTab: tab })
    get().go(s, label)
  },

  clearInitialTab() {
    set({ initialTab: null })
  },

  setPendingDocId(id) {
    set({ pendingDocId: id })
  },

  openChatWith(context) {
    set({ chatTrigger: { context, ts: Date.now() } })
  },

  // toggleDc works for both modes:
  // - wired rooms use expandedId
  // - un-wired rooms use decisions[id].status
  toggleDc(id) {
    // Update expandedId (for wired rooms)
    set(s => ({ expandedId: s.expandedId === id ? null : id }))

    // Also update decisions map (for un-wired rooms still using it)
    const decisions = { ...get().decisions }
    if (!decisions[id]) {
      decisions[id] = { id, status: 'pending' }
    }
    const dc = decisions[id]
    if (dc.status === 'done' || dc.status === 'rejected') return
    const wasExpanded = dc.status === 'expanded'
    Object.keys(decisions).forEach(k => {
      if (decisions[k].status === 'expanded') {
        decisions[k] = { ...decisions[k], status: 'pending' }
      }
    })
    if (!wasExpanded) {
      decisions[id] = { ...dc, status: 'expanded' }
    }
    set({ decisions })
  },

  // Local-only — used by un-wired rooms
  approve(id, msg) {
    const decisions = { ...get().decisions }
    if (!decisions[id]) decisions[id] = { id, status: 'pending' }
    decisions[id] = { ...decisions[id], status: 'done' }
    set({ decisions })
    get().addToast('ok', 'Aprovado', msg)
  },

  reject(id) {
    const decisions = { ...get().decisions }
    if (!decisions[id]) decisions[id] = { id, status: 'pending' }
    decisions[id] = { ...decisions[id], status: 'rejected' }
    set({ decisions })
    get().addToast('no', 'Rejeitado', 'Blu anotou. Não vou sugerir este tipo de ação novamente.')
  },

  snooze(id) {
    const decisions = { ...get().decisions }
    if (!decisions[id]) decisions[id] = { id, status: 'pending' }
    decisions[id] = { ...decisions[id], status: 'snoozed' }
    set({ decisions })
    setTimeout(() => {
      const current = { ...get().decisions }
      if (current[id]?.status === 'snoozed') {
        current[id] = { ...current[id], status: 'pending' }
        set({ decisions: current })
      }
    }, 2800)
    get().addToast('sn', 'Adiado', 'Lembrete em 2 horas. Voltarei a isso.')
  },

  addToast(type, title, msg) {
    const id = Math.random().toString(36).slice(2)
    const toast: Toast = { id, type, title, msg }
    set(s => ({ toasts: [...s.toasts, toast] }))
    setTimeout(() => get().removeToast(id), 4000)
  },

  removeToast(id) {
    set(s => ({ toasts: s.toasts.filter(t => t.id !== id) }))
  },

  dismissFirstRun() {
    try { localStorage.setItem('blu_first_run_done', '1') } catch {}
    set({ firstRun: false })
  },
}))
