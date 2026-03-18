import React, { useState, useEffect } from 'react';

export const App: React.FC = () => {
  const [status, setStatus] = useState<string>('disconnected');

  useEffect(() => {
    // TODO: Initialize dashboard state
    console.log('Dashboard initialized');
  }, []);

  return (
    <div style={{ width: '400px', padding: '20px' }}>
      <h1>StreamMind</h1>
      <p>Status: {status}</p>
      <button onClick={() => setStatus('connected')}>Connect</button>
    </div>
  );
};

