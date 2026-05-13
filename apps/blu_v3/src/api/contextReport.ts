import { supabase } from './client'

export interface ContextReport {
  id: string
  title: string
  storage_path: string
  created_at: string
  status: string
  file_name: string
}

export async function fetchContextReports(): Promise<ContextReport[]> {
  const { data, error } = await supabase
    .schema('vector_db')
    .from('documents')
    .select('id, title, storage_path, created_at, status, file_name')
    .eq('source', 'generated')
    .eq('category', 'business_context')
    .order('created_at', { ascending: false })
    .limit(24) // up to 2 years of monthly reports

  if (error) throw error
  return (data ?? []) as ContextReport[]
}

export async function downloadContextReport(storagePath: string): Promise<string> {
  const { data, error } = await supabase.storage
    .from('knowledge-base')
    .download(storagePath)

  if (error) throw error
  return await data.text()
}
