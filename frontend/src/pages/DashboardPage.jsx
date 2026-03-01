import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useWebSocket } from '../hooks/useWebSocket';
import { Header } from '../components/Layout/Header';
import { SessionList } from '../components/Dashboard/SessionList';
import { YouTubePanel } from '../components/Dashboard/YouTubePanel';
import { ManualInput } from '../components/Dashboard/ManualInput';
import { MetricsCards } from '../components/Dashboard/MetricsCards';
import { QuestionsFeed } from '../components/Dashboard/QuestionsFeed';
import { ClustersPanel } from '../components/Dashboard/ClustersPanel';

export function DashboardPage() {
  const { token } = useAuth();
  const [activeSession, setActiveSession] = useState(null);
  const { messages: wsMessages, connected } = useWebSocket(activeSession?.id, token);

  return (
    <div>
      <Header />
      <main className="app-main">
        <div className="panels-grid">
          <div className="left-column">
            <SessionList token={token} onSelect={setActiveSession} activeSession={activeSession} />
            <YouTubePanel token={token} />
            {activeSession && (
              <ManualInput sessionId={activeSession.id} token={token} />
            )}
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
