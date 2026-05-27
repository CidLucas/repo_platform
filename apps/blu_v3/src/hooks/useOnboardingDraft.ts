import { useState, useCallback } from 'react'
import { supabase } from '@blu/auth'

export type Vertical =
  | 'ecommerce'
  | 'servicos'
  | 'industria'
  | 'saude'
  | 'educacao'
  | 'financeiro'
  | 'agro'
  | 'outro'
  | null

export type NotifyChannel = 'email' | 'whatsapp' | 'app'

export interface OnboardingDraft {
  authMethod: 'google' | 'email' | null
  nome: string
  email: string
  empresa: string
  cnpj: string
  vertical: Vertical
  porte: string
  website: string
  // Context questions answered inline after website detection
  primaryFocus: 'vendas' | 'operacao' | 'atendimento' | 'estoque' | 'outro' | null
  produtoServico: string
  systems: string[]
  csvUploaded: boolean
  googleDriveConnected: boolean
  dataPath: 'systems' | 'files' | 'scratch' | null
  agents: string[]
  approvalTasks: string[]
  routines: string[]
  notifyChannel: NotifyChannel
  mapping_confirmed?: boolean
}

// Default agents matching the blu_v3 room set
const DEFAULT_AGENTS = ['compras', 'financeiro', 'clientes', 'agenda', 'documentos', 'estrategia']

// Tasks that require human approval by default
const DEFAULT_APPROVAL_TASKS = ['make_payment', 'supplier_order']

// All cross_agent_routines enabled by default for every new client
// Kept empty — the auto_enroll_system_routines DB trigger handles this automatically.
const DEFAULT_ROUTINES: string[] = []

export function initialDraft(email: string): OnboardingDraft {
  return {
    authMethod: null,
    nome: '',
    email,
    empresa: '',
    cnpj: '',
    vertical: null,
    porte: '',
    website: '',
    primaryFocus: null,
    produtoServico: '',
    systems: [],
    csvUploaded: false,
    googleDriveConnected: false,
    dataPath: null,
    agents: DEFAULT_AGENTS,
    approvalTasks: DEFAULT_APPROVAL_TASKS,
    routines: DEFAULT_ROUTINES,
    notifyChannel: 'email',
  }
}

const DRAFT_KEY = (email: string) => `blu_onb_${email || 'anon'}`

export function useOnboardingDraft(userEmail: string) {
  const [draft, setDraft] = useState<OnboardingDraft>(() => {
    try {
      const raw = localStorage.getItem(DRAFT_KEY(userEmail))
      if (raw) return { ...initialDraft(userEmail), ...JSON.parse(raw) }
    } catch {}
    return initialDraft(userEmail)
  })

  const updateDraft = useCallback((patch: Partial<OnboardingDraft>) => {
    setDraft(prev => ({ ...prev, ...patch }))
  }, [])

  const saveDraft = useCallback(async (patch: Partial<OnboardingDraft>) => {
    setDraft(prev => {
      const next = { ...prev, ...patch }
      try { localStorage.setItem(DRAFT_KEY(userEmail), JSON.stringify(next)) } catch {}
      return next
    })
  }, [userEmail])

  const bootstrap = useCallback(async (finalPatch?: Partial<OnboardingDraft>) => {
    const state = finalPatch ? { ...draft, ...finalPatch } : draft

    const { data, error } = await supabase.functions.invoke('onboarding-bootstrap', {
      body: state,
    })

    if (error) throw new Error(error.message ?? 'Bootstrap failed')
    try { localStorage.removeItem(DRAFT_KEY(userEmail)) } catch {}
    return data as { client_id: string; agents: number; routines: number }
  }, [draft, userEmail])

  return { draft, updateDraft, saveDraft, bootstrap }
}

// ── Mapping helpers ────────────────────────────────────────────────────────

export const VERTICAL_MAP: Record<string, Vertical> = {
  // From StepAuth SECTORS (with emoji)
  '🛍 Comércio': 'ecommerce',
  '⚙️ Serviços': 'servicos',
  '🏭 Indústria': 'industria',
  '🌱 Agronegócio': 'agro',
  '💊 Saúde': 'saude',
  '📚 Educação': 'educacao',
  // From StepInfo VERTICALS (without emoji)
  'Comércio': 'ecommerce',
  'Serviços': 'servicos',
  'Indústria': 'industria',
  'Saúde': 'saude',
  'Educação': 'educacao',
  'Agronegócio': 'agro',
  'Financeiro': 'financeiro',
  'Outro': 'outro',
}

export const PORTE_MAP: Record<string, string> = {
  'Só eu': 'solo',
  '2–10 pessoas': 'micro',
  '10–50 pessoas': 'pequena',
  '50+ pessoas': 'media',
}
