import { useState, useEffect, useRef } from 'react';
import { getSessionClusters, approveAnswer, editAnswer, getClusterComments } from '../../services/api';
import { showToast } from '../../hooks/useToast';
import { ClusterDetailsModal } from './ClusterDetailsModal';
import { Skeleton } from '../Skeleton';

const REFETCH_EVENTS = new Set(['cluster_created', 'cluster_updated', 'answer_ready', 'answer_posted']);

export function ClustersPanel({ sessionId, token, wsMessages, approveFirstRef }) {
  const [clusters, setClusters] = useState([]);
  const [isLoadingInitial, setIsLoadingInitial] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingAnswerId, setEditingAnswerId] = useState(null);
  const [editedText, setEditedText] = useState('');
  const [savingId, setSavingId] = useState(null);
  const [clusterFilter, setClusterFilter] = useState('all');
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [modalComments, setModalComments] = useState(null);
  const [expandedIds, setExpandedIds] = useState(new Set());
  const commentCache = useRef(new Map());

  async function fetchClusters() {
    const data = await getSessionClusters(sessionId, token);
    if (data) setClusters(data);
  }

  useEffect(() => {
    let stale = false;
    async function run() {
      setIsLoadingInitial(true);
      setError(null);
      try {
        const data = await getSessionClusters(sessionId, token);
        if (!stale) setClusters(data || []);
      } catch (e) {
        if (!stale) setError(e.message);
      } finally {
        if (!stale) setIsLoadingInitial(false);
      }
    }
    run();
    return () => { stale = true; };
  }, [sessionId, token]);

  // Wire approveFirstRef so DashboardPage keyboard shortcut can trigger approve
  useEffect(() => {
    if (!approveFirstRef) return;
    approveFirstRef.current = () => {
      const first = clusters.find(c => {
        const latest = c.answers?.[c.answers.length - 1];
        return latest && !latest.is_posted;
      });
      if (first) {
        const latest = first.answers[first.answers.length - 1];
        handleApprove(latest.id);
      }
    };
    return () => { approveFirstRef.current = null; };
  }, [clusters, approveFirstRef]);

  // WS-triggered refetch
  useEffect(() => {
    if (!wsMessages || wsMessages.length === 0) return;
    const last = wsMessages[wsMessages.length - 1];
    if (last && REFETCH_EVENTS.has(last.type)) {
      const affectedId = last.data?.cluster_id ?? last.data?.id ?? null;
      if (affectedId) {
        commentCache.current.delete(affectedId);
      } else {
        commentCache.current.clear();
      }
      fetchClusters().catch(() => {});
    }
  }, [wsMessages]);

  function toggleExpand(id) {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function openClusterModal(cluster) {
    setSelectedCluster(cluster);
    if (commentCache.current.has(cluster.id)) {
      setModalComments(commentCache.current.get(cluster.id));
      return;
    }
    setModalComments(null);
    try {
      const data = await getClusterComments(cluster.id, token);
      const processed = (data || []).map(c => ({
        ...c,
        _time: new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }));
      commentCache.current.set(cluster.id, processed);
      setModalComments(processed);
    } catch {
      setModalComments([]);
    }
  }

  async function handleApprove(answerId) {
    setLoading(true);
    try {
      await approveAnswer(answerId, token);
      await fetchClusters();
      showToast('Answer approved and posted!', 'success');
    } catch (err) {
      setError(err.message);
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  function startEdit(answer) {
    setEditingAnswerId(answer.id);
    setEditedText(answer.text);
  }

  function cancelEdit() {
    setEditingAnswerId(null);
    setEditedText('');
  }

  async function handleSaveEdit(answerId) {
    setSavingId(answerId);
    try {
      await editAnswer(answerId, editedText, token);
      await fetchClusters();
      setEditingAnswerId(null);
      setEditedText('');
      showToast('Answer updated.', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSavingId(null);
    }
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).catch(() => {});
  }

  const filteredClusters = clusters.filter(cluster => {
    if (clusterFilter === 'all') return true;
    const answers = cluster.answers ?? [];
    const latest = answers.length > 0 ? answers[answers.length - 1] : null;
    if (clusterFilter === 'approved') return latest?.is_posted === true;
    if (clusterFilter === 'pending') return !latest?.is_posted;
    return true;
  });

  return (
    <section className="panel panel-scrollable panel-clusters">
      <h2>
        Clusters &amp; Answers
        <span className="badge">{clusters.length}</span>
      </h2>

      <div className="filter-tabs">
        {['all', 'pending', 'approved'].map(tab => (
          <button
            key={tab}
            className={`filter-tab${clusterFilter === tab ? ' active' : ''}`}
            onClick={() => setClusterFilter(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {isLoadingInitial ? (
        <div className="clusters-list">
          {[1, 2, 3].map(i => (
            <div key={i} className="cluster-card">
              <div className="cluster-header">
                <Skeleton className="sk-cluster-title" />
                <Skeleton className="sk-cluster-count" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <p className="error-msg">{error}</p>
      ) : (
        <div className="clusters-list">
          {filteredClusters.length === 0 ? (
            <div className="empty-state">
              <span className="empty-state-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>
                  <line x1="12" y1="7" x2="5" y2="17"/><line x1="12" y1="7" x2="19" y2="17"/>
                  <line x1="5" y1="19" x2="19" y2="19"/>
                </svg>
              </span>
              <p className="empty-state-title">
                {clusters.length === 0 ? 'No clusters yet' : 'No clusters match this filter'}
              </p>
              {clusters.length === 0 && (
                <p className="empty-state-description">
                  Clusters form automatically once enough questions arrive
                </p>
              )}
            </div>
          ) : (
            filteredClusters.map(cluster => {
              const answers = cluster.answers || [];
              const latestAnswer = answers[answers.length - 1];
              const isEditing = latestAnswer && editingAnswerId === latestAnswer.id;
              const isExpanded = expandedIds.has(cluster.id);
              const isApproved = latestAnswer?.is_posted === true;

              return (
                <div
                  key={cluster.id}
                  className={`cluster-card${isApproved ? ' cluster-approved' : ''}${isExpanded ? ' expanded' : ''}`}
                >
                  <div className="cluster-header" onClick={() => toggleExpand(cluster.id)}>
                    <span className="cluster-title">
                      {cluster.title || 'Untitled Cluster'}
                    </span>
                    <span className="cluster-count">{cluster.comment_count || 0}q</span>
                    {isApproved && (
                      <span className="cluster-approved-badge">✓ POSTED</span>
                    )}
                    <span
                      className="cluster-expand-icon"
                      onClick={e => { e.stopPropagation(); openClusterModal(cluster); }}
                      title="View details"
                    >
                      ▼
                    </span>
                  </div>

                  <div className={`cluster-body${isExpanded ? ' expanded' : ''}`}>
                    <div className="cluster-body-inner">
                      {latestAnswer ? (
                        <>
                          {isEditing ? (
                            <textarea
                              value={editedText}
                              onChange={e => setEditedText(e.target.value)}
                              style={{ width: '100%', marginBottom: 8, minHeight: 80 }}
                            />
                          ) : (
                            <div className="cluster-answer">{latestAnswer.text}</div>
                          )}
                          <div style={{ marginBottom: 6 }}>
                            <span className={`badge ${latestAnswer.is_posted ? 'badge-posted' : 'badge-pending'}`}>
                              {latestAnswer.is_posted ? 'Posted' : 'Pending'}
                            </span>
                          </div>
                          <div className="cluster-actions">
                            {isEditing ? (
                              <>
                                <button
                                  className="btn btn-primary btn-sm"
                                  style={{ width: 'auto', marginTop: 0 }}
                                  onClick={() => handleSaveEdit(latestAnswer.id)}
                                  disabled={savingId === latestAnswer.id || !editedText.trim()}
                                >
                                  {savingId === latestAnswer.id ? 'Saving…' : 'Save'}
                                </button>
                                <button className="btn btn-sm" onClick={cancelEdit}>Cancel</button>
                              </>
                            ) : (
                              <>
                                <button
                                  className="btn btn-sm"
                                  onClick={() => copyToClipboard(latestAnswer.text)}
                                >
                                  Copy
                                </button>
                                {!latestAnswer.is_posted && (
                                  <>
                                    <button
                                      className="btn btn-sm"
                                      onClick={() => startEdit(latestAnswer)}
                                      disabled={loading}
                                    >
                                      Edit
                                    </button>
                                    <button
                                      className="btn btn-primary btn-sm"
                                      style={{ width: 'auto', marginTop: 0 }}
                                      onClick={() => handleApprove(latestAnswer.id)}
                                      disabled={loading}
                                    >
                                      {loading ? 'Posting…' : 'Approve & Post'}
                                    </button>
                                  </>
                                )}
                              </>
                            )}
                          </div>
                        </>
                      ) : (
                        <p className="hint">Generating answer…</p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {selectedCluster && (
        <ClusterDetailsModal
          cluster={selectedCluster}
          comments={modalComments}
          onClose={() => { setSelectedCluster(null); setModalComments(null); }}
        />
      )}
    </section>
  );
}
