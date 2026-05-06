import { supabase } from './client'

export interface ClientRoutine {
  id: string
  client_id: string
  routine_id: string
  active: boolean
  config: Record<string, unknown>
  last_run_at: string | null
}

export async function fetchRoutines(
  clientId: string,
  prefix?: string
): Promise<ClientRoutine[]> {
  let query = supabase
    .from('client_routines')
    .select('*')
    .eq('client_id', clientId)

  if (prefix) {
    query = query.like('routine_id', `${prefix}%`)
  }

  const { data, error } = await query.order('routine_id')
  if (error) throw error
  return data ?? []
}

export async function toggleRoutine(
  id: string,
  clientId: string,
  enabled: boolean
): Promise<void> {
  const { error } = await supabase
    .from('client_routines')
    .update({ active: enabled })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}
