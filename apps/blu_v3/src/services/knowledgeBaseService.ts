/**
 * Knowledge Base service for blu_v3.
 * Ported from apps/blu_app/src/services/knowledgeBaseService.ts
 * Uses @blu/auth supabase singleton.
 */

import { supabase } from '@blu/auth'

// ── Types ──────────────────────────────────────────────────────

export interface KBDocument {
  id: string
  client_id: string
  title: string | null
  file_name: string
  file_type: string | null
  storage_path: string | null
  source: 'upload' | 'chat' | 'url' | 'api'
  processing_mode: 'simple' | 'complex'
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'partially_failed'
  error_message: string | null
  chunk_count: number
  description: string | null
  category: string | null
  scope: 'platform' | 'client'
  created_at: string
  updated_at: string
}

export interface UploadOptions {
  forceComplex?: boolean
  description?: string
  category?: string
}

export interface EmbeddingProgress {
  total_chunks: number
  embedded_chunks: number
  progress_pct: number
  status: KBDocument['status'] | null
}

export type KBDocumentSource = 'upload' | 'chat' | 'url' | 'api'

export const KB_CATEGORIES = [
  { value: 'dados_negocio', label: 'Dados de Negócio' },
  { value: 'contexto_empresa', label: 'Contexto da Empresa' },
  { value: 'documentos', label: 'Documentos' },
  { value: 'conhecimento_ia', label: 'Conhecimento da IA' },
] as const

export type KBCategory = (typeof KB_CATEGORIES)[number]['value']

// ── Constants ──────────────────────────────────────────────────

const STORAGE_BUCKET = 'knowledge-base'
const ALWAYS_COMPLEX_EXTENSIONS = new Set(['.pptx', '.xlsx'])
const CSV_EXTENSIONS = new Set(['.csv', '.tsv'])

// ── Helpers ────────────────────────────────────────────────────

function getExtension(fileName: string): string {
  const idx = fileName.lastIndexOf('.')
  return idx === -1 ? '' : fileName.slice(idx).toLowerCase()
}

export function isComplexFile(fileName: string, forceComplex = false): boolean {
  const ext = getExtension(fileName)
  if (ALWAYS_COMPLEX_EXTENSIONS.has(ext)) return true
  if (forceComplex && (ext === '.pdf' || ext === '.docx')) return true
  return false
}

export function isCsvFile(fileName: string): boolean {
  return CSV_EXTENSIONS.has(getExtension(fileName))
}

export function getAcceptedExtensions(): string {
  return '.pdf,.docx,.csv,.txt,.md,.json,.xml,.html,.xlsx,.pptx,.yaml,.yml'
}

// ── Service functions ──────────────────────────────────────────

export async function listDocuments(clientId: string): Promise<KBDocument[]> {
  const { data, error } = await supabase
    .schema('vector_db')
    .from('documents')
    .select('*')
    .eq('client_id', clientId)
    .order('created_at', { ascending: false })

  if (error) throw new Error(`Erro ao listar documentos: ${error.message}`)
  return (data ?? []) as KBDocument[]
}

export async function deleteDocument(documentId: string, storagePath: string | null): Promise<void> {
  if (storagePath) {
    const { error: storageError } = await supabase.storage
      .from(STORAGE_BUCKET)
      .remove([storagePath])
    if (storageError) {
      console.warn('Erro ao remover arquivo do storage:', storageError.message)
    }
  }

  const { error } = await supabase
    .schema('vector_db')
    .from('documents')
    .delete()
    .eq('id', documentId)

  if (error) throw new Error(`Erro ao deletar documento: ${error.message}`)
}

export async function getDocumentProgress(documentId: string): Promise<EmbeddingProgress> {
  const [rpcResult, docResult] = await Promise.all([
    supabase
      .schema('vector_db')
      .rpc('get_document_embedding_progress', { p_document_id: documentId }),
    supabase
      .schema('vector_db')
      .from('documents')
      .select('status')
      .eq('id', documentId)
      .maybeSingle(),
  ])

  if (rpcResult.error) throw new Error(`Erro ao buscar progresso: ${rpcResult.error.message}`)

  const row = Array.isArray(rpcResult.data) ? rpcResult.data[0] : rpcResult.data
  const docStatus = docResult.data?.status ?? null

  return {
    total_chunks: row?.total_chunks ?? 0,
    embedded_chunks: row?.embedded_chunks ?? 0,
    progress_pct: row?.progress_pct ?? 0,
    status: docStatus,
  }
}

async function getAuthToken(): Promise<string> {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session?.access_token) throw new Error('Sessão expirada — faça login novamente.')
  return session.access_token
}

