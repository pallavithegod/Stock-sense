import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { StatePanel } from './StatePanel'

type ErrorBoundaryProps = {
  children: ReactNode
}

type ErrorBoundaryState = {
  message: string | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { message: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { message: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Page render failed', error, info.componentStack)
  }

  render() {
    if (this.state.message) {
      return (
        <StatePanel
          description={`${this.state.message}. Refresh the page or switch sections from the navigation.`}
          title="This page could not render"
        />
      )
    }

    return this.props.children
  }
}
