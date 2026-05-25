import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import { fetchTxCategories, saveTxCategories } from '../api/financeiro'

export function useTxCategories() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['tx-categories', clientId],
    queryFn: () => fetchTxCategories(clientId!),
    enabled: !!clientId,
    staleTime: Infinity,
    placeholderData: {},
  })
}

export function useSaveTxCategory() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (categories: Record<string, string>) => saveTxCategories(categories),
    onMutate: async (categories) => {
      await qc.cancelQueries({ queryKey: ['tx-categories', clientId] })
      const previous = qc.getQueryData<Record<string, string>>(['tx-categories', clientId])
      qc.setQueryData(['tx-categories', clientId], categories)
      return { previous }
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) {
        qc.setQueryData(['tx-categories', clientId], ctx.previous)
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['tx-categories', clientId] })
    },
  })
}
