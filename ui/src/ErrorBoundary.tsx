import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  failed: boolean;
}

export default class UiErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Claim map render failure", error, info.componentStack);
  }

  render() {
    if (!this.state.failed) {
      return this.props.children;
    }

    return (
      <main className="empty-state">
        <div className="empty-card" role="alert">
          <div className="eyebrow">claim-contract / optional UI</div>
          <h1>The claim map could not render.</h1>
          <p>
            The bundle passed loading but the interface hit an unexpected render
            failure. Reload the page; if the problem persists, verify the frontend
            build against the current repository revision.
          </p>
          <div className="recovery-actions">
            <button
              className="primary-button"
              onClick={() => window.location.reload()}
            >
              Reload claim map
            </button>
          </div>
        </div>
      </main>
    );
  }
}
