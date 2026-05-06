import type { AgentSlug } from './agent'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'snoozed'
export type ApprovalPriority = 'urgent' | 'normal' | 'low'

export interface ApprovalPayload {
  description?: string
  bullets?: string[]
  [key: string]: unknown
}

export interface ApprovalRequest {
  id: string
  client_id: string
  agent_slug: AgentSlug
  status: ApprovalStatus
  priority: ApprovalPriority
  title: string
  insight_text: string | null
  payload: ApprovalPayload
  snooze_until: string | null
  snooze_count: number
  scheduled_for: string | null
  created_at: string
  updated_at: string
}
