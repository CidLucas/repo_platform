import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { fetchSuppliers, fetchComprasHistory } from '@/api/suppliers'

export function useSuppliers() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['suppliers', clientId],
    queryFn: () => fetchSuppliers(clientId!),
    enabled: !!clientId,
    staleTime: 60_000,
  })
}

export function useComprasHistory() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['compras-history', clientId],
    queryFn: () => fetchComprasHistory(clientId!),
    enabled: !!clientId,
    staleTime: 60_000,
  })
}
