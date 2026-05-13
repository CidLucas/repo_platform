import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import { getUploadedFiles, deleteUploadedFile } from '../api/connectors'

export function useUploadedFiles() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['uploadedFiles', clientId],
    queryFn: () => getUploadedFiles(clientId!),
    enabled: !!clientId,
    staleTime: 60 * 1000,
  })
}

export function useDeleteUploadedFile() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (fileId: string) => deleteUploadedFile(fileId, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['uploadedFiles', clientId] })
    },
  })
}
