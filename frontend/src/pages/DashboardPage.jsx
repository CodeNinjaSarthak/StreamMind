import { useState, useRef, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useWebSocket } from '../hooks/useWebSocket';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { Header } from '../components/Layout/Header';
import { SessionList } from '../components/Dashboard/SessionList';
import { YouTubePanel } from '../components/Dashboard/YouTubePanel';
import { ManualInput } from '../components/Dashboard/ManualInput';
import { MetricsCards } from '../components/Dashboard/MetricsCards';
import { QuestionsFeed } from '../components/Dashboard/QuestionsFeed';
import { ClustersPanel } from '../components/Dashboard/ClustersPanel';
import { DocumentUpload } from '../components/Dashboard/DocumentUpload';

export function DashboardPage() {
  const { token } = useAuth();
  const [activeSession, setActiveSession] = useState(null);
  const { messages: wsMessages, connected, reconnecting } = useWebSocket(activeSession?.id, token);

  // Shortcut action refs
  const approveFirstRef = useRef(null);  // wired by ClustersPanel
  const titleInputRef = useRef(null);    // wired by SessionList (new session title input)
  const manualInputRef = useRef(null);   // wired by ManualInput (textarea)

  useKeyboardShortcuts({
    onNewSession: useCallback(() => titleInputRef.current?.focus(), []),
    onApproveFirst: useCallback(() => approveFirstRef.current?.(), []),
    onFocusSearch: useCallback(() => {
      if (activeSession) manualInputRef.current?.focus();
      else titleInputRef.current?.focus();
    }, [activeSession]),
  });

  return (
    <div>
      <Header connected={connected} reconnecting={reconnecting} activeSession={activeSession} />
      <main className="app-main">
        <div className="panels-grid">
          <div className="left-column">
            <SessionList
              token={token}
              onSelect={setActiveSession}
              activeSession={activeSession}
              titleInputRef={titleInputRef}
            />
            <YouTubePanel token={token} />
            {activeSession && (
              <ManualInput sessionId={activeSession.id} token={token} textareaRef={manualInputRef} />
            )}
            {activeSession && <DocumentUpload sessionId={activeSession.id} token={token} />}
            <MetricsCards sessionId={activeSession?.id} token={token} wsMessages={wsMessages} />
          </div>
          <div className="right-column">
            {activeSession ? (
              <>
                <QuestionsFeed
                  sessionId={activeSession.id}
                  token={token}
                  wsMessages={wsMessages}
                />
                <ClustersPanel
                  sessionId={activeSession.id}
                  token={token}
                  wsMessages={wsMessages}
                  approveFirstRef={approveFirstRef}
                />
              </>
            ) : (
              <p className="text-muted">Select or create a session to begin.</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
