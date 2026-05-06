import { cn } from '@/utils/cn'

interface Tab {
  id: string
  label: string
}

interface TabGroupProps {
  tabs: Tab[]
  activeId: string
  onChange: (id: string) => void
  accentColor?: string
  className?: string
}

export function TabGroup({ tabs, activeId, onChange, accentColor, className }: TabGroupProps) {
  return (
    <div
      role="tablist"
      className={cn('flex border-b border-border gap-1', className)}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeId
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              'px-4 py-2.5 text-body-sm transition-colors duration-normal cursor-pointer',
              'border-b-2 -mb-px',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500',
              'focus-visible:ring-offset-1 focus-visible:ring-offset-base',
              isActive
                ? 'text-white font-medium'
                : 'text-gray-300 hover:text-white border-transparent',
              isActive && !accentColor ? 'border-blu-500' : ''
            )}
            style={isActive && accentColor ? { borderBottomColor: accentColor } : undefined}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
