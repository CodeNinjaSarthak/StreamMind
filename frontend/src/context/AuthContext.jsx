import { createContext, useState } from 'react';
import {
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  updateProfile as apiUpdateProfile,
} from '../services/api';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('userEmail') || '');
  const [userName, setUserName] = useState(() => localStorage.getItem('userName') || '');

  async function login(email, password) {
    const data = await apiLogin(email, password);
    // data = { access_token, refresh_token, token_type, expires_in }
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('userEmail', email);
    setToken(data.access_token);
    setUserEmail(email);
  }

  async function register(email, password, name) {
    const user = await apiRegister(email, password, name);
    // user = { id, email, name, ... }
    localStorage.setItem('userName', user.name || name);
    setUserName(user.name || name);
    await login(email, password);
  }

  async function logout() {
    try { await apiLogout(token); } catch (_) {}
    localStorage.removeItem('token');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    setToken(null);
    setUserEmail('');
    setUserName('');
  }

  async function updateProfile(name) {
    const updated = await apiUpdateProfile({ name }, token);
    localStorage.setItem('userName', updated.name);
    setUserName(updated.name);
    return updated;
  }

  const displayName = userName || userEmail;

  return (
    <AuthContext.Provider value={{
      token,
      displayName,
      userEmail,
      userName,
      login,
      logout,
      register,
      isAuthenticated: !!token,
      updateProfile,
    }}>
      {children}
    </AuthContext.Provider>
  );
}
