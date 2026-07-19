import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="h-full flex items-center justify-center p-8">
          <div className="text-center space-y-3">
            <div className="text-sm text-status-error font-medium">Component error</div>
            <div className="text-2xs text-text-tertiary max-w-md">{this.state.error?.message}</div>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="px-3 py-1.5 text-xs bg-surface-3 rounded-md text-text-secondary hover:text-text-primary transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
