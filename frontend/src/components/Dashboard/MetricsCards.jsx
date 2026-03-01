import { useState, useEffect } from 'react';
import { getSessionStats } from '../../services/api';

const REFETCH_EVENTS = new Set(['comment_created', 'cluster_created', 'answer_ready', 'answer_posted', 'comment_classified']);

export function MetricsCards({ sessionId, token, wsMessages }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (sessionId) {
      fetchStats();
    } else {
      setStats(null);
      setLoading(false);
    }
  }, [sessionId]);

  async function fetchStats() {
    try {
      setLoading(true);
      const data = await getSessionStats(sessionId, token);
      setStats(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!sessionId || !wsMessages || wsMessages.length === 0) return;
    const last = wsMessages[wsMessages.length - 1];
    if (last && REFETCH_EVENTS.has(last.type)) {
      fetchStats();
    }
  }, [wsMessages]);

  return (
    <section className="panel">
      <h2>Session Stats</h2>
      {loading ? (
        <p>Loading...</p>
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
