import { FileText, Download, ExternalLink } from 'lucide-react'
import { cn } from '@/utils/cn'

export interface DocumentPreviewItem {
  id: string
  title: string
  description?: string
  updatedAt: string
  url?: string
}

interface DocumentPreviewProps {
  document: DocumentPreviewItem
  onOpen?: (id: string) => void
  className?: string
}

export function DocumentPreview({ document, onOpen, className }: DocumentPreviewProps) {
  return (
    <div
      className={cn(
        'bg-surface border border-border rounded-md p-4',
        'hover:border-blu-500/40 transition-colors',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded bg-elevated flex items-center justify-center shrink-0">
          <FileText size={18} className="text-gray-400" strokeWidth={1.5} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-body-sm text-white font-medium truncate">{document.title}</p>
          {document.description && (
            <p className="text-caption text-gray-400 line-clamp-2 mt-0.5">
              {document.description}
            </p>
          )}
          <p className="text-caption-sm text-gray-500 mt-1">
            Atualizado {document.updatedAt}
          </p>
        </div>
      </div>
      <div className="flex gap-2 mt-3">
        {onOpen && (
          <button
            onClick={() => onOpen(document.id)}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded',
              'text-caption text-blu-400 hover:text-blu-300 border border-blu-500/30',
              'hover:bg-blu-500/10 transition-colors cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
          >
            <ExternalLink size={12} />
            Abrir
          </button>
        )}
        {document.url && (
          <a
            href={document.url}
            download
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded',
              'text-caption text-gray-400 hover:text-white border border-border',
              'hover:bg-elevated transition-colors cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
          >
            <Download size={12} />
            Baixar
          </a>
        )}
      </div>
    </div>
  )
}
