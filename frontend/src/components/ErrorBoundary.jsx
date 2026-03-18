import { Component } from 'react';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <details>
            <summary>Error details</summary>
            <pre>{this.state.error?.message}</pre>
          </details>
          {/*
            Reload instead of setState({ hasError: false }): clearing state would immediately
            re-render the child, causing an infinite crash loop for structural errors
            (bad prop, null data, etc.). Reload is the safer default. Trade-off: any unsaved
            state (manual question drafts, in-progress edits) is lost, but this only triggers
            on a hard component crash.
          */}
          <button className="btn" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
