import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { cn } from '@/utils/cn'

interface BackToLobbyProps {
  className?: string
}

export function BackToLobby({ className }: BackToLobbyProps) {
  const navigate = useNavigate()

  return (
    <button
      onClick={() => navigate('/')}
      className={cn(
        'inline-flex items-center gap-2 text-gray-300 hover:text-white',
        'text-body-sm transition-colors duration-normal cursor-pointer',
        'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:outline-none rounded',
        className
      )}
    >
      <ArrowLeft size={16} strokeWidth={1.5} />
      <span>Início</span>
    </button>
  )
}
