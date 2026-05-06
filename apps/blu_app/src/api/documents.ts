import { supabase } from './client'

export interface BluDocument {
  id: string
  client_id: string
  title: string
  agent_slug: string
  editor_content: unknown
  created_at: string
  updated_at: string
}

export interface DocTemplate {
  id: string
  name: string
  description: string | null
  category: string | null
  is_system: boolean
}

export interface DocumentVersion {
  id: string
  document_id: string
  version_number: number
  created_at: string
  summary: string | null
}

export async function fetchRecentDocuments(clientId: string): Promise<BluDocument[]> {
  const { data, error } = await supabase
    .from('documents')
    .select('id, client_id, title, agent_slug, editor_content, created_at, updated_at')
    .eq('client_id', clientId)
    .eq('agent_slug', 'documentos')
    .order('updated_at', { ascending: false })
    .limit(20)

  if (error) throw error
  return data ?? []
}

export async function fetchDocument(id: string): Promise<BluDocument | null> {
  const { data, error } = await supabase
    .from('documents')
    .select('*')
    .eq('id', id)
    .maybeSingle()

  if (error) throw error
  return data
}

export async function saveDocument(id: string, clientId: string, content: unknown): Promise<void> {
  const { error } = await supabase
    .from('documents')
    .update({ editor_content: content, updated_at: new Date().toISOString() })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}

export async function createDocument(clientId: string, title: string): Promise<BluDocument> {
  const { data, error } = await supabase
    .from('documents')
    .insert({
      client_id: clientId,
      title,
      agent_slug: 'documentos',
      editor_content: null,
    })
    .select()
    .single()

  if (error) throw error
  return data
}

export async function fetchDocTemplates(): Promise<DocTemplate[]> {
  const { data, error } = await supabase
    .from('doc_templates')
    .select('id, name, description, category, is_system')
    .order('is_system', { ascending: false })
    .order('name')

  if (error) throw error
  return data ?? []
}

export async function fetchDocumentVersions(documentId: string): Promise<DocumentVersion[]> {
  const { data, error } = await supabase
    .from('document_versions')
    .select('id, document_id, version_number, created_at, summary')
    .eq('document_id', documentId)
    .order('version_number', { ascending: false })
    .limit(20)

  if (error) throw error
  return data ?? []
}
