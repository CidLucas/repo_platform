import { supabase } from './client'

export interface CalendarEvent {
  id: string
  title: string
  start_at: string
  end_at: string | null
  location: string | null
  calendar_source: string | null
  agenda_source: 'calendar' | 'approval'
}

export interface CalendarSettings {
  id: string
  client_id: string
  enabled: boolean
  provider: string | null
  calendar_name: string | null
}

export interface AgendaHistoryItem {
  id: string
  title: string
  action: 'approved' | 'rejected' | 'snoozed' | 'other'
  created_at: string
}

const CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.readonly'
const DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive.readonly'
// Request both scopes together so the single integration_tokens row covers both.
const DRIVE_AND_CALENDAR_SCOPES = `${DRIVE_SCOPE} ${CALENDAR_SCOPE}`

/** Initiates direct Google OAuth (server-side code exchange — gets refresh_token reliably). */
export async function connectGoogleCalendar(): Promise<void> {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) throw new Error('Not authenticated')

  const resp = await fetch(
    `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/google-oauth-start`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ scope: CALENDAR_SCOPE, return_url: window.location.href }),
    }
  )
  if (!resp.ok) throw new Error('Failed to start Google OAuth')
  const { url } = await resp.json()
  window.location.href = url
}

/**
 * Called after OAuth return. Stores the encrypted token via the
 * onboarding-capture-drive-token edge function, then enables calendar_settings.
 */
export async function captureCalendarToken(opts: {
  refreshToken: string
  accessToken: string
  email: string
  timezone?: string
}): Promise<void> {
  const { error } = await supabase.functions.invoke('onboarding-capture-drive-token', {
    body: {
      provider_refresh_token: opts.refreshToken,
      provider_token: opts.accessToken,
      account_email: opts.email,
      scopes: [CALENDAR_SCOPE],
    },
  })
  if (error) throw error

  const { data: clientId, error: cidErr } = await supabase.rpc('get_my_client_id')
  if (cidErr || !clientId) throw new Error('Could not resolve client_id')

  const { error: upsertErr } = await supabase
    .from('calendar_settings')
    .upsert(
      {
        client_id: clientId,
        calendar_id: 'primary',
        enabled: true,
        provider: 'google',
        calendar_name: opts.email,
        range_days: 7,
        timezone: opts.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone,
        updated_at: new Date().toISOString(),
      },
      { onConflict: 'client_id' },
    )
  if (upsertErr) throw upsertErr
}

/** Redirects to Google OAuth requesting drive + calendar read scopes. */
export async function connectGoogleDrive(redirectTo: string): Promise<void> {
  sessionStorage.setItem('drive_oauth_pending', '1')
  await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo,
      scopes: DRIVE_AND_CALENDAR_SCOPES,
      queryParams: { access_type: 'offline', prompt: 'consent' },
    },
  })
}

/**
 * Called after Drive OAuth return. Stores the encrypted token via
 * onboarding-capture-drive-token with both drive and calendar scopes.
 */
export async function captureDriveToken(opts: {
  refreshToken: string
  accessToken: string
  email: string
}): Promise<void> {
  const { error } = await supabase.functions.invoke('onboarding-capture-drive-token', {
    body: {
      provider_refresh_token: opts.refreshToken,
      provider_token: opts.accessToken,
      account_email: opts.email,
      scopes: [DRIVE_SCOPE, CALENDAR_SCOPE],
    },
  })
  if (error) throw error
}

