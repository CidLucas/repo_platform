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

export type ToastType = 'ok' | 'no' | 'sn'

export interface Toast {
  id: string
  type: ToastType
  title: string
  msg: string
}

export type DecisionStatus = 'pending' | 'expanded' | 'done' | 'rejected' | 'snoozed'

export interface Decision {
  id: string
  status: DecisionStatus
}

export interface AppState {
  screen: Screen
  breadcrumb: string
  decisions: Record<string, Decision>
  toasts: Toast[]
  pendingCount: number

  // actions
  go: (s: Screen, label: string) => void
  toggleDc: (id: string) => void
  approve: (id: string, msg: string) => void
  reject: (id: string) => void
  snooze: (id: string) => void
  addToast: (type: ToastType, title: string, msg: string) => void
  removeToast: (id: string) => void
}

const INITIAL_DECISIONS: Record<string, Decision> = {
  dc1: { id: 'dc1', status: 'pending' },
  dc2: { id: 'dc2', status: 'pending' },
  dc3: { id: 'dc3', status: 'pending' },
}

export const useAppStore = create<AppState>((set, get) => ({
  screen: 'home',
  breadcrumb: 'Bom dia, Carlos ☀️',
  decisions: INITIAL_DECISIONS,
  toasts: [],
  pendingCount: 5,

  go(s, label) {
    set({
      screen: s,
      breadcrumb:
        s === 'home'
          ? 'Bom dia, Carlos ☀️'
          : label,
    })
  },

  toggleDc(id) {
    const decisions = { ...get().decisions }
    const dc = decisions[id]
    if (!dc || dc.status === 'done' || dc.status === 'rejected') return

    // collapse all siblings
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

  approve(id, msg) {
    const decisions = { ...get().decisions }
    if (!decisions[id]) return
    decisions[id] = { ...decisions[id], status: 'done' }
    const pendingCount = Math.max(0, get().pendingCount - 1)
    set({ decisions, pendingCount })
    get().addToast('ok', 'Aprovado', msg)
  },

  reject(id) {
    const decisions = { ...get().decisions }
    if (!decisions[id]) return
    decisions[id] = { ...decisions[id], status: 'rejected' }
    set({ decisions })
    get().addToast('no', 'Rejeitado', 'Blu anotou. Não vou sugerir este tipo de ação novamente.')
  },

  snooze(id) {
    const decisions = { ...get().decisions }
    if (!decisions[id]) return
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
}))
