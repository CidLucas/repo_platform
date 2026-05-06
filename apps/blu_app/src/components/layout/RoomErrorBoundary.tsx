import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'
import { cn } from '@/utils/cn'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class RoomErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[RoomErrorBoundary]', error, info.componentStack)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className={cn(
            'flex flex-col items-center justify-center py-16 px-6',
            'bg-surface border border-border rounded-md text-center'
          )}
        >
          <AlertTriangle size={32} className="text-urgent mb-4" strokeWidth={1.5} />
          <h2 className="text-heading-sm text-white mb-2">Algo deu errado</h2>
          <p className="text-body-sm text-gray-300 mb-6 max-w-xs">
            Ocorreu um erro inesperado nesta área. Tente novamente.
          </p>
          <button
            onClick={this.handleRetry}
            className={cn(
              'px-4 py-2 bg-blu-500 hover:bg-blu-600 text-white text-body-sm font-medium rounded',
              'transition-colors duration-normal cursor-pointer',
              'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:outline-none'
            )}
          >
            Tentar novamente
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
