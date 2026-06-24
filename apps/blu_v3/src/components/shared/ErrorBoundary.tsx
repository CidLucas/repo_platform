// GOAL: Melhorar qualidade do código | BEHAVIOR: B8 Error Boundaries | DECISÃO: extend
import React from 'react'

interface ErrorBoundaryProps {
  fallback: React.ReactNode
  children: React.ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    const componentName = this.constructor.name || 'ErrorBoundary'
    const timestamp = new Date().toISOString()
    console.error(
      `[ErrorBoundary:${componentName}] ${timestamp}`,
      { error, componentStack: errorInfo.componentStack }
    )
    this.props.onError?.(error, errorInfo)
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      return this.props.fallback
    }
    return this.props.children
  }
}
