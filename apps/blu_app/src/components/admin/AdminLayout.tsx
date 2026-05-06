import { useState, type ReactNode } from 'react'
import { Settings } from 'lucide-react'
import { cn } from '@/utils/cn'
import { TabGroup } from '@/components/primitives/TabGroup'
import { RoomErrorBoundary } from '@/components/layout/RoomErrorBoundary'

export type AdminTab =
  | 'integrations'
  | 'users'
  | 'billing'
  | 'audit'
  | 'lgpd'
  | 'notifications'

const TABS = [
  { id: 'integrations' as AdminTab, label: 'Integrações' },
  { id: 'users' as AdminTab, label: 'Usuários' },
  { id: 'billing' as AdminTab, label: 'Faturamento' },
  { id: 'audit' as AdminTab, label: 'Auditoria' },
  { id: 'lgpd' as AdminTab, label: 'LGPD' },
  { id: 'notifications' as AdminTab, label: 'Notificações' },
]

interface AdminLayoutProps {
  integrations: ReactNode
  users: ReactNode
  billing: ReactNode
  audit: ReactNode
  lgpd: ReactNode
  notifications: ReactNode
}

/**
 * AdminLayout — tabbed layout for the Admin page.
 * NOT the desk pattern. Each tab renders independently.
 */
export function AdminLayout({
  integrations,
  users,
  billing,
  audit,
  lgpd,
  notifications,
}: AdminLayoutProps) {
  const [activeTab, setActiveTab] = useState<AdminTab>('integrations')

  const panelContent: Record<AdminTab, ReactNode> = {
    integrations,
    users,
    billing,
    audit,
    lgpd,
    notifications,
  }

  return (
    <div className="min-h-dvh pt-20 pb-12">
      <div className="max-w-5xl mx-auto px-4">
        {/* ── Header ────────────────────────────────────────────── */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 rounded-md bg-elevated border border-border flex items-center justify-center shrink-0">
            <Settings size={18} strokeWidth={1.5} className="text-gray-300" />
          </div>
          <div>
            <h1 className="text-heading-lg text-white leading-none">Administração</h1>
            <p className="text-caption text-gray-400 mt-0.5">
              Integrações, usuários, faturamento e configurações
            </p>
          </div>
        </div>

        {/* ── Tab bar ───────────────────────────────────────────── */}
        <TabGroup
          tabs={TABS}
          activeId={activeTab}
          onChange={(id) => setActiveTab(id as AdminTab)}
          className="mb-6"
        />

        {/* ── Tab panel ─────────────────────────────────────────── */}
        <RoomErrorBoundary key={activeTab}>
          <div
            className={cn(
              'animate-fade-in',
              'motion-reduce:animate-none'
            )}
          >
            {panelContent[activeTab]}
          </div>
        </RoomErrorBoundary>
      </div>
    </div>
  )
}
