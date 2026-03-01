import { useState, useEffect } from 'react';
import { getSessionComments } from '../../services/api';

function getBadge(isQuestion) {
  if (isQuestion === true) return <span className="badge badge-question">Question</span>;
  if (isQuestion === false) return <span className="badge badge-not-question">Not a question</span>;
  return <span className="badge badge-classifying">Classifying...</span>;
}

export function QuestionsFeed({ sessionId, token, wsMessages }) {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchComments();
  }, [sessionId]);

  async function fetchComments() {
    try {
      setLoading(true);
      const data = await getSessionComments(sessionId, token, 100, 0);
      setComments(data || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Process WebSocket messages
  useEffect(() => {
    if (!wsMessages || wsMessages.length === 0) return;
    const last = wsMessages[wsMessages.length - 1];
    if (!last) return;

    if (last.type === 'comment_created') {
      setComments(prev => [last.data || last, ...prev]);
    } else if (last.type === 'comment_classified') {
      const { comment_id, is_question } = last.data || last;
      setComments(prev =>
        prev.map(c => c.id === comment_id ? { ...c, is_question } : c)
      );
    }
  }, [wsMessages]);

  return (
    <section className="panel">
      <h2>
        Live Feed{' '}
        <span className="badge">{comments.length}</span>
      </h2>
      {loading ? (
        <p>Loading...</p>
      ) : error ? (
        <p className="error-msg">{error}</p>
      ) : (
        <div className="questions-feed">
          {comments.length === 0 ? (
            <p className="empty-msg">No comments yet. Start a session to see live feed.</p>
          ) : (
            comments.map(c => (
              <div key={c.id} className="feed-item">
                <span className="feed-item-author">{c.author_name || 'Unknown'}</span>
                <span className="feed-item-text">{c.text}</span>
                <span className="feed-item-badge">{getBadge(c.is_question)}</span>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  );
}
