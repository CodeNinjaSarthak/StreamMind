/**
 * API service — named exports, no class.
 * Base helper redirects to /login on 401.
 */

let refreshPromise = null;

export async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refreshToken');
  if (!refreshToken) return null;
  try {
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      console.error(`Token refresh failed: HTTP ${res.status}`);
      localStorage.removeItem('refreshToken');
      handleUnauthorized();
      return null;
    }
    const data = await res.json();
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('refreshToken', data.refresh_token);
    return data.access_token;
  } catch (err) {
    console.error('Token refresh error:', err);
    localStorage.removeItem('refreshToken');
    handleUnauthorized();
    return null;
  }
}

function handleUnauthorized() {
  localStorage.removeItem('token');
  localStorage.removeItem('userEmail');
  localStorage.removeItem('userName');
  window.location.href = '/login';
}

async function apiFetch(path, options = {}, token = null) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers });

  if (res.status === 401) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }
    const newToken = await refreshPromise;
    if (newToken) {
      const retryHeaders = { ...headers, Authorization: `Bearer ${newToken}` };
      const retryRes = await fetch(path, { ...options, headers: retryHeaders });
      if (!retryRes.ok) {
        if (retryRes.status === 401) {
          handleUnauthorized();
          return;
        }
        const body = await retryRes.json().catch(() => ({}));
        throw new Error(body.detail || body.message || `HTTP ${retryRes.status}`);
      }
      return retryRes.status === 204 ? null : retryRes.json();
    }
    handleUnauthorized();
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

export const getSessionAnalytics = (sessionId, token) =>
  apiFetch(`/api/v1/sessions/${sessionId}/analytics`, {}, token);

// Paginated comment fetcher — prevents silent truncation on large sessions
export async function fetchAllComments(sessionId, token) {
  const PAGE = 500;
  let offset = 0;
  const all = [];
  while (true) {
    const page = await getSessionComments(sessionId, token, PAGE, offset);
    if (!page || page.length === 0) break;
    all.push(...page);
    if (page.length < PAGE) break;
    offset += PAGE;
  }
  return all;
}

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

export const editAnswer = (answerId, text, token) =>
  apiFetch(`/api/v1/dashboard/answers/${answerId}`, {
    method: 'PATCH',
    body: JSON.stringify({ text }),
  }, token);

// RAG Documents
export const getDocuments = ({ token, sessionId = null }) =>
  apiFetch(
    sessionId ? `/api/v1/rag/documents?session_id=${sessionId}` : '/api/v1/rag/documents',
    {},
    token
  );

export function uploadDocument(sessionId, file, token, onProgress = () => {}, xhrRef = null) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    if (xhrRef) xhrRef.current = xhr;
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onabort = () => reject(new Error('aborted'));
    xhr.onerror = () => reject(new Error('Network error'));
    xhr.onload = () => {
      if (xhr.status === 401) { handleUnauthorized(); return; }
      if (xhr.status >= 400) {
        try { reject(new Error(JSON.parse(xhr.responseText).detail || `HTTP ${xhr.status}`)); }
        catch { reject(new Error(`HTTP ${xhr.status}`)); }
        return;
      }
      try { resolve(JSON.parse(xhr.responseText)); }
      catch { reject(new Error('Invalid response')); }
    };
    xhr.open('POST', '/api/v1/rag/documents');
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('session_id', sessionId);
    xhr.send(fd);
  });
}

export const deleteDocument = (documentId, token) =>
  apiFetch(`/api/v1/rag/documents/${documentId}`, { method: 'DELETE' }, token);

// Clusters
export const getClusterComments = (clusterId, token) =>
  apiFetch(`/api/v1/clusters/${clusterId}/comments`, {}, token);

export const getRepresentativeQuestion = (clusterId, token) =>
  apiFetch(`/api/v1/dashboard/clusters/${clusterId}/representative`, {}, token);

// Profile & password
export const updateProfile = (data, token) =>
  apiFetch('/api/v1/auth/profile', { method: 'PATCH', body: JSON.stringify(data) }, token);

export const changePassword = (currentPassword, newPassword, token) =>
  apiFetch('/api/v1/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  }, token);
