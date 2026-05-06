import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Zap, ArrowRight } from 'lucide-react'
import { supabase } from '@/api/client'

export function OnboardingBanner() {
  const [incomplete, setIncomplete] = useState(false)
  const location = useLocation()

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession()
      if (!session || cancelled) return

      const { data, error } = await supabase
        .from('clientes_blu')
        .select('onboarding_completed_at, client_id')
        .maybeSingle()
      if (cancelled || error || !data) return
      if (!data.client_id) return
      setIncomplete(data.onboarding_completed_at === null)
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (!incomplete || location.pathname === '/onboarding') return null

  return (
    <div className="mx-4 mt-3 px-4 py-3 rounded-xl border border-purple-500/35 bg-gradient-to-r from-blue-500/10 to-purple-500/10 flex items-center justify-between gap-3 flex-wrap shrink-0">
      <div className="flex items-center gap-2">
        <Zap size={15} strokeWidth={1.5} className="text-purple-400 shrink-0" />
        <span className="text-body-sm text-white">
          Seu onboarding ainda não foi concluído. Ative seus agentes para liberar os insights.
        </span>
      </div>
      <Link
        to="/onboarding"
        className="flex items-center gap-1 text-body-sm font-semibold text-purple-400 hover:text-purple-300 transition-colors duration-normal whitespace-nowrap"
      >
        Continuar onboarding
        <ArrowRight size={13} strokeWidth={2} />
      </Link>
    </div>
  )
}
