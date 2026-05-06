import { useState, useRef, useEffect } from 'react'
import { Search, X } from 'lucide-react'
import { cn } from '@/utils/cn'

interface GlobalSearchProps {
  className?: string
}

export function GlobalSearch({ className }: GlobalSearchProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        aria-label="Abrir busca"
        className={cn(
          'flex items-center justify-center w-9 h-9 rounded',
          'text-gray-300 hover:text-white hover:bg-elevated',
          'transition-colors duration-normal cursor-pointer',
          'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:outline-none',
          className
        )}
      >
        <Search size={18} strokeWidth={1.5} />
      </button>
    )
  }

  return (
    <div
      className={cn(
        'flex items-center gap-2 bg-elevated border border-border rounded px-3',
        'transition-all duration-normal',
        className
      )}
    >
      <Search size={16} strokeWidth={1.5} className="text-gray-400 shrink-0" />
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Buscar..."
        className="bg-transparent text-white text-body-sm placeholder:text-gray-400
          focus:outline-none w-40 py-2"
      />
      <button
        onClick={() => { setOpen(false); setQuery('') }}
        aria-label="Fechar busca"
        className="text-gray-400 hover:text-white cursor-pointer transition-colors duration-fast"
      >
        <X size={14} />
      </button>
    </div>
  )
}
