import { useContext } from 'react'
import { TrustContext, type TrustContextValue } from '@/contexts/TrustContext'

export function useTrust(): TrustContextValue {
  const ctx = useContext(TrustContext)
  if (!ctx) throw new Error('useTrust must be used within TrustProvider')
  return ctx
}
