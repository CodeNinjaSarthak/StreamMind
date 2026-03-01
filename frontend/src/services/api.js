/**
 * API service — named exports, no class.
 * Base helper redirects to /login on 401.
 */

async function apiFetch(path, options = {}, token = null) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    window.location.href = '/login';
    return;
  }

  if (res.status === 429) {
    throw new Error('rate_limit');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.message || `HTTP ${res.status}`);
  }

  return res.status === 204 ? null : res.json();
}

// Auth
export const login = (email, password) =>
  apiFetch('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });

export const register = (email, password, name) =>
  apiFetch('/api/v1/auth/register', { method: 'POST', body: JSON.stringify({ email, password, name }) });

export const logout = (token) =>
  apiFetch('/api/v1/auth/logout', { method: 'POST' }, token);

// Sessions
export const getSessions = (token) =>
  apiFetch('/api/v1/sessions/', {}, token);

export const createSession = (data, token) =>
  apiFetch('/api/v1/sessions/', { method: 'POST', body: JSON.stringify(data) }, token);

export const endSession = (id, token) =>
  apiFetch(`/api/v1/sessions/${id}/end`, { method: 'POST' }, token);

export const getSessionComments = (sessionId, token, limit = 100, offset = 0) =>
  apiFetch(`/api/v1/sessions/${sessionId}/comments?limit=${limit}&offset=${offset}`, {}, token);

export const getSessionClusters = (sessionId, token) =>
  apiFetch(`/api/v1/sessions/${sessionId}/clusters`, {}, token);

export const getSessionStats = (sessionId, token) =>
  apiFetch(`/api/v1/dashboard/sessions/${sessionId}/stats`, {}, token);

// YouTube
export const getYouTubeAuthURL = (token) =>
  apiFetch('/api/v1/youtube/auth/url?return_url=%2F', {}, token);

export const getYouTubeStatus = (token) =>
  apiFetch('/api/v1/youtube/auth/status', {}, token);

export const disconnectYouTube = (token) =>
  apiFetch('/api/v1/youtube/auth/disconnect', { method: 'DELETE' }, token);

// Dashboard
export const submitManualQuestion = (sessionId, text, token) =>
  apiFetch(
    `/api/v1/dashboard/sessions/${sessionId}/manual-question`,
    { method: 'POST', body: JSON.stringify({ text }) },
    token
  );

export const approveAnswer = (answerId, token) =>
  apiFetch(`/api/v1/dashboard/answers/${answerId}/approve`, { method: 'POST' }, token);

// RAG Documents
// Note: uses raw fetch — apiFetch sets Content-Type: application/json which
// breaks multipart/form-data boundary. The browser sets the correct header itself.
export async function uploadDocument(file, token) {
  const formData = new FormData();
  formData.append('file', file);
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch('/api/v1/rag/documents', { method: 'POST', headers, body: formData });
  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    window.location.href = '/login';
    return;
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.message || `HTTP ${res.status}`);
  }
  return res.json();
}

export const getDocuments = (token) =>
  apiFetch('/api/v1/rag/documents', {}, token);

export const deleteDocument = (documentId, token) =>
  apiFetch(`/api/v1/rag/documents/${documentId}`, { method: 'DELETE' }, token);
