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

  // Sidebar collapse state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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
      <div className="app-body">
        <aside className={`app-sidebar${sidebarCollapsed ? ' collapsed' : ''}`}>
          <div className="sidebar-content">
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
          </div>
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarCollapsed(c => !c)}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15,18 9,12 15,6" />
            </svg>
          </button>
        </aside>

        <main className="app-main">
          {/* Column 1 — Live Feed */}
          <div className="main-col">
            {activeSession ? (
              <QuestionsFeed
                sessionId={activeSession.id}
                token={token}
                wsMessages={wsMessages}
              />
            ) : (
              <div className="empty-state" style={{ padding: '48px 24px' }}>
                <p className="empty-state-title">LIVE FEED</p>
                <p className="empty-state-description">Select a session to see incoming questions</p>
              </div>
            )}
          </div>

          {/* Column 2 — Clusters */}
          <div className="main-col">
            {activeSession ? (
              <ClustersPanel
                sessionId={activeSession.id}
                token={token}
                wsMessages={wsMessages}
                approveFirstRef={approveFirstRef}
              />
            ) : (
              <div className="empty-state" style={{ padding: '48px 24px' }}>
                <p className="empty-state-title">CLUSTERS</p>
                <p className="empty-state-description">Question clusters will appear here</p>
              </div>
            )}
          </div>

          {/* Column 3 — Stats + Analytics */}
          <div className="main-col col-scrollable">
            <MetricsCards sessionId={activeSession?.id} token={token} wsMessages={wsMessages} />
            {activeSession && (
              <AnalyticsPanel
                sessionId={activeSession.id}
                token={token}
                sessionEvents={sessionEvents}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
