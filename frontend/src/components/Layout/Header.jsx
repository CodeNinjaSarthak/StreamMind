import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../context/ThemeContext';

export function Header({ connected = false, reconnecting = false, activeSession = null }) {
  const { displayName, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/');
  }

  const dotClass = `connection-dot ${reconnecting ? 'reconnecting' : connected ? 'connected' : 'connecting'}`;

  return (
    <header className="app-header">
      <div className="header-wordmark">AI Doubt Manager</div>

      <div className="header-center">
        {activeSession && (
          <>
            <span className="header-session-name">{activeSession.title}</span>
            <span className="live-badge">
              <span className="live-badge-dot" />
              LIVE
            </span>
          </>
        )}
      </div>

      <div className="header-right">
        {activeSession && <span className={dotClass} title={reconnecting ? 'Reconnecting…' : connected ? 'Connected' : 'Connecting…'} />}
        {displayName && <span className="header-user-email">{displayName}</span>}
        <button
          onClick={toggleTheme}
          className="btn btn-sm"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? '☀' : '🌙'}
        </button>
        <Link to="/settings" className="btn btn-sm">Settings</Link>
        <button onClick={handleLogout} className="btn btn-sm">Logout</button>
      </div>
    </header>
  );
}
