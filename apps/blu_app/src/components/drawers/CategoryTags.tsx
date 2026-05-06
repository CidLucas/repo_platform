import { cn } from '@/utils/cn'

interface CategoryTagsProps {
  categories: string[]
  active: string
  onChange: (category: string) => void
  allLabel?: string
  className?: string
}

/**
 * Horizontal scrollable filter strip.
 * [Todos] [Categoria1] [Categoria2] …
 */
export function CategoryTags({
  categories,
  active,
  onChange,
  allLabel = 'Todos',
  className,
}: CategoryTagsProps) {
  const all = [allLabel, ...categories]

  return (
    <div
      className={cn(
        'flex gap-2 overflow-x-auto py-2 px-4',
        'scroll-container',
        // Hide scrollbar but keep scroll
        '[&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]',
        className
      )}
    >
      {all.map((cat) => {
        const isActive = cat === active || (cat === allLabel && active === allLabel)
        return (
          <button
            key={cat}
            onClick={() => onChange(cat)}
            className={cn(
              'shrink-0 px-3 py-1 rounded-full text-caption font-medium',
              'transition-colors duration-normal cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500',
              isActive
                ? 'bg-blu-500/20 text-blu-300 border border-blu-500/40'
                : 'bg-elevated text-gray-400 border border-border hover:text-white hover:border-border'
            )}
          >
            {cat}
          </button>
        )
      })}
    </div>
  )
}
