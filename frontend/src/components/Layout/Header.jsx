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

  return (
    <header className="app-header">
      <div className="header-left">
        <span className="logo">AI Doubt Manager</span>
      </div>
      <div className="header-right" style={{ gap: 8 }}>
        {activeSession && (
          <span className={`connection-status ${reconnecting ? 'reconnecting' : connected ? 'connected' : 'connecting'}`}>
            {reconnecting ? '🟡 Reconnecting...' : connected ? '🟢 Connected' : '⚪ Connecting...'}
          </span>
        )}
        {displayName && <span className="user-name">{displayName}</span>}
        <button
          onClick={toggleTheme}
          className="btn btn-sm"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? '☀ Light' : '🌙 Dark'}
        </button>
        <Link to="/settings" className="btn btn-sm">Settings</Link>
        <button onClick={handleLogout} className="btn btn-sm">Logout</button>
      </div>
    </header>
  );
}
