import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '@blu/auth'
import {
  listDocuments,
  deleteDocument,
  uploadFile,
  retryDocument,
  getDocumentProgress,
  type KBDocument,
  type UploadOptions,
  type KBDocumentSource,
} from '../services/knowledgeBaseService'

interface KBState {
  documents: KBDocument[]
  loading: boolean
  error: string | null
  uploading: boolean
  uploadError: string | null
}

export function useKnowledgeBase() {
  const { clientId } = useAuth()

  const [state, setState] = useState<KBState>({
    documents: [],
    loading: true,
    error: null,
    uploading: false,
    uploadError: null,
  })

  const load = useCallback(async () => {
    if (!clientId) return
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }))
      const docs = await listDocuments(clientId)
      setState((prev) => ({ ...prev, documents: docs, loading: false }))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao carregar documentos'
      setState((prev) => ({ ...prev, error: message, loading: false }))
    }
  }, [clientId])

  useEffect(() => {
    load()
  }, [load])

  // Poll while any document is in a transient state
  useEffect(() => {
    const processing = state.documents.filter(
      (d) => d.status === 'processing' || d.status === 'pending',
    )
    if (processing.length === 0) return

    const interval = setInterval(() => {
      load()
    }, 5_000)

    return () => clearInterval(interval)
  }, [state.documents, load])

  const upload = useCallback(
    async (
      file: File,
      forceComplex = false,
      source: KBDocumentSource = 'upload',
      options?: UploadOptions,
    ) => {
      if (!clientId) return
      try {
        setState((prev) => ({ ...prev, uploading: true, uploadError: null }))
        await uploadFile(file, clientId, forceComplex, source, options)
        await load()
        setState((prev) => ({ ...prev, uploading: false }))
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Erro ao fazer upload'
        setState((prev) => ({ ...prev, uploading: false, uploadError: message }))
      }
    },
    [clientId, load],
  )

  const remove = useCallback(
    async (documentId: string, storagePath: string | null) => {
      try {
        await deleteDocument(documentId, storagePath)
        setState((prev) => ({
          ...prev,
          documents: prev.documents.filter((d) => d.id !== documentId),
        }))
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Erro ao remover documento'
        setState((prev) => ({ ...prev, error: message }))
      }
    },
    [],
  )

  const retry = useCallback(
    async (doc: KBDocument) => {
      try {
        await retryDocument(doc)
        setState((prev) => ({
          ...prev,
          documents: prev.documents.map((d) =>
            d.id === doc.id ? { ...d, status: 'processing' as const } : d,
          ),
        }))
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Erro ao reprocessar documento'
        setState((prev) => ({ ...prev, error: message }))
      }
    },
    [],
  )

  return {
    ...state,
    reload: load,
    upload,
    remove,
    retry,
    getDocumentProgress,
  }
}
