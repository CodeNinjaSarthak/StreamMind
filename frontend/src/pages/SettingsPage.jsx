import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/Layout/Header';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../context/ThemeContext';
import { changePassword } from '../services/api';
import { showToast } from '../hooks/useToast';

export function SettingsPage() {
  return (
    <div>
      <Header />
      <main className="app-main">
        <div className="settings-layout">
          <div className="settings-back">
            <Link to="/dashboard" className="btn btn-sm">← Dashboard</Link>
          </div>
          <h1 className="settings-title">Settings</h1>
          <ProfileSection />
          <PasswordSection />
          <PreferencesSection />
        </div>
      </main>
    </div>
  );
}

function ProfileSection() {
  const { userName, userEmail, updateProfile } = useAuth();
  const [name, setName] = useState(userName || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await updateProfile(name.trim());
      showToast('Profile updated!', 'success');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel settings-section">
      <h2>Profile</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Email <span className="hint">(read-only)</span>
          <input type="email" value={userEmail} disabled readOnly />
        </label>
        <label>
          Display Name
          <input type="text" value={name} onChange={e => setName(e.target.value)} required />
        </label>
        {error && <p className="error-msg">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Saving...' : 'Save Profile'}
        </button>
      </form>
    </section>
  );
}

function PasswordSection() {
  const { token } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    if (next !== confirm) { setError('Passwords do not match'); return; }
    if (next.length < 8) { setError('New password must be at least 8 characters'); return; }
    setSaving(true);
    setError('');
    try {
      await changePassword(current, next, token);
      showToast('Password changed!', 'success');
      setCurrent(''); setNext(''); setConfirm('');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel settings-section">
      <h2>Change Password</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Current Password
          <input type="password" value={current} onChange={e => setCurrent(e.target.value)} required />
        </label>
        <label>
          New Password <span className="hint">(min 8 chars)</span>
          <input type="password" value={next} onChange={e => setNext(e.target.value)} required minLength={8} />
        </label>
        <label>
          Confirm New Password
          <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required />
        </label>
        {error && <p className="error-msg">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Changing...' : 'Change Password'}
        </button>
      </form>
    </section>
  );
}

function PreferencesSection() {
  const { theme, toggleTheme } = useTheme();
  return (
    <section className="panel settings-section">
      <h2>Preferences</h2>
      <div className="settings-row">
        <div>
          <strong>Theme</strong>
          <p className="hint">Current: {theme === 'dark' ? 'Dark' : 'Light'} mode</p>
        </div>
        <button
          className="btn btn-sm"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? '☀ Light' : '🌙 Dark'}
        </button>
      </div>
    </section>
  );
}
