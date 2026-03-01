import { useState, useEffect } from 'react';
import { getSessionClusters, approveAnswer } from '../../services/api';

const REFETCH_EVENTS = new Set(['cluster_created', 'cluster_updated', 'answer_ready', 'answer_posted']);

export function ClustersPanel({ sessionId, token, wsMessages }) {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [approvingId, setApprovingId] = useState(null);

  useEffect(() => {
    fetchClusters();
  }, [sessionId, token]);

  async function fetchClusters() {
    try {
      setLoading(true);
      const data = await getSessionClusters(sessionId, token);
      setClusters(data || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!wsMessages || wsMessages.length === 0) return;
    const last = wsMessages[wsMessages.length - 1];
    if (last && REFETCH_EVENTS.has(last.type)) {
      fetchClusters();
    }
  }, [wsMessages]);

  async function handleApprove(answerId) {
    setApprovingId(answerId);
    try {
      await approveAnswer(answerId, token);
      // Optimistic update: flip is_posted immediately so the badge changes
      // and the button disappears without waiting for a re-fetch.
      setClusters(prev =>
        prev.map(cluster => ({
          ...cluster,
          answers: cluster.answers.map(a =>
            a.id === answerId ? { ...a, is_posted: true } : a
          ),
        }))
      );
      // Silent background re-fetch to sync canonical server state.
      const data = await getSessionClusters(sessionId, token);
      if (data) setClusters(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setApprovingId(null);
    }
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).catch(() => {});
  }

  return (
    <section className="panel">
      <h2>Clusters &amp; Answers</h2>
      {loading ? (
        <p>Loading...</p>
      ) : error ? (
        <p className="error-msg">{error}</p>
      ) : (
        <div className="clusters-list">
          {clusters.length === 0 ? (
            <p className="empty-msg">No clusters yet. Questions need to be classified first.</p>
          ) : (
            clusters.map(cluster => {
              const answers = cluster.answers || [];
              const latestAnswer = answers[answers.length - 1];
              return (
                <div key={cluster.id} className="cluster-card">
                  <div className="cluster-header">
                    <span className="cluster-title">{cluster.title || 'Untitled Cluster'}</span>
                    <span className="cluster-count">{cluster.comment_count || 0} questions</span>
                  </div>
                  {latestAnswer ? (
                    <>
                      <div className="cluster-answer">{latestAnswer.text}</div>
                      <div style={{ marginBottom: 6 }}>
                        <span className={`badge ${latestAnswer.is_posted ? 'badge-posted' : 'badge-pending'}`}>
                          {latestAnswer.is_posted ? 'Posted' : 'Pending'}
                        </span>
                      </div>
                      <div className="cluster-actions">
                        <button
                          className="btn btn-sm"
                          onClick={() => copyToClipboard(latestAnswer.text)}
                        >
                          Copy
                        </button>
                        {!latestAnswer.is_posted && (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handleApprove(latestAnswer.id)}
                            disabled={approvingId === latestAnswer.id}
                          >
                            {approvingId === latestAnswer.id ? 'Posting...' : 'Approve & Post'}
                          </button>
                        )}
                      </div>
                    </>
                  ) : (
                    <p className="hint">Generating answer...</p>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </section>
  );
}
