import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Toggle } from '@/components/primitives/Toggle'

interface PermissionToggleProps {
  userId: string
  label: string
  enabled: boolean
  description?: string
  disabled?: boolean
}

/**
 * Permission toggle for admin user management.
 * Optimistically updates and syncs via mutation.
 */
export function PermissionToggle({
  userId,
  label,
  enabled,
  description,
  disabled,
}: PermissionToggleProps) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: async (next: boolean) => {
      // Placeholder — real implementation would call supabase
      // to update user role/permissions in clientes_blu
      console.log('updatePermission', userId, label, next)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <div className="min-w-0">
        <p className="text-body-sm text-gray-200">{label}</p>
        {description && (
          <p className="text-caption-sm text-gray-500 mt-0.5">{description}</p>
        )}
      </div>
      <Toggle
        checked={enabled}
        onChange={(next) => mutation.mutate(next)}
        disabled={disabled || mutation.isPending}
      />
    </div>
  )
}