export async function uploadSimpleFile(
  file: File,
  clientId: string,
  source: KBDocumentSource = 'upload',
  options?: UploadOptions,
): Promise<string> {
  const ext = getExtension(file.name)
  const storagePath = `${clientId}/${crypto.randomUUID()}-${file.name}`

  const { error: uploadError } = await supabase.storage
    .from(STORAGE_BUCKET)
    .upload(storagePath, file)

  if (uploadError) throw new Error(`Erro no upload: ${uploadError.message}`)

  const { data: doc, error: insertError } = await supabase
    .schema('vector_db')
    .from('documents')
    .insert({
      client_id: clientId,
      file_name: file.name,
      file_type: ext.replace('.', ''),
      storage_path: storagePath,
      source,
      processing_mode: 'simple' as const,
      status: 'processing' as const,
      scope: 'client' as const,
      description: options?.description || null,
      category: options?.category || null,
    })
    .select('id')
    .single()

  if (insertError || !doc) throw new Error(`Erro ao criar documento: ${insertError?.message}`)

  const documentId = doc.id

  const { error: fnError } = await supabase.functions.invoke('process-document', {
    body: {
      document_id: documentId,
      storage_path: storagePath,
      client_id: clientId,
      file_name: file.name,
      file_type: ext.replace('.', ''),
    },
  })

  if (fnError) throw new Error(`Erro ao processar documento: ${fnError.message}`)

  return documentId
}

export async function uploadComplexFile(
  file: File,
  clientId: string,
  source: KBDocumentSource = 'upload',
  options?: UploadOptions,
): Promise<string> {
  const ext = getExtension(file.name)
  const storagePath = `${clientId}/${crypto.randomUUID()}-${file.name}`

  const { error: uploadError } = await supabase.storage
    .from(STORAGE_BUCKET)
    .upload(storagePath, file)

  if (uploadError) throw new Error(`Erro no upload: ${uploadError.message}`)

  const { data: doc, error: insertError } = await supabase
    .schema('vector_db')
    .from('documents')
    .insert({
      client_id: clientId,
      file_name: file.name,
      file_type: ext.replace('.', ''),
      storage_path: storagePath,
      source,
      processing_mode: 'complex' as const,
      status: 'pending' as const,
      scope: 'client' as const,
      description: options?.description || null,
      category: options?.category || null,
    })
    .select('id')
    .single()

  if (insertError || !doc) throw new Error(`Erro ao criar documento: ${insertError?.message}`)

  const documentId = doc.id

  const fileUploadApiUrl = import.meta.env.VITE_FILE_UPLOAD_API_URL
  if (!fileUploadApiUrl) {
    console.warn('VITE_FILE_UPLOAD_API_URL not set, skipping complex processing')
    return documentId
  }

  const accessToken = await getAuthToken()

  try {
    const res = await fetch(`${fileUploadApiUrl}/v1/upload/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        document_id: documentId,
        storage_path: storagePath,
        file_name: file.name,
        client_id: clientId,
      }),
    })

    if (!res.ok) {
      const errText = await res.text().catch(() => '')
      throw new Error(`Erro ao processar documento complexo (HTTP ${res.status}): ${errText}`)
    }
  } catch (err) {
    throw new Error(
      `Erro ao processar documento complexo: ${err instanceof Error ? err.message : String(err)}`,
    )
  }

  return documentId
}

export async function uploadFile(
  file: File,
  clientId: string,
  forceComplex = false,
  source: KBDocumentSource = 'upload',
  options?: UploadOptions,
): Promise<string> {
  if (isComplexFile(file.name, forceComplex)) {
    return uploadComplexFile(file, clientId, source, { ...options, forceComplex })
  }
  return uploadSimpleFile(file, clientId, source, options)
}

export interface CsvUploadResult {
  source_id: string
  columns: number
  file_name: string
}

export async function uploadCsvDataSource(
  file: File,
  clientId: string,
): Promise<CsvUploadResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('client_id', clientId)
  form.append('schema_type', 'invoices')

  const { data, error } = await supabase.functions.invoke('upload-csv-source', {
    body: form,
  })

  if (error || !data?.source_id) {
    throw new Error(error?.message ?? 'Erro ao processar CSV como fonte de dados')
  }

  return {
    source_id: data.source_id,
    columns: (data.columns as unknown[])?.length ?? 0,
    file_name: data.file_name ?? file.name,
  }
}

export async function retryDocument(doc: KBDocument): Promise<void> {
  await supabase
    .schema('vector_db')
    .from('document_chunks')
    .delete()
    .eq('document_id', doc.id)

  await supabase
    .schema('vector_db')
    .from('documents')
    .update({ status: 'processing', chunk_count: 0, error_message: null })
    .eq('id', doc.id)

  const { error } = await supabase.functions.invoke('process-document', {
    body: {
      document_id: doc.id,
      storage_path: doc.storage_path,
      client_id: doc.client_id,
      file_name: doc.file_name,
      file_type: doc.file_type,
    },
  })

  if (error) throw new Error(`Erro ao reprocessar: ${error.message}`)
}
