import { supabase } from './client'

export interface BluDocument {
  id: string
  client_id: string
  title: string
  agent_slug: string
  status?: 'draft' | 'published' | 'archived'
  editor_content: unknown
  created_at: string
  updated_at: string
}

export interface DocTemplate {
  id: string
  client_id: string | null
  name: string
  description: string | null
  category: string | null
  is_system: boolean
}

export async function fetchRecentDocuments(clientId: string): Promise<BluDocument[]> {
  const { data, error } = await supabase
    .from('documents')
    .select('id, client_id, title, agent_slug, status, editor_content, created_at, updated_at')
    .eq('client_id', clientId)
    .in('agent_slug', ['documentos', 'biblioteca', 'estrategia', 'financeiro', 'compras', 'clientes', 'agenda'])
    .neq('status', 'archived')
    .order('updated_at', { ascending: false })
    .limit(20)

  if (error) throw error
  return data ?? []
}

export async function fetchDraftDocuments(clientId: string): Promise<BluDocument[]> {
  const { data, error } = await supabase
    .from('documents')
    .select('id, client_id, title, agent_slug, status, editor_content, created_at, updated_at')
    .eq('client_id', clientId)
    .eq('status', 'draft')
    .order('created_at', { ascending: false })
    .limit(20)

  if (error) throw error
  return data ?? []
}

export async function publishDocument(id: string, clientId: string): Promise<void> {
  const { error } = await supabase
    .from('documents')
    .update({ status: 'published', updated_at: new Date().toISOString() })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}

export async function archiveDocument(id: string, clientId: string): Promise<void> {
  const { error } = await supabase
    .from('documents')
    .update({ status: 'archived', updated_at: new Date().toISOString() })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
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

export async function fetchDocTemplates(clientId: string): Promise<DocTemplate[]> {
  const { data, error } = await supabase
    .from('doc_templates')
    .select('id, client_id, name, description, category, is_system')
    .or(`is_system.eq.true,client_id.eq.${clientId}`)
    .order('is_system', { ascending: false })
    .order('name')

  if (error) throw error
  return data ?? []
}
