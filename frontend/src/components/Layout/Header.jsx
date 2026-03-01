import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

export function Header() {
  const { displayName, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <header className="app-header">
      <div className="header-left">
        <span className="logo">AI Doubt Manager</span>
      </div>
      <div className="header-right">
        {displayName && <span className="user-name">{displayName}</span>}
        <button onClick={handleLogout} className="btn btn-sm">Logout</button>
      </div>
    </header>
  );
}
