import { useState, useEffect } from 'react';
import { getSessionComments } from '../../services/api';
import { Skeleton } from '../Skeleton';

const PAGE_SIZE = 20;

function getBadge(isQuestion) {
  if (isQuestion === true) return <span className="badge badge-question">Question</span>;
  if (isQuestion === false) return <span className="badge badge-not-question">Not a question</span>;
  return <span className="badge badge-classifying">Classifying...</span>;
}

export function QuestionsFeed({ sessionId, token, wsMessages }) {
  const [comments, setComments] = useState([]);
  const [isLoadingInitial, setIsLoadingInitial] = useState(true);
  const [error, setError] = useState(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Initial fetch — reset everything on session change
  useEffect(() => {
    let stale = false;
    setOffset(0);
    setSearchQuery('');
    setDebouncedQuery('');
    async function run() {
      setIsLoadingInitial(true);
      setError(null);
      try {
        const data = await getSessionComments(sessionId, token, PAGE_SIZE, 0);
        if (!stale && data) {
          setComments(data);
          setHasMore(data.length === PAGE_SIZE);
        }
      } catch (e) {
        if (!stale) setError(e.message);
      } finally {
        if (!stale) setIsLoadingInitial(false);
      }
    }
    run();
    return () => { stale = true; };
  }, [sessionId, token]);

  // Re-fetch when token refreshes while initial load is still pending
  useEffect(() => {
    if (!sessionId || !token || !isLoadingInitial) return;
    let stale = false;
    getSessionComments(sessionId, token, PAGE_SIZE, 0).then(data => {
      if (!stale && data) {
        setComments(data);
        setHasMore(data.length === PAGE_SIZE);
        setIsLoadingInitial(false);
      }
    });
    return () => { stale = true; };
  }, [token]);

  // Process WebSocket messages — skip until initial fetch is done
  useEffect(() => {
    if (isLoadingInitial) return;
    if (!wsMessages || wsMessages.length === 0) return;
    const last = wsMessages[wsMessages.length - 1];
    if (!last) return;

    if (last.type === 'comment_created') {
      setComments(prev => {
        if (prev.some(c => c.id === (last.data?.id ?? last.id))) return prev;
        return [last.data || last, ...prev];
      });
      // do NOT touch offset
    } else if (last.type === 'comment_classified') {
      const { comment_id, is_question } = last.data || last;
      setComments(prev =>
        prev.map(c => c.id === comment_id ? { ...c, is_question } : c)
      );
    }
  }, [wsMessages, isLoadingInitial]);

  async function loadMore() {
    if (loadingMore) return;
    setLoadingMore(true);
    const currentOffset = offset; // capture before async
    try {
      const data = await getSessionComments(sessionId, token, PAGE_SIZE, currentOffset + PAGE_SIZE);
      setComments(prev => [...prev, ...(data || [])]);
      setOffset(currentOffset + PAGE_SIZE);
      setHasMore((data || []).length === PAGE_SIZE);
    } catch { }
    finally { setLoadingMore(false); }
  }

  const filteredComments = debouncedQuery
    ? comments.filter(c => c.text.toLowerCase().includes(debouncedQuery.toLowerCase()))
    : comments;

  return (
    <section className="panel panel-scrollable panel-feed">
      <h2>
        Live Feed{' '}
        <span className="badge">{comments.length}</span>
      </h2>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search questions..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
      </div>

      <p className="search-result-count">
        {debouncedQuery
          ? `Searching ${filteredComments.length} of ${comments.length} loaded`
          : `${comments.length} loaded`}
      </p>

      {isLoadingInitial ? (
        <div className="questions-feed">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="feed-item">
              <Skeleton className="sk-feed-author" />
              <Skeleton className="sk-feed-text" />
              <Skeleton className="sk-feed-badge" />
            </div>
          ))}
        </div>
      ) : error ? (
        <p className="error-msg">{error}</p>
      ) : (
        <>
          <div className="questions-feed">
            {filteredComments.length === 0 ? (
              <div className="empty-state">
                <span className="empty-state-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                </span>
                <p className="empty-state-title">
                  {debouncedQuery ? 'No matching questions' : 'No questions yet'}
                </p>
                {!debouncedQuery && (
                  <p className="empty-state-description">
                    Questions from your live stream will appear here
                  </p>
                )}
              </div>
            ) : (
              filteredComments.map(c => (
                <div key={c.id} className="feed-item">
                  <span className="feed-item-author">{c.author_name || 'Unknown'}</span>
                  <span className="feed-item-text">{c.text}</span>
                  <span className="feed-item-badge">{getBadge(c.is_question)}</span>
                </div>
              ))
            )}
          </div>

          {!debouncedQuery && hasMore && (
            <button
              className="load-more-btn"
              onClick={loadMore}
              disabled={loadingMore}
            >
              {loadingMore ? 'Loading...' : 'Load More'}
            </button>
          )}
        </>
      )}
    </section>
  );
}
