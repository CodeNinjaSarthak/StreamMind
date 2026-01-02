const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export const backend = {
  async get(endpoint: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    return response.json();
  },

  async post(endpoint: string, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },

  async websocket(sessionId: number): Promise<WebSocket> {
    const ws = new WebSocket(`${API_BASE_URL.replace('http', 'ws')}/ws/${sessionId}`);
    return ws;
  },
};