/** Fetch today's schedule — approval_requests.scheduled_for + Google Calendar events */
export async function fetchTodaySchedule(clientId: string): Promise<CalendarEvent[]> {
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)
  const todayEnd = new Date()
  todayEnd.setHours(23, 59, 59, 999)

  const [approvalsResult, calendarResult] = await Promise.allSettled([
    supabase
      .from('approval_requests')
      .select('id, title, scheduled_for, agent_slug')
      .eq('client_id', clientId)
      .gte('scheduled_for', todayStart.toISOString())
      .lte('scheduled_for', todayEnd.toISOString())
      .eq('status', 'pending')
      .order('scheduled_for'),

    supabase.functions.invoke('google-calendar-events', { body: { rangeDays: 1 } }),
  ])

  const approvalEvents: CalendarEvent[] =
    approvalsResult.status === 'fulfilled' && approvalsResult.value.data
      ? approvalsResult.value.data.map((row) => ({
          id: row.id,
          title: row.title,
          start_at: row.scheduled_for,
          end_at: null,
          location: null,
          calendar_source: null,
          agenda_source: 'approval' as const,
        }))
      : []

  const gcalEvents: CalendarEvent[] =
    calendarResult.status === 'fulfilled' &&
    !calendarResult.value.error &&
    !calendarResult.value.data?.disabled
      ? (calendarResult.value.data?.events ?? []).map(
          (ev: { id: string; title: string; starts_at: string; ends_at: string; location: string | null }) => ({
            id: ev.id,
            title: ev.title,
            start_at: ev.starts_at,
            end_at: ev.ends_at,
            location: ev.location,
            calendar_source: 'google',
            agenda_source: 'calendar' as const,
          }),
        )
      : []

  const all = [...approvalEvents, ...gcalEvents]
  all.sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
  return all
}

export async function fetchCalendarSettings(clientId: string): Promise<CalendarSettings | null> {
  const { data, error } = await supabase
    .from('calendar_settings')
    .select('*')
    .eq('client_id', clientId)
    .maybeSingle()

  if (error) throw error
  return data
}

export async function fetchAgendaHistory(clientId: string): Promise<AgendaHistoryItem[]> {
  const { data, error } = await supabase
    .from('approval_requests')
    .select('id, title, status, created_at')
    .eq('client_id', clientId)
    .eq('agent_slug', 'agenda')
    .in('status', ['approved', 'rejected'])
    .order('created_at', { ascending: false })
    .limit(15)

  if (error) throw error

  return (data ?? []).map((row) => ({
    id: row.id,
    title: row.title,
    action: row.status as 'approved' | 'rejected',
    created_at: row.created_at,
  }))
}

export interface UnifiedTask {
  task_id: string
  title: string
  domain: string
  start_date: string
  due_date: string | null
  status: string
  source: 'approval' | 'routine' | 'calendar'
  /** Expressão cron para rotinas periódicas (ex: "0 6 * * *"). Null para não-cron. */
  schedule_cron?: string | null
}

export async function fetchUnifiedTasks(clientId: string): Promise<UnifiedTask[]> {
  const { data, error } = await supabase
    .rpc('get_unified_tasks', { p_client_id: clientId })
  if (error) throw error
  return (data ?? []) as UnifiedTask[]
}

export interface AgendaExternalEvent {
  id: string
  title: string
  start_date: string
  due_date: string | null
  domain: string
  source: 'google' | 'monday' | 'notion'
  /** Hierarchy type:
   *  monday: project (board) → phase (group) → task (item)
   *  google: event
   *  notion: page
   */
  type: 'project' | 'phase' | 'task' | 'subitem' | 'milestone' | 'event' | 'page'
  /** Links task→phase id, phase→project id. null for top-level items. */
  parent_id: string | null
  url: string | null
  status: string
  location: string | null
  owner: string | null
  progress_pct: number | null
  group_title: string | null
  description: string | null
  notes: string | null
}

export async function fetchExternalAgendaEvents(rangeDays = 84): Promise<AgendaExternalEvent[]> {
  const { data, error } = await supabase.functions.invoke('get-agenda-events', {
    body: { rangeDays },
  })
  if (error) throw error
  return (data?.events ?? []) as AgendaExternalEvent[]
}

/** Lazy-fetch subitems for a specific Monday item (4th level Gantt).
 *  Returns [] if the item has no subitems or Monday token is missing. */
export async function fetchMondaySubitems(itemId: string): Promise<AgendaExternalEvent[]> {
  // itemId may be prefixed (monday_item_12345) or raw (12345)
  const rawId = itemId.replace('monday_item_', '')
  const { data, error } = await supabase.functions.invoke('get-monday-subitems', {
    body: { item_id: rawId },
  })
  if (error) throw error
  return (data?.subitems ?? []) as AgendaExternalEvent[]
}
