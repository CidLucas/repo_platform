import type { AgentSlug } from './agent'

export type NotificationType =
  | 'approval_created'
  | 'approval_approved'
  | 'approval_rejected'
  | 'insight'
  | 'alert'
  | 'system'

export type UrgencyLevel = 'low' | 'normal' | 'high' | 'critical'

export interface Notification {
  id: string
  client_id: string
  type: NotificationType
  urgency_level: UrgencyLevel
  title: string
  body: string | null
  agent_slug: AgentSlug | null
  related_entity_type: string | null
  related_entity_id: string | null
  read_at: string | null
  dismissed_at: string | null
  created_at: string
}
