import { useState, useEffect } from 'react';
import { getSessions, createSession, endSession } from '../../services/api';

export function SessionList({ token, onSelect, activeSession, titleInputRef }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Create session form state
  const [title, setTitle] = useState('');
  const [videoId, setVideoId] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  // End session state
  const [ending, setEnding] = useState(false);
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchSessions();
  }, []);

  async function fetchSessions() {
    try {
      setLoading(true);
      const data = await getSessions(token);
      setSessions(data || []);
      // Auto-select first active session if none selected
      if (!activeSession) {
        const active = (data || []).find(s => s.is_active);
        if (active) onSelect(active);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setCreateError('');
    setCreating(true);
    try {
      const session = await createSession(
        { title: title.trim(), youtube_video_id: videoId.trim() || null },
        token
      );
      setTitle('');
      setVideoId('');
      setSessions(prev => [session, ...prev]);
      onSelect(session);
    } catch (e) {
      setCreateError(e.message || 'Failed to create session');
    } finally {
      setCreating(false);
    }
  }

  async function handleEnd() {
    if (!activeSession) return;
    setEnding(true);
    setShowEndConfirm(false);
    try {
      await endSession(activeSession.id, token);
      setSessions(prev => prev.map(s => s.id === activeSession.id ? { ...s, is_active: false } : s));
      onSelect(null);
    } catch {
      // ignore
    } finally {
      setEnding(false);
    }
  }

  return (
    <section className="panel">
      <h2>Session</h2>

      {showEndConfirm && (
        <div className="modal-overlay" onClick={() => setShowEndConfirm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>End session?</h3>
            <p>This will stop YouTube polling and end the session. This cannot be undone.</p>
            <div className="modal-actions">
              <button className="btn btn-sm" onClick={() => setShowEndConfirm(false)}>
                Cancel
              </button>
              <button className="btn btn-danger btn-sm" onClick={handleEnd} disabled={ending}>
                {ending ? 'Ending...' : 'End Session'}
              </button>
            </div>
          </div>
        </div>
      )}

      {activeSession ? (
        <div>
          <div className="session-info">
            <strong>{activeSession.title}</strong>
            <span className="badge badge-active">Live</span>
          </div>
          {activeSession.youtube_video_id ? (
            <p className="hint">YouTube: {activeSession.youtube_video_id}</p>
          ) : (
            <p className="hint">Manual mode (no YouTube video)</p>
          )}
          <button
            onClick={() => setShowEndConfirm(true)}
            className="btn btn-danger"
            disabled={ending}
          >
            {ending ? 'Ending...' : 'End Session'}
          </button>
          <button onClick={() => onSelect(null)} className="btn" style={{ marginLeft: 8 }}>
            Switch Session
          </button>
        </div>
      ) : (
        <div>
          <form onSubmit={handleCreate}>
            <label>
              Session Title
              <input
                ref={titleInputRef}
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Math Live Class"
                required
              />
            </label>
            <label>
              YouTube Video ID <span className="hint">(optional)</span>
              <input
                type="text"
                value={videoId}
                onChange={e => setVideoId(e.target.value)}
                placeholder="dQw4w9WgXcQ"
              />
            </label>
            {createError && <p className="error-msg">{createError}</p>}
            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? 'Starting...' : 'Start Session'}
            </button>
          </form>

          {loading ? (
            <p style={{ marginTop: 12, color: 'var(--color-muted)', fontSize: 13 }}>Loading sessions...</p>
          ) : error ? (
            <p className="error-msg" style={{ marginTop: 8 }}>{error}</p>
          ) : sessions.length > 0 ? (
            <div style={{ marginTop: 16 }}>
              <select
                className="session-filter"
                value={filter}
                onChange={e => setFilter(e.target.value)}
              >
                <option value="all">All Sessions</option>
                <option value="active">Active Only</option>
                <option value="ended">Ended Only</option>
              </select>
              {(() => {
                const displayedSessions = sessions.filter(s => {
                  if (filter === 'active') return s.is_active;
                  if (filter === 'ended') return !s.is_active;
                  return true;
                });
                return displayedSessions.length > 0 ? displayedSessions.map(s => (
                  <div
                    key={s.id}
                    onClick={() => onSelect(s)}
                    style={{
                      padding: '6px 8px',
                      fontSize: 12,
                      color: 'var(--color-muted)',
                      borderBottom: '1px solid var(--color-border)',
                      cursor: 'pointer',
                    }}
                  >
                    {s.title}
                    {s.is_active && <span className="badge badge-active" style={{ marginLeft: 6 }}>Live</span>}
                  </div>
                )) : (
                  <p className="hint" style={{ marginTop: 8 }}>No sessions match this filter.</p>
                );
              })()}
            </div>
          ) : !loading && !error ? (
            <div className="empty-state" style={{ padding: '16px 0' }}>
              <span className="empty-icon">🎓</span>
              <p>No sessions yet</p>
              <p className="empty-hint">Create your first session to start managing questions</p>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
