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

/** Redirects to Google OAuth requesting calendar read scope. */
export async function connectGoogleCalendar(redirectTo: string): Promise<void> {
  sessionStorage.setItem('cal_oauth_pending', '1')
  await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo,
      scopes: CALENDAR_SCOPE,
      queryParams: { access_type: 'offline', prompt: 'consent' },
    },
  })
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
