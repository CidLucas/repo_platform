import { useState } from 'react'
import { User, ChevronDown, ChevronUp, Shield, ShieldCheck } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Badge } from '@/components/primitives/Badge'
import { Avatar } from '@/components/primitives/Avatar'
import { Divider } from '@/components/primitives/Divider'
import { PermissionToggle } from './PermissionToggle'
import type { ClienteBlu } from '@/types/user'
import { formatShortDate } from '@/utils/format'

// ── Tier badge ─────────────────────────────────────────────────────────────

const TIER_VARIANT: Record<ClienteBlu['tier'], 'ok' | 'attention' | 'urgent' | 'info'> = {
  free: 'info',
  starter: 'ok',
  growth: 'attention',
  enterprise: 'urgent',
}

const TIER_LABEL: Record<ClienteBlu['tier'], string> = {
  free: 'Free',
  starter: 'Starter',
  growth: 'Growth',
  enterprise: 'Enterprise',
}

// ── UserRow ────────────────────────────────────────────────────────────────

interface UserRowProps {
  user: ClienteBlu
  isOwner?: boolean
}

function UserRow({ user, isOwner }: UserRowProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-surface border border-border rounded-md overflow-hidden">
      {/* Header row */}
      <button
        className={cn(
          'w-full flex items-center gap-3 px-4 py-3',
          'hover:bg-elevated transition-colors duration-normal cursor-pointer',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:ring-inset'
        )}
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <Avatar name={user.name ?? user.email ?? undefined} size="sm" />

        <div className="flex-1 min-w-0 text-left">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-body-sm font-medium text-white truncate">
              {user.name ?? 'Sem nome'}
            </span>
            {isOwner && (
              <span className="inline-flex items-center gap-1 text-caption-sm text-blu-400">
                <ShieldCheck size={12} strokeWidth={2} />
                Proprietário
              </span>
            )}
          </div>
          <p className="text-caption text-gray-400 truncate">{user.email ?? '—'}</p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Badge variant={TIER_VARIANT[user.tier]}>{TIER_LABEL[user.tier]}</Badge>
          {expanded ? (
            <ChevronUp size={16} strokeWidth={1.5} className="text-gray-400" />
          ) : (
            <ChevronDown size={16} strokeWidth={1.5} className="text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded permissions */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-border/60 animate-fade-in">
          <p className="text-caption-sm text-gray-500 uppercase tracking-wider mt-3 mb-2">
            Permissões
          </p>
          <div className="divide-y divide-border/40">
            <PermissionToggle
              userId={user.id}
              label="Acesso a Aprovações"
              description="Pode aprovar e rejeitar decisões dos agentes"
              enabled={true}
              disabled={isOwner}
            />
            <PermissionToggle
              userId={user.id}
              label="Acesso a Configurações"
              description="Pode alterar configurações e integrações"
              enabled={isOwner ?? false}
              disabled={isOwner}
            />
            <PermissionToggle
              userId={user.id}
              label="Acesso a Faturamento"
              description="Pode visualizar e alterar plano"
              enabled={isOwner ?? false}
              disabled={isOwner}
            />
          </div>
          <p className="text-caption-sm text-gray-600 mt-3">
            Membro desde {formatShortDate(user.created_at)}
          </p>
        </div>
      )}
    </div>
  )
}

// ── UserTable ──────────────────────────────────────────────────────────────

interface UserTableProps {
  users: ClienteBlu[]
  loading?: boolean
  currentUserId?: string
}

export function UserTable({ users, loading, currentUserId }: UserTableProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <div
            key={i}
            className="h-16 bg-surface border border-border rounded-md"
            style={{
              backgroundImage:
                'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.03) 50%, transparent 100%)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 2s linear infinite',
            }}
          />
        ))}
      </div>
    )
  }

  if (users.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <User size={32} strokeWidth={1} className="mx-auto mb-3 opacity-40" />
        <p className="text-body-sm">Nenhum usuário encontrado.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <Shield size={16} strokeWidth={1.5} className="text-gray-400" />
        <p className="text-body-sm text-gray-300">
          {users.length} {users.length === 1 ? 'usuário' : 'usuários'} com acesso
        </p>
      </div>
      {users.map((user) => (
        <UserRow
          key={user.id}
          user={user}
          isOwner={user.external_user_id === currentUserId}
        />
      ))}
      <Divider className="my-4" />
      <p className="text-caption text-gray-500">
        Convites e gerenciamento de múltiplos usuários disponíveis nos planos Growth e Enterprise.
      </p>
    </div>
  )
}
