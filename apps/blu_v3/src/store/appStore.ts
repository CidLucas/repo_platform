import { create } from 'zustand'

export type Screen =
  | 'home'
  | 'compras'
  | 'financeiro'
  | 'agenda'
  | 'estrategia'
  | 'clientes'
  | 'atividade'
  | 'admin'
  | 'biblioteca'
  | 'blu_ops'
  | 'documentos'

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
  initFirstRun: (clientId: string) => void
  dismissFirstRun: (clientId: string) => void
  // internal: called by popstate listener only
  _restoreScreen: (s: Screen, label: string) => void
}

// --- Browser history sync helpers ---
const SCREEN_LABELS: Record<Screen, string> = {
  home: 'Início', compras: 'Compras', financeiro: 'Financeiro',
  agenda: 'Agenda', estrategia: 'Estratégia',
  clientes: 'Clientes', atividade: 'Atividade', admin: 'Admin',
  biblioteca: 'Biblioteca', blu_ops: 'BluOps', documentos: 'Documentos',
}

const VALID_SCREENS = new Set<string>(Object.keys(SCREEN_LABELS))

function screenFromHash(): Screen {
  const hash = window.location.hash  // e.g. '#room/financeiro'
  if (hash.startsWith('#room/')) {
    const candidate = hash.slice(6)
    if (VALID_SCREENS.has(candidate)) return candidate as Screen
  }
  // Legacy: 'documentos' was a screen; the room now lives as a tab inside EstrategiaRoom
  if (window.location.hash === '#room/documentos') return 'estrategia'
  return 'home'
}

function pushScreen(s: Screen, label: string) {
  const state = { screen: s, label }
  const hash = `#room/${s}`
  // only push if different from current hash to avoid duplicates
  if (window.location.hash !== hash) {
    window.history.pushState(state, '', hash)
  }
}

// Wire up popstate once (module level — survives React re-renders)
let _popstateWired = false
let _storeRef: { getState: () => AppState } | null = null
function wirePopstate() {
  if (_popstateWired) return
  _popstateWired = true
  window.addEventListener('popstate', (e) => {
    if (!_storeRef) return
    const state = e.state as { screen?: Screen; label?: string } | null
    if (state?.screen) {
      _storeRef.getState()._restoreScreen(state.screen, state.label ?? SCREEN_LABELS[state.screen])
    } else if (!window.location.hash || window.location.hash === '#room/home') {
      _storeRef.getState()._restoreScreen('home', 'Início')
    }
  })
}

export const useAppStore = create<AppState>((set, get) => {
  const initialScreen = screenFromHash()
  const store = {
    screen: initialScreen,
    breadcrumb: initialScreen === 'home' ? 'Bom dia ☀️' : SCREEN_LABELS[initialScreen],
    expandedId: null,
    decisions: {},
    toasts: [],
    chatTrigger: null,
    initialTab: null,
    pendingDocId: null,
    firstRun: true,

    go(s: Screen, label: string) {
      pushScreen(s, label)
      set({
        screen: s,
        breadcrumb: s === 'home' ? 'Bom dia ☀️' : label,
        expandedId: null,
      })
    },

    goWithTab(s: Screen, label: string, tab: string) {
      set({ initialTab: tab })
      get().go(s, label)
    },

    _restoreScreen(s: Screen, label: string) {
      set({
        screen: s,
        breadcrumb: s === 'home' ? 'Bom dia ☀️' : label,
        expandedId: null,
        initialTab: null,
      })
    },

    clearInitialTab() {
      set({ initialTab: null })
    },

    setPendingDocId(id: string | null) {
      set({ pendingDocId: id })
    },

    openChatWith(context: string) {
      set({ chatTrigger: { context, ts: Date.now() } })
    },

    // toggleDc works for both modes:
    // - wired rooms use expandedId
    // - un-wired rooms use decisions[id].status
    toggleDc(id: string) {
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
    approve(id: string, msg: string) {
      const decisions = { ...get().decisions }
      if (!decisions[id]) decisions[id] = { id, status: 'pending' }
      decisions[id] = { ...decisions[id], status: 'done' }
      set({ decisions })
      get().addToast('ok', 'Aprovado', msg)
    },

    reject(id: string) {
      const decisions = { ...get().decisions }
      if (!decisions[id]) decisions[id] = { id, status: 'pending' }
      decisions[id] = { ...decisions[id], status: 'rejected' }
      set({ decisions })
      get().addToast('no', 'Rejeitado', 'Blu anotou. Não vou sugerir este tipo de ação novamente.')
    },

    snooze(id: string) {
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

    addToast(type: ToastType, title: string, msg: string) {
      const id = Math.random().toString(36).slice(2)
      const toast: Toast = { id, type, title, msg }
      set(s => ({ toasts: [...s.toasts, toast] }))
      setTimeout(() => get().removeToast(id), 4000)
    },

    removeToast(id: string) {
      set(s => ({ toasts: s.toasts.filter(t => t.id !== id) }))
    },

    initFirstRun(clientId: string) {
      try {
        const done = !!localStorage.getItem(`blu_first_run_done:${clientId}`)
        set({ firstRun: !done })
      } catch {
        set({ firstRun: true })
      }
    },

    dismissFirstRun(clientId: string) {
      try { localStorage.setItem(`blu_first_run_done:${clientId}`, '1') } catch {
        // localStorage may be unavailable; firstRun is also dismissed in store state
      }
      set({ firstRun: false })
    },
  }

  return store
})

// Wire popstate after store is created
_storeRef = useAppStore
wirePopstate()

