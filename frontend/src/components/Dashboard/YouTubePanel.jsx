import { useState, useEffect, useRef } from 'react';
import { getYouTubeStatus, getYouTubeAuthURL, disconnectYouTube } from '../../services/api';

export function YouTubePanel({ token }) {
  const [ytStatus, setYtStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const pollIntervalRef = useRef(null);
  const messageHandlerRef = useRef(null);

  useEffect(() => () => {
    clearInterval(pollIntervalRef.current);
    if (messageHandlerRef.current) {
      window.removeEventListener('message', messageHandlerRef.current);
      messageHandlerRef.current = null;
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, []);

  async function fetchStatus() {
    try {
      setLoading(true);
      const status = await getYouTubeStatus(token);
      setYtStatus(status);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleConnect() {
    setActionLoading(true);
    try {
      const data = await getYouTubeAuthURL(token);
      const popup = window.open(data.url, 'youtube_oauth', 'width=600,height=700,noopener');

      const handler = (e) => {
        if (e.origin !== window.location.origin) return;
        if (e.data?.type === 'youtube_oauth_complete') {
          messageHandlerRef.current = null;
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          popup?.close();
          fetchStatus();
          setActionLoading(false);
        }
      };
      messageHandlerRef.current = handler;
      window.addEventListener('message', handler, { once: true });

      pollIntervalRef.current = setInterval(() => {
        if (popup && popup.closed) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          fetchStatus();
          setActionLoading(false);
        }
      }, 500);
    } catch (e) {
      setError(e.message);
      setActionLoading(false);
    }
  }

  async function handleDisconnect() {
    setActionLoading(true);
    try {
      await disconnectYouTube(token);
      await fetchStatus();
    } catch (e) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>YouTube</h2>
      {loading ? (
        <p className="hint">Loading…</p>
      ) : error ? (
        <p className="error-msg">{error}</p>
      ) : (
        <>
          <div className="yt-status-row">
            <span className={`badge ${ytStatus?.connected ? 'badge-connected' : 'badge-disconnected'}`}>
              {ytStatus?.connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          {ytStatus?.connected ? (
            <>
              {ytStatus.expires_at && (
                <p className="hint">Expires: {new Date(ytStatus.expires_at).toLocaleString()}</p>
              )}
              <button
                onClick={handleDisconnect}
                className="btn btn-danger-sm"
                disabled={actionLoading}
              >
                {actionLoading ? 'Disconnecting…' : 'Disconnect'}
              </button>
            </>
          ) : (
            <button
              onClick={handleConnect}
              className="btn btn-primary"
              disabled={actionLoading}
            >
              {actionLoading ? 'Connecting…' : 'Connect YouTube'}
            </button>
          )}
        </>
      )}
    </section>
  );
}
