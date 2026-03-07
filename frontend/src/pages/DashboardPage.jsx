import { useState, useRef, useCallback, useEffect } from 'react';
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
import { AnalyticsPanel } from '../components/Dashboard/AnalyticsPanel';
import { QuotaBanner } from '../components/Dashboard/QuotaBanner';

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

  // Tab view: 'main' | 'analytics' — reset on session change
  const [view, setView] = useState('main');
  useEffect(() => { setView('main'); }, [activeSession?.id]);

  // Session-scoped event accumulator — survives WS reconnects, resets on session change
  const [sessionEvents, setSessionEvents] = useState([]);
  const [quotaAlert, setQuotaAlert] = useState(null);
  useEffect(() => { setSessionEvents([]); }, [activeSession?.id]);
  useEffect(() => { setQuotaAlert(null); }, [activeSession?.id]);
  useEffect(() => {
    if (!wsMessages || wsMessages.length === 0) return;
    const last = wsMessages[wsMessages.length - 1];
    if (!last) return;
    setSessionEvents(prev => [...prev.slice(-199), last]);
    if (last.type === 'quota_alert') {
      setQuotaAlert(prev => (prev === 'critical' ? 'critical' : 'warning'));
    } else if (last.type === 'quota_exceeded') {
      setQuotaAlert('critical');
    }
  }, [wsMessages]);

  return (
    <div className="app-shell">
      <Header connected={connected} reconnecting={reconnecting} activeSession={activeSession} />
      {quotaAlert && (
        <QuotaBanner
          level={quotaAlert}
          onDismiss={() => setQuotaAlert(null)}
        />
      )}
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
                <div className="tab-bar">
                  <button
                    className={`tab-btn${view === 'main' ? ' active' : ''}`}
                    onClick={() => setView('main')}
                  >
                    Questions &amp; Clusters
                  </button>
                  <button
                    className={`tab-btn${view === 'analytics' ? ' active' : ''}`}
                    onClick={() => setView('analytics')}
                  >
                    Analytics
                  </button>
                </div>

                {view === 'main' ? (
                  <div className="tab-view-panels">
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
                  </div>
                ) : (
                  <div className="analytics-scroll-wrapper">
                    <AnalyticsPanel
                      sessionId={activeSession.id}
                      token={token}
                      sessionEvents={sessionEvents}
                    />
                  </div>
                )}
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
