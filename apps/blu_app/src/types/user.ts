export interface ClienteBlu {
  id: string
  external_user_id: string
  name: string | null
  email: string | null
  tier: 'free' | 'starter' | 'growth' | 'enterprise'
  created_at: string
}
