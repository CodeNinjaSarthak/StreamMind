import { Skeleton } from '../Skeleton';

export function ClusterDetailsModal({ cluster, comments, onClose }) {
  const answers = cluster.answers ?? [];
  const latestAnswer = answers.length > 0 ? answers[answers.length - 1] : null;

  return (
    <div className="modal-overlay" onMouseDown={onClose}>
      <div className="modal modal-large" onMouseDown={e => e.stopPropagation()}>
        <h3>{cluster.title || 'Untitled Cluster'}</h3>
        <p className="hint">{cluster.comment_count ?? 0} questions in this cluster</p>

        <div className="cluster-comments-list">
          {comments === null ? (
            <div className="skeleton-list">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="skeleton-row">
                  <Skeleton className="sk-comment-author" />
                  <Skeleton className="sk-comment-text" />
                </div>
              ))}
            </div>
          ) : comments.length === 0 ? (
            <div className="empty-state">
              <span className="empty-state-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
              </span>
              <p className="empty-state-title">No questions assigned</p>
              <p className="empty-state-description">Questions will appear here once grouped into this cluster</p>
            </div>
          ) : (
            comments.map(c => (
              <div key={c.id} className="cluster-comment-item">
                <div className="cluster-comment-meta">
                  <span className="feed-item-author">{c.author_name || 'Unknown'}</span>
                  <span>{c._time}</span>
                </div>
                <span className="feed-item-text">{c.text}</span>
              </div>
            ))
          )}
        </div>

        {latestAnswer && (
          <div className="cluster-answer-box">
            <strong>Generated Answer</strong>
            <p style={{ marginTop: 6 }}>{latestAnswer.text}</p>
          </div>
        )}

        <div className="modal-actions">
          <button className="btn btn-sm" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
