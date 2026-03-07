import { useState, useEffect } from 'react';
import { getSessionStats } from '../../services/api';
import { Skeleton } from '../Skeleton';

const REFETCH_EVENTS = new Set(['comment_created', 'cluster_created', 'answer_ready', 'answer_posted', 'comment_classified']);

export function MetricsCards({ sessionId, token, wsMessages }) {
  const [stats, setStats] = useState(null);
  const [isLoadingInitial, setIsLoadingInitial] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let stale = false;
    async function run() {
      if (!sessionId) {
        setStats(null);
        setIsLoadingInitial(false);
        return;
      }
      setIsLoadingInitial(true);
      setError(null);
      try {
        const data = await getSessionStats(sessionId, token);
        if (!stale) setStats(data);
      } catch (e) {
        if (!stale) setError(e.message);
      } finally {
        if (!stale) setIsLoadingInitial(false);
      }
    }
    run();
    return () => { stale = true; };
  }, [sessionId, token]);

  // WS-triggered refetch — does NOT set isLoadingInitial
  useEffect(() => {
    if (!sessionId || !wsMessages || wsMessages.length === 0) return;
    const last = wsMessages[wsMessages.length - 1];
    if (last && REFETCH_EVENTS.has(last.type)) {
      getSessionStats(sessionId, token)
        .then(data => { if (data) setStats(data); })
        .catch(() => {});
    }
  }, [wsMessages]);

  return (
    <section className="panel">
      <h2>Session Stats</h2>
      {isLoadingInitial && sessionId ? (
        <div className="metrics-grid">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="metric-card">
              <Skeleton className="sk-metric-value" />
              <Skeleton className="sk-metric-label" />
            </div>
          ))}
        </div>
      ) : error ? (
        <p className="error-msg">{error}</p>
      ) : !stats ? (
        <p className="hint">Start a session to see stats.</p>
      ) : (
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-value">{stats.total_comments ?? '—'}</div>
            <div className="metric-label">Total Comments</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{stats.questions ?? '—'}</div>
            <div className="metric-label">Questions</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{stats.clusters ?? '—'}</div>
            <div className="metric-label">Clusters</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{stats.answers_posted ?? '—'}</div>
            <div className="metric-label">Answers Posted</div>
          </div>
        </div>
      )}
    </section>
  );
}
