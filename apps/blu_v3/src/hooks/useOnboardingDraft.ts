import { useState, useCallback, useEffect, useRef } from 'react'
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

const DEFAULT_AGENTS = ['compras', 'financeiro', 'clientes', 'agenda', 'documentos', 'estrategia']
const DEFAULT_APPROVAL_TASKS = ['make_payment', 'supplier_order']
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

  // AC: Re-initialize draft when userEmail changes (signOut → signIn as a
  // different user). useState's initializer only runs on first mount, so a
  // stale draft from a previous session would otherwise bleed into the new
  // one — the previous user's company name / CNPJ would appear in StepInfo.
  const prevEmailRef = useRef(userEmail)
  useEffect(() => {
    if (prevEmailRef.current === userEmail) return
    prevEmailRef.current = userEmail
    try {
      const raw = localStorage.getItem(DRAFT_KEY(userEmail))
      setDraft(raw
        ? { ...initialDraft(userEmail), ...JSON.parse(raw) }
        : initialDraft(userEmail)
      )
    } catch {
      setDraft(initialDraft(userEmail))
    }
  }, [userEmail])

  const updateDraft = useCallback((patch: Partial<OnboardingDraft>) => {
    setDraft(prev => ({ ...prev, ...patch }))
  }, [])

  const saveDraft = useCallback(async (patch: Partial<OnboardingDraft>) => {
    setDraft(prev => {
      const next = { ...prev, ...patch }
      try {
        const key = DRAFT_KEY(next.email || prev.email || userEmail || '')
        localStorage.setItem(key, JSON.stringify(next))
      } catch {}
      return next
    })
  }, [userEmail])

  const bootstrap = useCallback(async (finalPatch?: Partial<OnboardingDraft>) => {
    const state = finalPatch ? { ...draft, ...finalPatch } : draft

    const { data, error } = await supabase.functions.invoke('onboarding-bootstrap', {
      body: state,
    })

    if (error) throw new Error(error.message ?? 'Bootstrap failed')

    // Finaliza o onboarding: marca `onboarding_completed_at` e dispara a rotina
    // `onboarding_complete` (event-triggered). Desde o refactor P12
    // (migration 20260525_p12_split_onboarding_completion) essa é a ÚNICA via
    // que faz o dispatch — a edge function não dispara mais. Sem esta chamada o
    // onboarding nunca é finalizado e nenhuma rotina é triggered.
    // Best-effort e idempotente (a RPC ignora chamadas repetidas via cooldown).
    try {
      const { error: finalizeErr } = await supabase.rpc('finalize_onboarding')
      if (finalizeErr) console.warn('[onboarding] finalize_onboarding failed:', finalizeErr.message)
    } catch (e) {
      console.warn('[onboarding] finalize_onboarding error:', e)
    }

    try {
      const key = DRAFT_KEY(state.email || userEmail || '')
      localStorage.removeItem(key)
      localStorage.removeItem(DRAFT_KEY(state.authMethod ? (state.email || userEmail || '') : ''))
      localStorage.removeItem(DRAFT_KEY(''))
    } catch {}
    return data as unknown as { client_id: string; agents: number; routines: number; prompts_seeded: number }
  }, [draft, userEmail])

  return { draft, updateDraft, saveDraft, bootstrap }
}

export const VERTICAL_MAP: Record<string, Vertical> = {
  '🛍 Comércio': 'ecommerce',
  '⚙️ Serviços': 'servicos',
  '🏭 Indústria': 'industria',
  '🌱 Agronegócio': 'agro',
  '💊 Saúde': 'saude',
  '📚 Educação': 'educacao',
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
